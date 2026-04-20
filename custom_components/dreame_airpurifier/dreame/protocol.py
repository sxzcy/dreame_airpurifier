from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from ..const import (
    BASIC_AUTH,
    DEVICE_LIST_PATH,
    DREAME_RLC,
    KNOWN_REGIONS,
    OTC_INFO_PATH,
    PASSWORD_SALT,
    PROPS_PATH,
    REGION_AUTO,
    SEND_COMMAND_PREFIX,
    SEND_COMMAND_SUFFIX,
    TOKEN_PATH,
    USER_AGENT,
)
from ..utils import maybe_json
from .exceptions import DreameSmartlifeApiError, DreameSmartlifeAuthError

_LOGGER = logging.getLogger(__name__)


class DreameSmartlifeClient:
    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        region: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._requested_region = region.lower()
        self._region = region.lower()
        self._tenant_id = "000000"
        self._auth_token: str | None = None
        self._refresh_token: str | None = None
        self._uid: str | None = None
        self._domain: str | None = None

    @property
    def uid(self) -> str | None:
        return self._uid

    @property
    def region(self) -> str:
        return self._region

    @property
    def base_url(self) -> str:
        return self._build_base_url(self._region)

    @staticmethod
    def _build_base_url(region: str) -> str:
        return f"https://{region}.iot.dreame.tech:13267"

    def _token_headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": USER_AGENT,
            "Dreame-Rlc": DREAME_RLC,
            "Authorization": BASIC_AUTH,
            "Tenant-Id": self._tenant_id,
        }

    def _json_headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": USER_AGENT,
            "Authorization": BASIC_AUTH,
            "Tenant-Id": self._tenant_id,
            "Content-Type": "application/json",
            "Dreame-Auth": self._auth_token or "",
        }

    async def _async_login_region(self, region: str) -> dict[str, Any]:
        password_hash = hashlib.md5(f"{self._password}{PASSWORD_SALT}".encode("utf-8")).hexdigest()
        url = f"{self._build_base_url(region)}{TOKEN_PATH}"
        payload = {
            "grant_type": "password",
            "scope": "all",
            "platform": "IOS",
            "type": "account",
            "username": self._username,
            "password": password_hash,
        }
        _LOGGER.debug("Logging in to Dreame air purifier cloud: %s", url)
        try:
            async with self._session.post(url, headers=self._token_headers(), data=payload, timeout=20) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
        except ClientResponseError as err:
            raise DreameSmartlifeAuthError(f"Login failed with HTTP {err.status}") from err
        except Exception as err:
            raise DreameSmartlifeAuthError(f"Login failed: {err}") from err

        if "access_token" not in data:
            raise DreameSmartlifeAuthError(f"Unexpected login response: {data}")
        return data

    async def async_login(self) -> dict[str, Any]:
        regions = KNOWN_REGIONS if self._requested_region == REGION_AUTO else (self._requested_region,)
        last_error: DreameSmartlifeAuthError | None = None

        for region in regions:
            try:
                data = await self._async_login_region(region)
            except DreameSmartlifeAuthError as err:
                last_error = err
                if self._requested_region != REGION_AUTO:
                    raise
                continue

            self._auth_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            self._tenant_id = str(data.get("tenant_id", self._tenant_id))
            self._uid = str(data.get("uid", "")) or None
            self._region = str(data.get("region", region)).lower()
            self._domain = data.get("domain") or self.base_url
            _LOGGER.debug("Logged in to Dreame air purifier cloud using region %s", self._region)
            return data

        if last_error is not None:
            raise last_error
        raise DreameSmartlifeAuthError("Login failed: no region candidates available")

    async def _async_post_json(self, url: str, payload: dict[str, Any], retry: bool = True) -> Any:
        if not self._auth_token:
            await self.async_login()
        try:
            async with self._session.post(url, headers=self._json_headers(), json=payload, timeout=20) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except ClientResponseError as err:
            if retry and err.status in (401, 403):
                await self.async_login()
                return await self._async_post_json(url, payload, retry=False)
            raise DreameSmartlifeApiError(f"Request failed with HTTP {err.status}: {url}") from err
        except Exception as err:
            raise DreameSmartlifeApiError(f"Request failed: {err}") from err

    async def async_list_devices(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}{DEVICE_LIST_PATH}"
        payload = {"page": 1, "size": 100}
        data = await self._async_post_json(url, payload)
        return data.get("data", {}).get("page", {}).get("records", [])

    async def async_get_props(self, did: str, keys: list[str]) -> list[dict[str, Any]]:
        if not keys:
            return []
        url = f"{self.base_url}{PROPS_PATH}"
        data = await self._async_post_json(url, {"did": did, "keys": ",".join(keys)})
        result = data.get("data", [])
        if isinstance(result, list):
            return result
        return []

    async def async_get_otc_info(self, did: str) -> dict[str, Any]:
        url = f"{self.base_url}{OTC_INFO_PATH}"
        data = await self._async_post_json(url, {"did": did})
        return data.get("data", {})

    def _command_url(self, bind_domain: str) -> str:
        host = bind_domain.split(".", 1)[0]
        return f"{self.base_url}{SEND_COMMAND_PREFIX}{host}{SEND_COMMAND_SUFFIX}"

    async def async_send_command(
        self,
        bind_domain: str,
        did: str,
        method: str,
        params: Any,
    ) -> dict[str, Any]:
        request_id = random.randint(1000, 9999)
        envelope = {
            "did": did,
            "id": request_id,
            "data": {
                "did": did,
                "id": request_id,
                "method": method,
                "params": params,
            },
        }
        url = self._command_url(bind_domain)
        result = await self._async_post_json(url, envelope)
        if isinstance(result, dict):
            return result
        _LOGGER.debug("Unexpected Dreame air purifier command response for %s: %r", method, result)
        return {}

    async def async_get_properties_raw(
        self,
        bind_domain: str,
        did: str,
        requests: list[dict[str, int]],
    ) -> list[dict[str, Any]]:
        result = await self.async_send_command(bind_domain, did, "get_properties", requests)
        if not isinstance(result, dict):
            return []
        return result.get("data", {}).get("result", []) or result.get("result", []) or []

    async def async_set_properties(
        self,
        bind_domain: str,
        did: str,
        values: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result = await self.async_send_command(bind_domain, did, "set_properties", values)
        if not isinstance(result, dict):
            return []
        return result.get("data", {}).get("result", []) or result.get("result", []) or []

    async def async_action(
        self,
        bind_domain: str,
        did: str,
        siid: int,
        aiid: int,
        inputs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        params = {
            "did": did,
            "siid": siid,
            "aiid": aiid,
            "in": inputs or [],
        }
        result = await self.async_send_command(bind_domain, did, "action", params)
        if isinstance(result, dict):
            return result
        return {}

    async def async_probe_properties(
        self,
        bind_domain: str,
        did: str,
        max_siid: int,
        max_piid: int,
        chunk_size: int = 20,
    ) -> dict[str, Any]:
        requests: list[dict[str, int]] = []
        for siid in range(1, max_siid + 1):
            for piid in range(1, max_piid + 1):
                requests.append({"siid": siid, "piid": piid})

        discovered: dict[str, Any] = {}
        for index in range(0, len(requests), chunk_size):
            chunk = requests[index : index + chunk_size]
            result = await self.async_get_properties_raw(bind_domain, did, chunk)
            for item in result:
                if not isinstance(item, dict):
                    continue
                if item.get("code") != 0:
                    continue
                key = f"{item.get('siid')}.{item.get('piid')}"
                value = maybe_json(item.get("value"))
                discovered[key] = value
            await asyncio.sleep(0.05)
        return discovered
