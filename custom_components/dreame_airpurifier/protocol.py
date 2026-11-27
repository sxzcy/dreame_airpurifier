"""Pure Dreame Smart Life cloud protocol helpers and immutable models (zero I/O)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import random
import re
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
    fw_version: str | None = None
    mqtt_connected: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
        if not isinstance(self.otc_info, MappingProxyType):
            object.__setattr__(self, "otc_info", MappingProxyType(dict(self.otc_info)))

    def with_property(self, key: str, value: Any) -> DreameState:
        return self.with_properties({key: value})

    def with_properties(self, updates: Mapping[str, Any]) -> DreameState:
        if not updates:
            return self
        return DreameState(
            self.descriptor,
            {**self.properties, **updates},
            self.otc_info,
            self.fw_version,
            self.mqtt_connected,
        )

    def with_otc_info(self, otc_info: Mapping[str, Any]) -> DreameState:
        return DreameState(
            self.descriptor,
            self.properties,
            {**self.otc_info, **otc_info},
            self.fw_version,
            self.mqtt_connected,
        )

    def with_mqtt_connected(self, connected: bool) -> DreameState:
        if self.mqtt_connected == connected:
            return self
        return DreameState(
            self.descriptor,
            self.properties,
            self.otc_info,
            self.fw_version,
            connected,
        )


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


def parse_bind_domain(bind_domain: str, region: str) -> tuple[str, int]:
    """Parse bindDomain ('host:port') into MQTT (hostname, port)."""
    raw = (bind_domain or "").strip()
    if not raw:
        raise DreameApiError("Missing Dreame bind domain for MQTT connection")
    if ":" in raw:
        host, port_str = raw.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = C.MQTT_DEFAULT_PORT
    else:
        host, port = raw, C.MQTT_DEFAULT_PORT
    host = host.strip()
    if not host:
        raise DreameApiError("Empty Dreame MQTT host in bind domain")
    if region.lower() == "kr" and host.startswith("10100."):
        host = "10000." + host.split(".", 1)[1]
    return host, port


def build_mqtt_client_id(did: str, random_hex: str) -> str:
    digest = hashlib.md5(f"{did}mqtt{random_hex}".encode("utf-8")).hexdigest()
    return f"p_{digest}"


def build_mqtt_topics(did: str, master_uid: str, model: str, region: str) -> tuple[str, ...]:
    reg = region.lower()
    primary = f"/status/{did}/{master_uid}/{model}/{reg}/"
    if reg == "kr":
        return (primary, f"/status/{did}/{master_uid}/{model}/sg/")
    return (primary,)


def parse_mqtt_message(payload: bytes | str) -> tuple[str | None, dict[str, Any]]:
    """Parse a Dreame MQTT push payload into ('properties'|'otc'|None, data)."""
    try:
        text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else str(payload)
        envelope = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, {}
    if not isinstance(envelope, dict):
        return None, {}
    data = envelope.get("data")
    if not isinstance(data, dict):
        return None, {}
    method = data.get("method")
    params = data.get("params")
    if method == "properties_changed" and isinstance(params, list):
        updates: dict[str, Any] = {}
        for item in params:
            if not isinstance(item, dict):
                continue
            siid = item.get("siid")
            piid = item.get("piid")
            if siid is not None and piid is not None and "value" in item:
                updates[f"{siid}.{piid}"] = maybe_json(item["value"])
        return ("properties", updates) if updates else (None, {})
    if method == "_otc.info" and isinstance(params, dict):
        return "otc", {"otcInfo": {"params": params}}
    return None, {}


def parse_mcu_version(fw_version: str | None) -> int | None:
    """Extract numeric MCU version from firmware string like '1.9.3_1072'."""
    if not fw_version:
        return None
    match = re.search(r"_(\d+)$", str(fw_version).strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def resolve_child_lock_key(properties: Mapping[str, Any], fw_version: str | None = None) -> str:
    """Resolve child lock MIOT key: 6.10 on 1.9.3_1072+ firmware, 2.5 on legacy 1055."""
    if properties.get(C.PROP_CHILD_LOCK_V2) is not None:
        return C.PROP_CHILD_LOCK_V2
    mcu = parse_mcu_version(fw_version)
    if mcu is not None and mcu >= C.FP10_V2_MCU_MIN:
        return C.PROP_CHILD_LOCK_V2
    return C.PROP_CHILD_LOCK


def resolve_key_sound_key(properties: Mapping[str, Any], fw_version: str | None = None) -> str:
    """Resolve key sound MIOT key: 6.17 on 1.9.3_1072+ firmware, 6.7 on legacy 1055."""
    if properties.get(C.PROP_KEY_SOUND) is not None:
        return C.PROP_KEY_SOUND
    mcu = parse_mcu_version(fw_version)
    if mcu is not None and mcu >= C.FP10_V2_MCU_MIN:
        return C.PROP_KEY_SOUND
    return C.PROP_KEY_SOUND_LEGACY


def extract_wifi_rssi(otc_info: Mapping[str, Any]) -> int | None:
    """Extract Wi-Fi RSSI (dBm) from Dreame devOTCInfo payload."""
    if not isinstance(otc_info, Mapping):
        return None
    candidates: list[Any] = []
    otc_inner = otc_info.get("otcInfo")
    if isinstance(otc_inner, Mapping):
        params = otc_inner.get("params")
        if isinstance(params, Mapping):
            ap = params.get("ap")
            if isinstance(ap, Mapping):
                candidates.append(ap.get("rssi"))
            candidates.append(params.get("rssi"))
    params_top = otc_info.get("params")
    if isinstance(params_top, Mapping):
        ap = params_top.get("ap")
        if isinstance(ap, Mapping):
            candidates.append(ap.get("rssi"))
    candidates.append(otc_info.get("rssi"))
    for raw in candidates:
        if raw is None or isinstance(raw, bool):
            continue
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            continue
    return None


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


def build_refresh_payload(refresh_token: str) -> dict[str, str]:
    return {
        "grant_type": "refresh_token",
        "platform": "IOS",
        "refresh_token": refresh_token,
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


def parse_device_info_response(data: Any) -> dict[str, Any]:
    payload = data.get("data") if isinstance(data, dict) else None
    return dict(payload) if isinstance(payload, dict) else {}


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
