"""Pure Dreame Smart Life cloud protocol helpers and immutable models (zero I/O)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import random
from types import MappingProxyType
from typing import Any

from . import const as C

_COMMON_HEADERS: Mapping[str, str] = MappingProxyType(
    {
        "Accept": "*/*",
        "Accept-Language": "en-US;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": C.USER_AGENT,
        "Authorization": C.BASIC_AUTH,
    }
)


class DreameError(Exception):
    """Base Dreame Smart Life exception."""


class DreameAuthError(DreameError):
    """Authentication or authorization error."""


class DreameApiError(DreameError):
    """Transport or remote API error."""


class DreameCommandError(DreameApiError):
    """Device or cloud rejected a write command."""


@dataclass(frozen=True, slots=True)
class DreameDeviceDescriptor:
    did: str
    name: str
    model: str
    bind_domain: str
    mac: str | None = None


@dataclass(frozen=True, slots=True)
class DreameState:
    descriptor: DreameDeviceDescriptor
    properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    otc_info: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
        if not isinstance(self.otc_info, MappingProxyType):
            object.__setattr__(self, "otc_info", MappingProxyType(dict(self.otc_info)))

    def with_property(self, key: str, value: Any) -> DreameState:
        return DreameState(self.descriptor, {**self.properties, key: value}, self.otc_info)


def format_error_detail(err: BaseException) -> str:
    return str(err) or err.__class__.__name__


def parse_key(key: str) -> tuple[int, int]:
    siid, piid = key.split(".", 1)
    return int(siid), int(piid)


def maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in "[{":
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def values_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, bool) or isinstance(right, bool):
        return str(left).lower() == str(right).lower()
    return str(left) == str(right)


def hash_password(password: str) -> str:
    return hashlib.md5(f"{password}{C.PASSWORD_SALT}".encode("utf-8")).hexdigest()


def build_base_url(region: str) -> str:
    return f"https://{region.lower()}.iot.dreame.tech:13267"


def build_command_path(bind_domain: str) -> str:
    if not bind_domain or not bind_domain.strip():
        raise DreameApiError("Missing Dreame bind domain for command request")
    return f"{C.SEND_COMMAND_PREFIX}{bind_domain.strip().split('.', 1)[0]}{C.SEND_COMMAND_SUFFIX}"


def build_token_headers(tenant_id: str = C.DEFAULT_TENANT_ID) -> dict[str, str]:
    return {
        **_COMMON_HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
        "Dreame-Rlc": C.DREAME_RLC,
        "Tenant-Id": tenant_id,
    }


def build_json_headers(auth_token: str | None, tenant_id: str = C.DEFAULT_TENANT_ID) -> dict[str, str]:
    return {
        **_COMMON_HEADERS,
        "Content-Type": "application/json",
        "Tenant-Id": tenant_id,
        "Dreame-Auth": auth_token or "",
    }


def build_login_payload(username: str, password: str) -> dict[str, str]:
    return {
        "grant_type": "password",
        "scope": "all",
        "platform": "IOS",
        "type": "account",
        "username": username,
        "password": hash_password(password),
    }


def build_command_envelope(
    did: str, method: str, params: Any, *, request_id: int | None = None
) -> dict[str, Any]:
    req_id = random.randint(1000, 9999) if request_id is None else request_id
    return {
        "did": did,
        "id": req_id,
        "data": {"did": did, "id": req_id, "method": method, "params": params},
    }


def is_success_code(code: Any) -> bool:
    return code in (None, 0, "0", 200, "200")


def response_message(data: Mapping[str, Any]) -> str:
    return str(data.get("msg") or data.get("message") or data.get("error") or data)


def raise_for_api_error(data: Any, url: str) -> None:
    if not isinstance(data, dict) or is_success_code(data.get("code")):
        return
    code, message = data.get("code"), response_message(data)
    if str(code) in {"401", "403"}:
        raise DreameAuthError(f"Authentication failed: {message}")
    raise DreameApiError(f"API returned code {code}: {message} ({url})")


def assert_command_success(method: str, result: Mapping[str, Any]) -> None:
    data = result.get("data")
    if isinstance(data, list):
        command_result, command_error = data, None
    else:
        payload = data if isinstance(data, dict) else result
        command_error = payload.get("error") if isinstance(payload, Mapping) else None
        command_result = payload.get("result") if isinstance(payload, Mapping) else None
    if command_error:
        raise DreameCommandError(f"{method} failed: {command_error}")
    items = (
        [command_result]
        if isinstance(command_result, dict)
        else (command_result if isinstance(command_result, list) else [])
    )
    for item in items:
        if isinstance(item, dict) and not is_success_code(item.get("code")):
            raise DreameCommandError(f"{method} failed for {item}")


def parse_device_list_response(data: Any) -> list[dict[str, Any]]:
    payload = data.get("data") if isinstance(data, dict) else None
    page = payload.get("page") if isinstance(payload, dict) else None
    records = page.get("records") if isinstance(page, dict) else None
    return [i for i in records if isinstance(i, dict)] if isinstance(records, list) else []


def parse_props_response(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        return {}
    return {
        str(i["key"]): maybe_json(i.get("value"))
        for i in data["data"]
        if isinstance(i, dict) and i.get("key")
    }


def parse_otc_response(data: Any) -> dict[str, Any]:
    payload = data.get("data") if isinstance(data, dict) else None
    return dict(payload) if isinstance(payload, dict) else {}
