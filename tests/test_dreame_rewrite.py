"""Comprehensive unit tests for the Dreame FP10 Air Purifier v1.0.0 rewrite."""

from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_DIR = REPO_ROOT / "custom_components" / "dreame_airpurifier"
LEGACY_DIR = (
    REPO_ROOT.parents[1]
    / "ha-plugins-audit"
    / "github"
    / "dreame_airpurifier"
    / "custom_components"
    / "dreame_airpurifier"
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _install_stubs() -> None:
    """Install lightweight aiohttp, voluptuous, and HA 2026.11 API stubs."""
    # aiohttp
    aiohttp_mod = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    class ClientResponseError(ClientError):
        def __init__(self, status: int = 500, message: str = "") -> None:
            super().__init__(message or f"HTTP {status}")
            self.status = status
            self.message = message

    class ClientTimeout:
        def __init__(
            self,
            total: float | None = None,
            connect: float | None = None,
            sock_connect: float | None = None,
            sock_read: float | None = None,
        ) -> None:
            self.total = total
            self.connect = connect
            self.sock_connect = sock_connect
            self.sock_read = sock_read

    class ClientSession:
        pass

    aiohttp_mod.ClientError = ClientError
    aiohttp_mod.ClientResponseError = ClientResponseError
    aiohttp_mod.ClientTimeout = ClientTimeout
    aiohttp_mod.ClientSession = ClientSession
    sys.modules["aiohttp"] = aiohttp_mod

    # voluptuous
    vol_mod = types.ModuleType("voluptuous")

    class _Marker:
        def __init__(self, schema: Any, default: Any = None) -> None:
            self.schema = schema
            self.default = default

        def __hash__(self) -> int:
            return hash((self.__class__, self.schema))

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _Marker) and self.schema == other.schema

    class Required(_Marker):
        pass

    class Optional(_Marker):
        pass

    class Schema:
        def __init__(self, schema: dict[Any, Any]) -> None:
            self.schema = schema

        def __call__(self, data: Any) -> Any:
            return data

    class All:
        def __init__(self, *validators: Any) -> None:
            self.validators = validators

    class Coerce:
        def __init__(self, target_type: Any) -> None:
            self.target_type = target_type

    class Range:
        def __init__(self, min: Any = None, max: Any = None) -> None:
            self.min = min
            self.max = max

    class In:
        def __init__(self, container: Any) -> None:
            self.container = container

    vol_mod.Required = Required
    vol_mod.Optional = Optional
    vol_mod.Schema = Schema
    vol_mod.All = All
    vol_mod.Coerce = Coerce
    vol_mod.Range = Range
    vol_mod.In = In
    sys.modules["voluptuous"] = vol_mod

    # homeassistant root
    ha_mod = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha_mod

    # homeassistant.const (verified HA 2026.11.1 constants)
    const_mod = types.ModuleType("homeassistant.const")

    class Platform:
        BUTTON = "button"
        FAN = "fan"
        NUMBER = "number"
        SELECT = "select"
        SENSOR = "sensor"
        SWITCH = "switch"

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"
        CONFIG = "config"

    class UnitOfDensity:
        MICROGRAMS_PER_CUBIC_METER = "µg/m³"

    class UnitOfTime:
        DAYS = "d"
        HOURS = "h"
        MINUTES = "min"

    const_mod.Platform = Platform
    const_mod.EntityCategory = EntityCategory
    const_mod.UnitOfDensity = UnitOfDensity
    const_mod.UnitOfTime = UnitOfTime
    const_mod.PERCENTAGE = "%"
    const_mod.CONF_USERNAME = "username"
    const_mod.CONF_PASSWORD = "password"
    sys.modules["homeassistant.const"] = const_mod

    # homeassistant.core
    core_mod = types.ModuleType("homeassistant.core")

    class HomeAssistant:
        pass

    def callback(func):
        return func

    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = callback
    sys.modules["homeassistant.core"] = core_mod

    # homeassistant.exceptions
    exc_mod = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    class ConfigEntryAuthFailed(HomeAssistantError):
        pass

    exc_mod.HomeAssistantError = HomeAssistantError
    exc_mod.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    sys.modules["homeassistant.exceptions"] = exc_mod

    # homeassistant.config_entries
    ce_mod = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        def __init__(
            self,
            entry_id: str = "entry_1",
            title: str = "Dreame FP10",
            data: dict[str, Any] | None = None,
            options: dict[str, Any] | None = None,
            unique_id: str | None = None,
        ) -> None:
            self.entry_id = entry_id
            self.title = title
            self.data = dict(data or {})
            self.options = dict(options or {})
            self.unique_id = unique_id
            self.runtime_data: Any = None
            self.reauth_started = False
            self._update_listeners: list[Any] = []

        def __class_getitem__(cls, item: Any):
            return cls

        def async_start_reauth(self, hass: Any) -> None:
            self.reauth_started = True

        def add_update_listener(self, listener: Any) -> Any:
            self._update_listeners.append(listener)
            return lambda: None

    class AbortFlow(Exception):
        def __init__(self, reason: str) -> None:
            super().__init__(reason)
            self.reason = reason

    class ConfigFlow:
        def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        hass: Any = None
        unique_id: str | None = None
        _reauth_entry: ConfigEntry | None = None
        _configured_unique_ids: set[str] = set()

        async def async_set_unique_id(self, unique_id: str | None) -> None:
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self) -> None:
            if self.unique_id in self._configured_unique_ids:
                raise AbortFlow("already_configured")

        def _abort_if_unique_id_mismatch(self, *, reason: str = "unique_id_mismatch") -> None:
            entry = self._get_reauth_entry()
            if entry.unique_id is not None and entry.unique_id != self.unique_id:
                raise AbortFlow(reason)

        def _get_reauth_entry(self) -> ConfigEntry:
            if self._reauth_entry is None:
                raise RuntimeError("reauth entry not attached")
            return self._reauth_entry

        def async_update_reload_and_abort(
            self, entry: ConfigEntry, *, data_updates: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            if data_updates:
                entry.data = {**entry.data, **data_updates}
            return {"type": "abort", "reason": "reauth_successful", "data_updates": data_updates}

        def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "create_entry", **kwargs}

    class OptionsFlow:
        def __init__(self) -> None:
            self._config_entry: ConfigEntry | None = None

        @property
        def config_entry(self) -> ConfigEntry:
            if self._config_entry is None:
                raise RuntimeError("config_entry not attached")
            return self._config_entry

        def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
            return {"type": "create_entry", **kwargs}

    class OptionsFlowWithReload(OptionsFlow):
        pass

    ce_mod.ConfigEntry = ConfigEntry
    ce_mod.ConfigFlow = ConfigFlow
    ce_mod.ConfigFlowResult = dict
    ce_mod.OptionsFlow = OptionsFlow
    ce_mod.OptionsFlowWithReload = OptionsFlowWithReload
    ce_mod.AbortFlow = AbortFlow
    sys.modules["homeassistant.config_entries"] = ce_mod

    # homeassistant.helpers
    helpers_mod = types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = helpers_mod

    aio_helper_mod = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aio_helper_mod.async_get_clientsession = MagicMock()
    sys.modules["homeassistant.helpers.aiohttp_client"] = aio_helper_mod

    dr_mod = types.ModuleType("homeassistant.helpers.device_registry")

    class DeviceInfo(dict):
        pass

    dr_mod.DeviceInfo = DeviceInfo
    sys.modules["homeassistant.helpers.device_registry"] = dr_mod

    ep_mod = types.ModuleType("homeassistant.helpers.entity_platform")
    ep_mod.AddEntitiesCallback = Any
    sys.modules["homeassistant.helpers.entity_platform"] = ep_mod

    uc_mod = types.ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __init__(
            self,
            hass: Any,
            logger: Any,
            *,
            name: str,
            config_entry: Any = None,
            update_interval: Any = None,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.config_entry = config_entry
            self.update_interval = update_interval
            self.data: Any = None

        def __class_getitem__(cls, item: Any):
            return cls

        def async_set_updated_data(self, data: Any) -> None:
            self.data = data

        async def async_config_entry_first_refresh(self) -> None:
            self.data = await self._async_update_data()

        async def async_request_refresh(self) -> None:
            self.data = await self._async_update_data()

    class CoordinatorEntity:
        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

        def __class_getitem__(cls, item: Any):
            return cls

    uc_mod.UpdateFailed = UpdateFailed
    uc_mod.DataUpdateCoordinator = DataUpdateCoordinator
    uc_mod.CoordinatorEntity = CoordinatorEntity
    sys.modules["homeassistant.helpers.update_coordinator"] = uc_mod

    selector_mod = types.ModuleType("homeassistant.helpers.selector")

    class TextSelectorType:
        PASSWORD = "password"
        TEXT = "text"

    @dataclass
    class TextSelectorConfig:
        type: str = TextSelectorType.TEXT

    class TextSelector:
        def __init__(self, config: TextSelectorConfig) -> None:
            self.config = config

    selector_mod.TextSelector = TextSelector
    selector_mod.TextSelectorConfig = TextSelectorConfig
    selector_mod.TextSelectorType = TextSelectorType
    sys.modules["homeassistant.helpers.selector"] = selector_mod

    # homeassistant.util.percentage (exact HA Core formulas)
    util_mod = types.ModuleType("homeassistant.util")
    pct_mod = types.ModuleType("homeassistant.util.percentage")

    def int_states_in_range(low_high_range: tuple[float, float]) -> int:
        return int(low_high_range[1] - low_high_range[0] + 1)

    def ranged_value_to_percentage(low_high_range: tuple[float, float], value: float) -> int:
        offset = low_high_range[0] - 1
        return int((value - offset) * 100 // (low_high_range[1] - offset))

    def percentage_to_ranged_value(low_high_range: tuple[float, float], percentage: int) -> float:
        offset = low_high_range[0] - 1
        return (low_high_range[1] - offset) * percentage / 100 + offset

    pct_mod.int_states_in_range = int_states_in_range
    pct_mod.ranged_value_to_percentage = ranged_value_to_percentage
    pct_mod.percentage_to_ranged_value = percentage_to_ranged_value
    util_mod.percentage = pct_mod
    sys.modules["homeassistant.util"] = util_mod
    sys.modules["homeassistant.util.percentage"] = pct_mod

    # homeassistant.components.*
    comp_mod = types.ModuleType("homeassistant.components")
    sys.modules["homeassistant.components"] = comp_mod

    diag_mod = types.ModuleType("homeassistant.components.diagnostics")
    REDACTED = "**REDACTED**"

    def async_redact_data(data: Any, to_redact: set[str]) -> Any:
        if isinstance(data, dict):
            return {
                k: REDACTED if k in to_redact else async_redact_data(v, to_redact)
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [async_redact_data(item, to_redact) for item in data]
        return data

    diag_mod.async_redact_data = async_redact_data
    sys.modules["homeassistant.components.diagnostics"] = diag_mod

    # fan
    fan_mod = types.ModuleType("homeassistant.components.fan")

    class FanEntityFeature:
        SET_SPEED = 1
        PRESET_MODE = 8
        TURN_OFF = 16
        TURN_ON = 32

    class FanEntity:
        pass

    fan_mod.FanEntity = FanEntity
    fan_mod.FanEntityFeature = FanEntityFeature
    sys.modules["homeassistant.components.fan"] = fan_mod

    # number
    num_mod = types.ModuleType("homeassistant.components.number")

    class NumberMode:
        AUTO = "auto"
        BOX = "box"
        SLIDER = "slider"

    class NumberEntity:
        pass

    num_mod.NumberEntity = NumberEntity
    num_mod.NumberMode = NumberMode
    sys.modules["homeassistant.components.number"] = num_mod

    # select
    sel_mod = types.ModuleType("homeassistant.components.select")

    class SelectEntity:
        pass

    sel_mod.SelectEntity = SelectEntity
    sys.modules["homeassistant.components.select"] = sel_mod

    # switch
    sw_mod = types.ModuleType("homeassistant.components.switch")

    class SwitchEntity:
        pass

    sw_mod.SwitchEntity = SwitchEntity
    sys.modules["homeassistant.components.switch"] = sw_mod

    # sensor
    sen_mod = types.ModuleType("homeassistant.components.sensor")

    class SensorDeviceClass:
        PM25 = "pm25"
        PM10 = "pm10"

    class SensorStateClass:
        MEASUREMENT = "measurement"

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        device_class: Any = None
        native_unit_of_measurement: Any = None
        state_class: Any = None
        entity_category: Any = None
        icon: str | None = None

    class SensorEntity:
        pass

    sen_mod.SensorDeviceClass = SensorDeviceClass
    sen_mod.SensorStateClass = SensorStateClass
    sen_mod.SensorEntityDescription = SensorEntityDescription
    sen_mod.SensorEntity = SensorEntity
    sys.modules["homeassistant.components.sensor"] = sen_mod


_install_stubs()

import aiohttp  # noqa: E402
from homeassistant.components.fan import FanEntityFeature  # noqa: E402
from homeassistant.components.number import NumberMode  # noqa: E402
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass  # noqa: E402
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload  # noqa: E402
from homeassistant.const import (  # noqa: E402
    CONF_PASSWORD,
    CONF_USERNAME,
    PERCENTAGE,
    EntityCategory,
    Platform,
    UnitOfDensity,
    UnitOfTime,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError  # noqa: E402
from homeassistant.helpers.selector import TextSelector, TextSelectorType  # noqa: E402
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

import custom_components.dreame_airpurifier as dreame_init  # noqa: E402
from custom_components.dreame_airpurifier import const as C  # noqa: E402
from custom_components.dreame_airpurifier import protocol as P  # noqa: E402
from custom_components.dreame_airpurifier.client import DreameClient  # noqa: E402
from custom_components.dreame_airpurifier.config_flow import (  # noqa: E402
    DreameConfigFlow,
    DreameOptionsFlow,
)
from custom_components.dreame_airpurifier.coordinator import DreameCoordinator  # noqa: E402
from custom_components.dreame_airpurifier.diagnostics import async_get_config_entry_diagnostics  # noqa: E402
from custom_components.dreame_airpurifier.fan import DreameFanEntity  # noqa: E402
from custom_components.dreame_airpurifier.number import DreameFanSpeedNumber  # noqa: E402
from custom_components.dreame_airpurifier.select import DreameWindModeSelect  # noqa: E402
from custom_components.dreame_airpurifier.sensor import (  # noqa: E402
    SENSOR_DESCRIPTIONS,
    DreameSensorEntity,
)
from custom_components.dreame_airpurifier.switch import DreameChildLockSwitch  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: Any = None, status: int = 200, error: Exception | None = None) -> None:
        self._payload = payload
        self.status = status
        self._error = error

    async def __aenter__(self) -> _FakeResponse:
        if self._error is not None:
            raise self._error
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(status=self.status)

    async def json(self, content_type: Any = None) -> Any:
        return self._payload


class _FakeSession:
    def __init__(self, handler) -> None:
        self._handler = handler
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self._handler(url, kwargs)


def _live_entry(region: str = "cn", options: dict[str, Any] | None = None) -> ConfigEntry:
    """Build a ConfigEntry matching the exact live HAOS entry schema."""
    return ConfigEntry(
        entry_id="entry_fp10",
        title="Dreame FP10",
        unique_id="123456789",
        data={
            "bind_domain": "cn.iot.dreame.tech",
            "device_model": "dreame.airp.u2513",
            "device_name": "Dreame FP10",
            "did": "123456789",
            "mac": "AA:BB:CC:DD:EE:FF",
            "password": "sample_password",
            "region": region,
            "username": "user@example.com",
        },
        options=options or {},
    )


class TestArchitectureAndProtocol(unittest.TestCase):
    """Verify strict 3-layer separation and byte-level protocol equivalence."""

    def test_layer_isolation_and_no_blocking_io(self) -> None:
        def imported_roots(path: Path) -> set[str]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        roots.add(alias.name.split(".", 1)[0])
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    roots.add(node.module.split(".", 1)[0])
            return roots

        for pure_file in ("const.py", "protocol.py"):
            roots = imported_roots(COMPONENT_DIR / pure_file)
            self.assertNotIn("homeassistant", roots, pure_file)
            self.assertNotIn("aiohttp", roots, pure_file)

        client_roots = imported_roots(COMPONENT_DIR / "client.py")
        self.assertNotIn("homeassistant", client_roots)
        self.assertIn("aiohttp", client_roots)

        forbidden_io = {"urllib", "requests", "socket", "threading"}
        for py_file in COMPONENT_DIR.rglob("*.py"):
            roots = imported_roots(py_file)
            self.assertFalse(roots & forbidden_io, f"Blocking I/O import in {py_file.name}: {roots & forbidden_io}")

        # Verify bloated legacy files and scaffolding were removed
        for removed in ("button.py", "utils.py", "services.yaml", "CODEX_DONE.md", "dreame"):
            self.assertFalse((COMPONENT_DIR / removed).exists(), f"{removed} should be removed")

        # Verify offline probe tool remains intact
        self.assertTrue((REPO_ROOT / "tools" / "dreame_airpurifier_probe.py").exists())

    def test_protocol_equivalence_with_legacy_reference(self) -> None:
        """Verify login hash, headers, URLs, and command envelope match legacy reference."""
        self.assertEqual(P.build_base_url("CN"), "https://cn.iot.dreame.tech:13267")
        self.assertEqual(
            P.build_command_path("cn.iot.dreame.tech"),
            "/dreame-iot-com-cn/device/sendCommand",
        )
        with self.assertRaises(P.DreameApiError):
            P.build_command_path("   ")

        envelope = P.build_command_envelope(
            "123456789",
            "set_properties",
            [{"siid": 2, "piid": 4, "value": 7}],
            request_id=4321,
        )
        self.assertEqual(
            envelope,
            {
                "did": "123456789",
                "id": 4321,
                "data": {
                    "did": "123456789",
                    "id": 4321,
                    "method": "set_properties",
                    "params": [{"siid": 2, "piid": 4, "value": 7}],
                },
            },
        )

        # Dynamically verify against legacy reference constants if audit directory is present
        legacy_const_path = LEGACY_DIR / "const.py"
        if legacy_const_path.exists():
            spec = importlib.util.spec_from_file_location("_legacy_dreame_const", legacy_const_path)
            assert spec is not None and spec.loader is not None
            legacy_const = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy_const)

            self.assertEqual(C.USER_AGENT, legacy_const.USER_AGENT)
            self.assertEqual(C.DREAME_RLC, legacy_const.DREAME_RLC)
            self.assertEqual(C.BASIC_AUTH, legacy_const.BASIC_AUTH)
            self.assertEqual(C.PASSWORD_SALT, legacy_const.PASSWORD_SALT)
            self.assertEqual(C.TOKEN_PATH, legacy_const.TOKEN_PATH)
            self.assertEqual(C.DEVICE_LIST_PATH, legacy_const.DEVICE_LIST_PATH)
            self.assertEqual(C.OTC_INFO_PATH, legacy_const.OTC_INFO_PATH)
            self.assertEqual(C.PROPS_PATH, legacy_const.PROPS_PATH)
            self.assertEqual(C.SEND_COMMAND_PREFIX, legacy_const.SEND_COMMAND_PREFIX)
            self.assertEqual(C.SEND_COMMAND_SUFFIX, legacy_const.SEND_COMMAND_SUFFIX)

            expected_md5 = hashlib.md5(
                f"test_pw{legacy_const.PASSWORD_SALT}".encode("utf-8")
            ).hexdigest()
            payload = P.build_login_payload("alice@example.com", "test_pw")
            self.assertEqual(payload["password"], expected_md5)
            self.assertEqual(payload["grant_type"], "password")
            self.assertEqual(payload["platform"], "IOS")
            self.assertEqual(payload["type"], "account")
            self.assertEqual(payload["scope"], "all")

            token_headers = P.build_token_headers("000000")
            self.assertEqual(
                set(token_headers),
                {
                    "Accept",
                    "Content-Type",
                    "Accept-Language",
                    "Accept-Encoding",
                    "User-Agent",
                    "Dreame-Rlc",
                    "Authorization",
                    "Tenant-Id",
                },
            )
            self.assertEqual(token_headers["Dreame-Rlc"], legacy_const.DREAME_RLC)
            self.assertEqual(token_headers["Authorization"], legacy_const.BASIC_AUTH)

            json_headers = P.build_json_headers("sample_tok", "000000")
            self.assertEqual(json_headers["Dreame-Auth"], "sample_tok")
            self.assertEqual(json_headers["Authorization"], legacy_const.BASIC_AUTH)

    def test_protocol_parsers_and_state_immutability(self) -> None:
        parsed = P.parse_props_response(
            {
                "code": 0,
                "data": [
                    {"key": "3.5", "value": 18},
                    {"key": "2.1", "value": "1"},
                    {"key": "9.1", "value": '{"a": 1}'},
                    {"value": "missing_key"},
                ],
            }
        )
        self.assertEqual(parsed, {"3.5": 18, "2.1": "1", "9.1": {"a": 1}})

        with self.assertRaises(P.DreameAuthError):
            P.raise_for_api_error({"code": 401, "msg": "expired"}, "https://example")
        with self.assertRaises(P.DreameApiError):
            P.raise_for_api_error({"code": 500, "msg": "server err"}, "https://example")

        # Command success validation (both list and dict response shapes)
        P.assert_command_success("set_properties", {"data": {"result": [{"code": 0}]}})
        P.assert_command_success("action", {"data": [{"code": 0}]})
        with self.assertRaises(P.DreameCommandError):
            P.assert_command_success("set_properties", {"data": {"result": [{"code": -4004}]}})
        with self.assertRaises(P.DreameCommandError):
            P.assert_command_success("action", {"data": {"error": {"code": -1, "message": "busy"}}})

        desc = P.DreameDeviceDescriptor("123", "FP10", C.FP10_MODEL, "cn.iot.dreame.tech")
        state = P.DreameState(descriptor=desc, properties={"3.5": 10}, otc_info={"fw": "1.0"})
        with self.assertRaises(TypeError):
            state.properties["3.5"] = 99  # type: ignore[index]
        next_state = state.with_property("2.4", 6)
        self.assertNotIn("2.4", state.properties)
        self.assertEqual(next_state.properties["2.4"], 6)


class TestDreameClient(unittest.IsolatedAsyncioTestCase):
    """Verify DreameClient auth lock, retry, auto-region, timeout, and OTC cache."""

    async def test_concurrent_relogin_on_http_and_json_401_403(self) -> None:
        login_calls = 0
        req_count = 0

        def handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            nonlocal login_calls, req_count
            if "/oauth/token" in url:
                login_calls += 1
                return _FakeResponse({"access_token": f"fresh_{login_calls}", "region": "cn"})
            req_count += 1
            if kwargs["headers"].get("Dreame-Auth") == "stale_tok":
                return _FakeResponse({"code": 401 if req_count % 2 else 403, "msg": "expired"})
            return _FakeResponse({"code": 0, "data": [{"key": "3.5", "value": 21}]})

        client = DreameClient(_FakeSession(handler), "u", "p", "cn")
        client._auth_token = "stale_tok"

        r1, r2 = await asyncio.gather(
            client.async_get_props("123", ["3.5"]),
            client.async_get_props("123", ["3.5"]),
        )
        self.assertEqual(r1, {"3.5": 21})
        self.assertEqual(r2, {"3.5": 21})
        self.assertEqual(login_calls, 1)

        # HTTP 401 retry works once, then raises DreameAuthError on persistent failure
        def always_http_401(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "/oauth/token" in url:
                return _FakeResponse({"access_token": "tok_2", "region": "cn"})
            return _FakeResponse(status=401)

        client2 = DreameClient(_FakeSession(always_http_401), "u", "p", "cn")
        client2._auth_token = "tok_1"
        with self.assertRaises(P.DreameAuthError):
            await client2.async_get_props("123", ["3.5"])

    async def test_auto_region_fast_timeout_memory_and_empty_timeout_error(self) -> None:
        def auto_handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "https://cn." in url:
                return _FakeResponse({"access_token": "tok_cn", "region": "cn", "uid": "u1"})
            return _FakeResponse(status=401)

        session = _FakeSession(auto_handler)
        client = DreameClient(session, "u", "p", C.REGION_AUTO)
        await client.async_login()
        self.assertEqual(client.region, "cn")
        self.assertEqual(session.calls[0]["timeout"].total, C.AUTO_REGION_TOTAL_TIMEOUT)
        self.assertEqual(session.calls[0]["timeout"].connect, C.AUTO_REGION_CONNECT_TIMEOUT)

        prev = len(session.calls)
        await client.async_login()
        self.assertEqual(len(session.calls) - prev, 1)
        self.assertIn("https://cn.", session.calls[-1]["url"])
        self.assertEqual(session.calls[-1]["timeout"].total, C.DEFAULT_REQUEST_TIMEOUT)

        # Empty TimeoutError produces non-empty diagnostic message
        timeout_session = _FakeSession(lambda url, kw: _FakeResponse(error=TimeoutError()))
        timeout_client = DreameClient(timeout_session, "u", "p", "cn")
        timeout_client._auth_token = "tok"
        with self.assertRaises(P.DreameApiError) as ctx:
            await timeout_client.async_get_props("123", ["3.5"])
        self.assertIn("TimeoutError", str(ctx.exception))

    async def test_otc_cache_30_minutes(self) -> None:
        otc_calls = 0

        def handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            nonlocal otc_calls
            otc_calls += 1
            return _FakeResponse({"code": 0, "data": {"fw": "1.2.3", "localIp": "192.168.1.50"}})

        client = DreameClient(_FakeSession(handler), "u", "p", "cn")
        client._auth_token = "tok"

        with patch(
            "custom_components.dreame_airpurifier.client.monotonic",
            side_effect=[100.0, 200.0, 100.0 + C.OTC_REFRESH_INTERVAL + 1.0],
        ):
            info1 = await client.async_get_otc_info("123")
            info2 = await client.async_get_otc_info("123")
            self.assertEqual(otc_calls, 1)
            self.assertEqual(info1, info2)
            await client.async_get_otc_info("123")
            self.assertEqual(otc_calls, 2)

    async def test_auto_region_error_precedence_and_command_wire_envelopes(self) -> None:
        # All regions returning 401 -> DreameAuthError
        auth_only = DreameClient(_FakeSession(lambda u, k: _FakeResponse(status=401)), "u", "p", C.REGION_AUTO)
        with self.assertRaises(P.DreameAuthError):
            await auth_only.async_login()

        # Mixed timeout + 401 -> DreameApiError (cannot_connect, not false invalid_auth)
        def mixed_handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "https://ru." in url:
                return _FakeResponse(error=TimeoutError())
            return _FakeResponse(status=401)

        mixed = DreameClient(_FakeSession(mixed_handler), "u", "p", C.REGION_AUTO)
        with self.assertRaises(P.DreameApiError):
            await mixed.async_login()

        # Command wire envelopes & rejection handling
        def cmd_handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            method = kwargs["json"]["data"]["method"]
            if method == "set_properties" and kwargs["json"]["data"]["params"][0]["value"] == 99:
                return _FakeResponse({"code": 0, "data": {"result": [{"code": -4004}]}})
            return _FakeResponse({"code": 0, "data": {"result": [{"code": 0}]}})

        session = _FakeSession(cmd_handler)
        client = DreameClient(session, "u", "p", "cn")
        client._auth_token = "tok"

        await client.async_set_property("cn.iot.dreame.tech", "123456789", 2, 4, 6)
        self.assertEqual(
            session.calls[-1]["url"],
            "https://cn.iot.dreame.tech:13267/dreame-iot-com-cn/device/sendCommand",
        )
        self.assertEqual(
            session.calls[-1]["json"]["data"]["params"],
            [{"siid": 2, "piid": 4, "value": 6}],
        )

        await client.async_action("cn.iot.dreame.tech", "123456789", 2, 1, [{"piid": 1, "value": 1}])
        self.assertEqual(
            session.calls[-1]["json"]["data"]["params"],
            {"did": "123456789", "siid": 2, "aiid": 1, "in": [{"piid": 1, "value": 1}]},
        )

        with self.assertRaises(P.DreameCommandError):
            await client.async_set_property("cn.iot.dreame.tech", "123456789", 2, 4, 99)


class TestEntitiesFlowAndLifecycle(unittest.IsolatedAsyncioTestCase):
    """Verify HA lifecycle, flows, all 17 core unique_ids, fan math, sensors, and diagnostics."""

    async def test_setup_unload_runtime_data_and_auto_region_persist(self) -> None:
        entry = _live_entry(region=C.REGION_AUTO, options={})
        hass = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.async_create_task = lambda coro: asyncio.create_task(coro)

        def update_entry(target: ConfigEntry, *, data: dict[str, Any]) -> None:
            target.data = dict(data)

        hass.config_entries.async_update_entry = MagicMock(side_effect=update_entry)

        def handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "/oauth/token" in url:
                return _FakeResponse({"access_token": "tok", "region": "cn"}) if "cn." in url else _FakeResponse(status=401)
            if "/devOTCInfo" in url:
                return _FakeResponse({"code": 0, "data": {"fw": "2.0.1"}})
            return _FakeResponse({"code": 0, "data": [{"key": "2.1", "value": 1}, {"key": "3.5", "value": 14}]})

        with patch(
            "custom_components.dreame_airpurifier.coordinator.async_get_clientsession",
            return_value=_FakeSession(handler),
        ):
            ok = await dreame_init.async_setup_entry(hass, entry)

        self.assertTrue(ok)
        self.assertIsInstance(entry.runtime_data, DreameCoordinator)
        self.assertEqual(entry.data[C.CONF_REGION], "cn")
        self.assertEqual(entry._update_listeners, [])  # OptionsFlowWithReload, NO add_update_listener
        self.assertEqual(
            dreame_init.PLATFORMS,
            (Platform.FAN, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH),
        )
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(entry, dreame_init.PLATFORMS)

        # Schedule a follow-up task and verify unload shuts it down cleanly
        entry.runtime_data.async_schedule_follow_up_refresh(delays=(60.0,))
        self.assertIsNotNone(entry.runtime_data._follow_up_task)
        unloaded = await dreame_init.async_unload_entry(hass, entry)
        self.assertTrue(unloaded)
        self.assertIsNone(entry.runtime_data._follow_up_task)

    async def test_coordinator_update_error_mapping(self) -> None:
        entry = _live_entry()
        hass = MagicMock()
        with patch(
            "custom_components.dreame_airpurifier.coordinator.async_get_clientsession",
            return_value=_FakeSession(lambda u, k: _FakeResponse(status=401)),
        ):
            coord = DreameCoordinator(hass, entry)
            with self.assertRaises(ConfigEntryAuthFailed):
                await coord._async_update_data()

        with patch(
            "custom_components.dreame_airpurifier.coordinator.async_get_clientsession",
            return_value=_FakeSession(lambda u, k: _FakeResponse(error=TimeoutError())),
        ):
            coord2 = DreameCoordinator(hass, entry)
            with self.assertRaises(UpdateFailed):
                await coord2._async_update_data()

    async def test_config_flow_reauth_and_options_flow_with_reload(self) -> None:
        devices_payload = [
            {
                "did": "123456789",
                "customName": "Living Room FP10",
                "model": "dreame.airp.u2513",
                "bindDomain": "cn.iot.dreame.tech",
                "mac": "AA:BB:CC:DD:EE:FF",
            }
        ]

        def flow_handler(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "/oauth/token" in url:
                return _FakeResponse({"access_token": "tok_flow", "region": "cn"})
            return _FakeResponse({"code": 0, "data": {"page": {"records": devices_payload}}})

        flow = DreameConfigFlow()
        flow.hass = MagicMock()
        form = await flow.async_step_user()
        self.assertEqual(form["step_id"], "user")
        pw_selector = next(v for k, v in form["data_schema"].schema.items() if k.schema == CONF_PASSWORD)
        self.assertIsInstance(pw_selector, TextSelector)
        self.assertEqual(pw_selector.config.type, TextSelectorType.PASSWORD)

        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(flow_handler),
        ):
            step2 = await flow.async_step_user(
                {CONF_USERNAME: "u@example.com", CONF_PASSWORD: "pw", C.CONF_REGION: "cn"}
            )
            self.assertEqual(step2["step_id"], "select_device")
            created = await flow.async_step_select_device({C.CONF_DID: "123456789"})

        self.assertEqual(created["type"], "create_entry")
        self.assertEqual(
            sorted(created["data"].keys()),
            ["bind_domain", "device_model", "device_name", "did", "mac", "password", "region", "username"],
        )

        # Reauth flow
        entry = _live_entry()
        reauth_flow = DreameConfigFlow()
        reauth_flow.hass = MagicMock()
        reauth_flow._reauth_entry = entry
        reauth_form = await reauth_flow.async_step_reauth(entry.data)
        self.assertEqual(reauth_form["step_id"], "reauth_confirm")
        reauth_pw = next(v for k, v in reauth_form["data_schema"].schema.items() if k.schema == CONF_PASSWORD)
        self.assertIsInstance(reauth_pw, TextSelector)
        self.assertEqual(reauth_pw.config.type, TextSelectorType.PASSWORD)

        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(flow_handler),
        ):
            done = await reauth_flow.async_step_reauth_confirm(
                {CONF_USERNAME: "u2@example.com", CONF_PASSWORD: "pw2", C.CONF_REGION: "cn"}
            )
        self.assertEqual(done["type"], "abort")
        self.assertEqual(done["reason"], "reauth_successful")
        self.assertEqual(entry.data[CONF_USERNAME], "u2@example.com")

        # OptionsFlowWithReload: no custom __init__, only scan_interval 15..300
        opt_flow = DreameConfigFlow.async_get_options_flow(entry)
        self.assertIsInstance(opt_flow, DreameOptionsFlow)
        self.assertIsInstance(opt_flow, OptionsFlowWithReload)
        self.assertNotIn("__init__", DreameOptionsFlow.__dict__)
        opt_flow._config_entry = entry
        opt_form = await opt_flow.async_step_init()
        field_keys = [k.schema for k in opt_form["data_schema"].schema]
        self.assertEqual(field_keys, [C.CONF_SCAN_INTERVAL])
        range_validator = next(iter(opt_form["data_schema"].schema.values())).validators[1]
        self.assertEqual((range_validator.min, range_validator.max), (15, 300))

        saved = await opt_flow.async_step_init({C.CONF_SCAN_INTERVAL: 999})
        self.assertEqual(saved["data"], {C.CONF_SCAN_INTERVAL: 300})
        saved_low = await opt_flow.async_step_init({C.CONF_SCAN_INTERVAL: 5})
        self.assertEqual(saved_low["data"], {C.CONF_SCAN_INTERVAL: 15})

    async def test_all_17_core_entities_unique_ids_fan_speed_sensors_and_errors(self) -> None:
        entry = _live_entry()
        hass = MagicMock()
        hass.async_create_task = lambda coro: asyncio.create_task(coro)
        with patch(
            "custom_components.dreame_airpurifier.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        ):
            coord = DreameCoordinator(hass, entry)

        coord.client.async_action = AsyncMock()
        coord.client.async_set_property = AsyncMock()
        coord.async_schedule_follow_up_refresh = MagicMock()

        did = "123456789"
        fan = DreameFanEntity(coord)
        number = DreameFanSpeedNumber(coord)
        select = DreameWindModeSelect(coord)
        switch = DreameChildLockSwitch(coord)
        sensors = [DreameSensorEntity(coord, desc) for desc in SENSOR_DESCRIPTIONS]

        all_unique_ids = {
            fan._attr_unique_id,
            number._attr_unique_id,
            select._attr_unique_id,
            switch._attr_unique_id,
            *(s._attr_unique_id for s in sensors),
        }
        expected_unique_ids = {
            f"{did}_fan",
            f"{did}_number_fan_speed",
            f"{did}_select_wind_mode",
            f"{did}_switch_child_lock",
            *(
                f"{did}_sensor_{key}"
                for key in (
                    "pm25", "pm10", "tvoc", "aq", "air_quality_level", "display_value",
                    "current_speed", "hepa_filter_life", "hepa_filter_life_days",
                    "combbox_life", "combbox_life_days", "status_code", "error_code",
                )
            ),
        }
        self.assertEqual(len(all_unique_ids), 17)
        self.assertEqual(all_unique_ids, expected_unique_ids)
        self.assertNotIn(f"{did}_diagnostics", all_unique_ids)

        # Fan features, naming, unknown state, percentage <-> speed 1..10 mapping
        self.assertIsNone(fan._attr_name)
        self.assertTrue(fan._attr_has_entity_name)
        self.assertEqual(
            fan._attr_supported_features,
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE,
        )
        self.assertEqual(fan._attr_speed_count, 10)
        self.assertIsNone(fan.is_on)
        self.assertIsNone(fan.percentage)

        # Unknown state: set_percentage powers on ONCE then writes speed 5 to 2.4
        await fan.async_set_percentage(50)
        self.assertEqual(coord.client.async_action.await_count, 1)
        coord.client.async_set_property.assert_awaited_once_with("cn.iot.dreame.tech", did, 2, 4, 5)
        self.assertTrue(fan.is_on)
        self.assertEqual(fan.percentage, 50)

        # Already ON: set_percentage writes 2.4 WITHOUT redundant power-on
        coord.client.async_action.reset_mock()
        coord.client.async_set_property.reset_mock()
        for level in range(1, 11):
            pct = level * 10
            await fan.async_set_percentage(pct)
            self.assertEqual(fan.percentage, pct)
        self.assertEqual(coord.client.async_action.await_count, 0)
        self.assertEqual(coord.client.async_set_property.await_count, 10)

        # Percentage 0 turns off
        await fan.async_set_percentage(0)
        self.assertFalse(fan.is_on)
        self.assertEqual(fan.percentage, 0)

        # turn_on(percentage=60, preset_mode="自定义") powers on ONCE, sets mode then speed
        coord.client.async_action.reset_mock()
        coord.client.async_set_property.reset_mock()
        coord.async_schedule_follow_up_refresh.reset_mock()
        await fan.async_turn_on(percentage=60, preset_mode="自定义")
        self.assertEqual(coord.client.async_action.await_count, 1)
        self.assertEqual(coord.client.async_set_property.await_count, 2)
        self.assertEqual(coord.client.async_set_property.await_args_list[0].args, ("cn.iot.dreame.tech", did, 2, 3, 3))
        self.assertEqual(coord.client.async_set_property.await_args_list[1].args, ("cn.iot.dreame.tech", did, 2, 4, 6))
        self.assertEqual(coord.async_schedule_follow_up_refresh.call_count, 1)

        with self.assertRaises(ValueError):
            await fan.async_set_preset_mode("invalid_mode")

        # Number, Select, Switch
        self.assertEqual((number._attr_native_min_value, number._attr_native_max_value, number._attr_native_step), (1.0, 10.0, 1.0))
        self.assertEqual(number._attr_mode, NumberMode.SLIDER)
        await number.async_set_native_value(8.0)
        self.assertEqual(number.native_value, 8.0)

        await select.async_select_option("宠物模式")
        self.assertEqual(select.current_option, "宠物模式")
        with self.assertRaises(HomeAssistantError):
            await select.async_select_option("unknown")

        await switch.async_turn_on()
        self.assertTrue(switch.is_on)
        await switch.async_turn_off()
        self.assertFalse(switch.is_on)

        # Sensor units, device classes, state classes, entity categories, and decoding
        coord.async_set_updated_data(
            P.DreameState(
                descriptor=coord.descriptor,
                properties={
                    "2.1": 1, "2.2": 0, "2.4": "7", "3.4": "2",
                    "3.5": "15", "3.6": 28, "3.7": 120, "3.8": 95, "3.13": 15,
                    "4.1": 86, "4.2": 140, "4.4": 74, "4.5": 60,
                },
                otc_info={"fw": "1.2.3", "localIp": "192.168.1.99", "bssid": "11:22:33:44:55:66"},
            )
        )
        by_key = {s.entity_description.key: s for s in sensors}
        self.assertEqual(by_key["pm25"].entity_description.device_class, SensorDeviceClass.PM25)
        self.assertEqual(by_key["pm25"].entity_description.native_unit_of_measurement, UnitOfDensity.MICROGRAMS_PER_CUBIC_METER)
        self.assertEqual(by_key["pm25"].entity_description.state_class, SensorStateClass.MEASUREMENT)
        self.assertEqual(by_key["pm25"].native_value, 15)

        self.assertEqual(by_key["pm10"].entity_description.device_class, SensorDeviceClass.PM10)
        self.assertEqual(by_key["pm10"].entity_description.native_unit_of_measurement, UnitOfDensity.MICROGRAMS_PER_CUBIC_METER)
        self.assertEqual(by_key["tvoc"].entity_description.native_unit_of_measurement, UnitOfDensity.MICROGRAMS_PER_CUBIC_METER)
        self.assertEqual(by_key["tvoc"].entity_description.state_class, SensorStateClass.MEASUREMENT)
        self.assertEqual(by_key["air_quality_level"].native_value, "良")
        self.assertEqual(by_key["status_code"].native_value, "工作中")
        self.assertEqual(by_key["current_speed"].native_value, 7)

        for key in ("hepa_filter_life", "combbox_life"):
            self.assertEqual(by_key[key].entity_description.native_unit_of_measurement, PERCENTAGE)
            self.assertEqual(by_key[key].entity_description.entity_category, EntityCategory.DIAGNOSTIC)
        for key in ("hepa_filter_life_days", "combbox_life_days"):
            self.assertEqual(by_key[key].entity_description.native_unit_of_measurement, UnitOfTime.DAYS)
            self.assertEqual(by_key[key].entity_description.entity_category, EntityCategory.DIAGNOSTIC)
        for key in ("status_code", "error_code"):
            self.assertEqual(by_key[key].entity_description.entity_category, EntityCategory.DIAGNOSTIC)

        # Auth and API errors across all control platforms
        for exc_cls, expect_reauth in ((P.DreameAuthError, True), (P.DreameCommandError, False)):
            for ent, coro_fn in (
                (fan, lambda: fan.async_turn_off()),
                (number, lambda: number.async_set_native_value(3)),
                (select, lambda: select.async_select_option("智能净化")),
                (switch, lambda: switch.async_turn_on()),
            ):
                entry.reauth_started = False
                coord.client.async_action.side_effect = exc_cls("boom")
                coord.client.async_set_property.side_effect = exc_cls("boom")
                with self.assertRaises(HomeAssistantError):
                    await coro_fn()
                self.assertEqual(entry.reauth_started, expect_reauth, f"{type(ent).__name__} / {exc_cls.__name__}")

        # Diagnostics redaction
        entry.runtime_data = coord
        diag = await async_get_config_entry_diagnostics(hass, entry)
        self.assertEqual(diag["entry"]["data"][CONF_USERNAME], "**REDACTED**")
        self.assertEqual(diag["entry"]["data"][CONF_PASSWORD], "**REDACTED**")
        self.assertEqual(diag["entry"]["data"][C.CONF_DID], "**REDACTED**")
        self.assertEqual(diag["entry"]["data"][C.CONF_MAC], "**REDACTED**")
        self.assertEqual(diag["entry"]["data"][C.CONF_BIND_DOMAIN], "**REDACTED**")
        self.assertEqual(diag["otc_info"]["localIp"], "**REDACTED**")
        self.assertEqual(diag["otc_info"]["bssid"], "**REDACTED**")
        self.assertEqual(diag["otc_info"]["fw"], "1.2.3")
        self.assertEqual(diag["properties"]["3.5"], "15")

    def test_manifest_and_translations_alignment(self) -> None:
        manifest = json.loads((COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain"], "dreame_airpurifier")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["iot_class"], "cloud_polling")

        strings = json.loads((COMPONENT_DIR / "strings.json").read_text(encoding="utf-8"))
        en = json.loads((COMPONENT_DIR / "translations" / "en.json").read_text(encoding="utf-8"))
        zh = json.loads((COMPONENT_DIR / "translations" / "zh-Hans.json").read_text(encoding="utf-8"))

        def key_tree(obj: Any) -> Any:
            return {k: key_tree(v) for k, v in obj.items()} if isinstance(obj, dict) else True

        self.assertEqual(key_tree(strings), key_tree(en))
        self.assertEqual(key_tree(strings), key_tree(zh))
        self.assertEqual(set(strings["entity"]["sensor"]), {d.key for d in SENSOR_DESCRIPTIONS})
        self.assertIn("fan_speed", strings["entity"]["number"])
        self.assertIn("wind_mode", strings["entity"]["select"])
        self.assertIn("child_lock", strings["entity"]["switch"])

    async def test_legacy_options_graceful_and_config_flow_errors_and_fan_unknown_speed(self) -> None:
        # Legacy options with old reverse-engineering keys must not break coordinator or options flow
        legacy_opts_entry = _live_entry(
            options={"watched_keys": "2.1,3.5", "sensor_mappings": "{}", "scan_interval": 45}
        )
        hass = MagicMock()
        with patch(
            "custom_components.dreame_airpurifier.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        ):
            coord = DreameCoordinator(hass, legacy_opts_entry)
        self.assertEqual(coord.update_interval.total_seconds(), 45)

        # Fan on with missing or zero speed returns None (never fabricates 100)
        fan = DreameFanEntity(coord)
        coord.async_set_updated_data(P.DreameState(coord.descriptor, properties={"2.1": 1}))
        self.assertTrue(fan.is_on)
        self.assertIsNone(fan.percentage)
        coord.async_set_updated_data(P.DreameState(coord.descriptor, properties={"2.1": 1, "2.4": 0}))
        self.assertIsNone(fan.percentage)

        # Config flow error branches
        flow = DreameConfigFlow()
        flow.hass = MagicMock()
        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(lambda u, k: _FakeResponse(status=401)),
        ):
            res = await flow.async_step_user({CONF_USERNAME: "u", CONF_PASSWORD: "bad", C.CONF_REGION: "cn"})
        self.assertEqual(res["errors"], {"base": "invalid_auth"})

        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(lambda u, k: _FakeResponse(error=TimeoutError())),
        ):
            res = await flow.async_step_user({CONF_USERNAME: "u", CONF_PASSWORD: "p", C.CONF_REGION: "cn"})
        self.assertEqual(res["errors"], {"base": "cannot_connect"})

        def empty_devices(url: str, kwargs: dict[str, Any]) -> _FakeResponse:
            if "/oauth/token" in url:
                return _FakeResponse({"access_token": "tok", "region": "cn"})
            return _FakeResponse({"code": 0, "data": {"page": {"records": []}}})

        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(empty_devices),
        ):
            res = await flow.async_step_user({CONF_USERNAME: "u", CONF_PASSWORD: "p", C.CONF_REGION: "cn"})
        self.assertEqual(res["errors"], {"base": "no_devices"})

        # Reauth missing configured device
        reauth_flow = DreameConfigFlow()
        reauth_flow.hass = MagicMock()
        reauth_flow._reauth_entry = _live_entry()
        with patch(
            "custom_components.dreame_airpurifier.config_flow.async_get_clientsession",
            return_value=_FakeSession(empty_devices),
        ):
            res = await reauth_flow.async_step_reauth_confirm(
                {CONF_USERNAME: "u", CONF_PASSWORD: "p", C.CONF_REGION: "cn"}
            )
        self.assertEqual(res["errors"], {"base": "reauth_device_missing"})


if __name__ == "__main__":
    unittest.main()
