from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

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
from .exceptions import (
    DreameSmartlifeApiError,
    DreameSmartlifeAuthError,
    DreameSmartlifeCommandError,
    DreameSmartlifeError,
)

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

    @staticmethod
    def _is_success_code(code: Any) -> bool:
        return code in (None, 0, "0", 200, "200")

    @staticmethod
    def _response_message(data: dict[str, Any]) -> str:
        return str(data.get("msg") or data.get("message") or data.get("error") or data)

    @classmethod
    def _raise_for_api_error(cls, data: Any, url: str) -> None:
        if not isinstance(data, dict):
            return
        code = data.get("code")
        if cls._is_success_code(code):
            return
        message = cls._response_message(data)
        if str(code) in {"401", "403"}:
            raise DreameSmartlifeAuthError(f"Authentication failed: {message}")
        raise DreameSmartlifeApiError(f"API returned code {code}: {message} ({url})")

    @classmethod
    def _assert_command_success(cls, method: str, result: dict[str, Any]) -> None:
        data = result.get("data")
        if isinstance(data, list):
            command_result = data
            command_error = None
        else:
            payload = data if isinstance(data, dict) else result
            command_error = payload.get("error") if isinstance(payload, dict) else None
            command_result = payload.get("result") if isinstance(payload, dict) else None
        if command_error:
            raise DreameSmartlifeCommandError(f"{method} failed: {command_error}")

        if isinstance(command_result, dict):
            items = [command_result]
        elif isinstance(command_result, list):
            items = command_result
        else:
            return

        for item in items:
            if not isinstance(item, dict):
                continue
            if cls._is_success_code(item.get("code")):
                continue
            raise DreameSmartlifeCommandError(f"{method} failed for {item}")

    @staticmethod
    def _extract_command_result(result: dict[str, Any]) -> list[dict[str, Any]]:
        data = result.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        payload = data if isinstance(data, dict) else result
        raw_result = payload.get("result") if isinstance(payload, dict) else None
        if isinstance(raw_result, list):
            return [item for item in raw_result if isinstance(item, dict)]
        if isinstance(raw_result, dict):
            return [raw_result]
        return []

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
            if err.status in (400, 401, 403):
                raise DreameSmartlifeAuthError(f"Login failed with HTTP {err.status}") from err
            raise DreameSmartlifeApiError(f"Login request failed with HTTP {err.status}: {url}") from err
        except (asyncio.TimeoutError, ClientError) as err:
            raise DreameSmartlifeApiError(f"Login request failed: {err}") from err
        except Exception as err:
            raise DreameSmartlifeApiError(f"Unexpected login failure: {err}") from err

        if "access_token" not in data:
            raise DreameSmartlifeAuthError(f"Unexpected login response: {data}")
        return data

    async def async_login(self) -> dict[str, Any]:
        regions = KNOWN_REGIONS if self._requested_region == REGION_AUTO else (self._requested_region,)
        last_error: DreameSmartlifeError | None = None

        for region in regions:
            try:
                data = await self._async_login_region(region)
            except DreameSmartlifeError as err:
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
                data = await response.json(content_type=None)
                self._raise_for_api_error(data, url)
                return data
        except ClientResponseError as err:
            if retry and err.status in (401, 403):
                await self.async_login()
                return await self._async_post_json(url, payload, retry=False)
            if err.status in (401, 403):
                raise DreameSmartlifeAuthError(f"Request failed with HTTP {err.status}: {url}") from err
            raise DreameSmartlifeApiError(f"Request failed with HTTP {err.status}: {url}") from err
        except DreameSmartlifeAuthError:
            raise
        except DreameSmartlifeApiError:
            raise
        except (asyncio.TimeoutError, ClientError) as err:
            raise DreameSmartlifeApiError(f"Request failed: {err}") from err
        except Exception as err:
            raise DreameSmartlifeApiError(f"Unexpected request failure: {err}") from err

    async def async_list_devices(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}{DEVICE_LIST_PATH}"
        payload = {"page": 1, "size": 100}
        data = await self._async_post_json(url, payload)
        payload_data = data.get("data", {}) if isinstance(data, dict) else {}
        page = payload_data.get("page", {}) if isinstance(payload_data, dict) else {}
        records = page.get("records", []) if isinstance(page, dict) else []
        return records if isinstance(records, list) else []

    async def async_get_props(self, did: str, keys: list[str]) -> list[dict[str, Any]]:
        if not keys:
            return []
        url = f"{self.base_url}{PROPS_PATH}"
        data = await self._async_post_json(url, {"did": did, "keys": ",".join(keys)})
        result = data.get("data", []) if isinstance(data, dict) else []
        if isinstance(result, list):
            return result
        return []

    async def async_get_otc_info(self, did: str) -> dict[str, Any]:
        url = f"{self.base_url}{OTC_INFO_PATH}"
        data = await self._async_post_json(url, {"did": did})
        result = data.get("data", {}) if isinstance(data, dict) else {}
        return result if isinstance(result, dict) else {}

    def _command_url(self, bind_domain: str) -> str:
        if not bind_domain:
            raise DreameSmartlifeApiError("Missing Dreame bind domain for command request")
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
        return self._extract_command_result(result)

    async def async_set_properties(
        self,
        bind_domain: str,
        did: str,
        values: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result = await self.async_send_command(bind_domain, did, "set_properties", values)
        if not isinstance(result, dict):
            return []
        self._assert_command_success("set_properties", result)
        return self._extract_command_result(result)

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
            self._assert_command_success("action", result)
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
                if not self._is_success_code(item.get("code")):
                    continue
                key = f"{item.get('siid')}.{item.get('piid')}"
                value = maybe_json(item.get("value"))
                discovered[key] = value
            await asyncio.sleep(0.05)
        return discovered
