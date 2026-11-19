"""Async Dreame Smart Life cloud HTTP client (zero HA imports)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import logging
from time import monotonic
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from . import const as C
from . import protocol as P

_LOGGER = logging.getLogger(__name__)


class DreameClient:
    """Pure-asyncio client for the Dreame Smart Life cloud API."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        region: str,
        *,
        otc_refresh_interval: float = C.OTC_REFRESH_INTERVAL,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._region = region.lower()
        self._resolved_region: str | None = None if self._region == C.REGION_AUTO else self._region
        self._tenant_id = C.DEFAULT_TENANT_ID
        self._auth_token: str | None = None
        self._refresh_token: str | None = None
        self._uid: str | None = None
        self._login_lock = asyncio.Lock()
        self._otc_refresh_interval = otc_refresh_interval
        self._otc_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def region(self) -> str:
        return self._region

    @property
    def uid(self) -> str | None:
        return self._uid

    @property
    def base_url(self) -> str:
        return P.build_base_url(self._region)

    async def _async_login_region(self, region: str, *, timeout: ClientTimeout) -> dict[str, Any]:
        url = f"{P.build_base_url(region)}{C.TOKEN_PATH}"
        try:
            async with asyncio.timeout(timeout.total):
                async with self._session.post(
                    url,
                    headers=P.build_token_headers(self._tenant_id),
                    data=P.build_login_payload(self._username, self._password),
                    timeout=timeout,
                ) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
        except ClientResponseError as err:
            exc = P.DreameAuthError if err.status in (400, 401, 403) else P.DreameApiError
            raise exc(f"Login failed with HTTP {err.status}: {url}") from err
        except (TimeoutError, ClientError) as err:
            raise P.DreameApiError(f"Login request failed: {P.format_error_detail(err)}") from err
        except Exception as err:
            raise P.DreameApiError(f"Unexpected login failure: {P.format_error_detail(err)}") from err

        if not isinstance(data, dict) or "access_token" not in data:
            msg = P.response_message(data) if isinstance(data, dict) else "missing access_token"
            raise P.DreameAuthError(f"Unexpected login response: {msg}")
        return data

    async def _async_login_locked(self) -> dict[str, Any]:
        is_auto = self._resolved_region is None
        regions = C.KNOWN_REGIONS if is_auto else (self._resolved_region,)
        timeout = (
            ClientTimeout(total=C.AUTO_REGION_TOTAL_TIMEOUT, connect=C.AUTO_REGION_CONNECT_TIMEOUT)
            if is_auto
            else ClientTimeout(total=C.DEFAULT_REQUEST_TIMEOUT)
        )
        last_auth_err: P.DreameAuthError | None = None
        last_api_err: P.DreameError | None = None

        for region in regions:
            try:
                data = await self._async_login_region(region, timeout=timeout)
            except P.DreameAuthError as err:
                last_auth_err = err
                if not is_auto:
                    self._auth_token = None
                    raise
                continue
            except P.DreameError as err:
                last_api_err = err
                if not is_auto:
                    raise
                continue

            self._auth_token = str(data["access_token"])
            self._refresh_token = data.get("refresh_token")
            self._tenant_id = str(data.get("tenant_id", self._tenant_id))
            self._uid = str(data.get("uid", "")) or None
            resolved = str(data.get("region", region)).lower()
            self._region = self._resolved_region = resolved
            _LOGGER.debug("Logged in to Dreame cloud region %s", resolved)
            return data

        self._auth_token = None
        if last_api_err is not None:
            raise last_api_err
        if last_auth_err is not None:
            raise last_auth_err
        raise P.DreameAuthError("Login failed: no region candidates available")

    async def async_login(self) -> dict[str, Any]:
        async with self._login_lock:
            return await self._async_login_locked()

    async def _async_relogin_if_needed(self, used_token: str | None) -> None:
        async with self._login_lock:
            if not self._auth_token or self._auth_token == used_token:
                await self._async_login_locked()

    async def _async_post_json(
        self, path: str, payload: dict[str, Any], *, retry: bool = True
    ) -> Any:
        if not self._auth_token:
            await self._async_relogin_if_needed(None)
        url = f"{self.base_url}{path}"
        used_token = self._auth_token
        timeout = ClientTimeout(total=C.DEFAULT_REQUEST_TIMEOUT)
        try:
            async with asyncio.timeout(timeout.total):
                async with self._session.post(
                    url,
                    headers=P.build_json_headers(used_token, self._tenant_id),
                    json=payload,
                    timeout=timeout,
                ) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    P.raise_for_api_error(data, url)
                    return data
        except ClientResponseError as err:
            if retry and err.status in (401, 403):
                await self._async_relogin_if_needed(used_token)
                return await self._async_post_json(path, payload, retry=False)
            exc = P.DreameAuthError if err.status in (401, 403) else P.DreameApiError
            raise exc(f"Request failed with HTTP {err.status}: {url}") from err
        except P.DreameAuthError:
            if retry:
                await self._async_relogin_if_needed(used_token)
                return await self._async_post_json(path, payload, retry=False)
            raise
        except P.DreameApiError:
            raise
        except (TimeoutError, ClientError) as err:
            raise P.DreameApiError(f"Request failed: {P.format_error_detail(err)}") from err
        except Exception as err:
            raise P.DreameApiError(f"Unexpected request failure: {P.format_error_detail(err)}") from err

    async def async_list_devices(self) -> list[dict[str, Any]]:
        return P.parse_device_list_response(
            await self._async_post_json(C.DEVICE_LIST_PATH, {"page": 1, "size": 100})
        )

    async def async_get_props(self, did: str, keys: Sequence[str]) -> dict[str, Any]:
        if not keys:
            return {}
        return P.parse_props_response(
            await self._async_post_json(C.PROPS_PATH, {"did": did, "keys": ",".join(keys)})
        )

    async def async_get_otc_info(self, did: str, *, force: bool = False) -> dict[str, Any]:
        now = monotonic()
        cached = self._otc_cache.get(did)
        if not force and cached is not None and (now - cached[0]) < self._otc_refresh_interval:
            return dict(cached[1])
        info = P.parse_otc_response(await self._async_post_json(C.OTC_INFO_PATH, {"did": did}))
        self._otc_cache[did] = (now, info)
        return dict(info)

    async def _async_send_command(self, bind_domain: str, did: str, method: str, params: Any) -> None:
        result = await self._async_post_json(
            P.build_command_path(bind_domain), P.build_command_envelope(did, method, params)
        )
        if isinstance(result, dict):
            P.assert_command_success(method, result)

    async def async_set_property(
        self, bind_domain: str, did: str, siid: int, piid: int, value: Any
    ) -> None:
        await self._async_send_command(
            bind_domain, did, "set_properties", [{"siid": siid, "piid": piid, "value": value}]
        )

    async def async_action(
        self,
        bind_domain: str,
        did: str,
        siid: int,
        aiid: int,
        inputs: list[dict[str, Any]] | None = None,
    ) -> None:
        await self._async_send_command(
            bind_domain, did, "action", {"did": did, "siid": siid, "aiid": aiid, "in": inputs or []}
        )
