from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..const import (
    CONF_BIND_DOMAIN,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_NAME,
    CONF_DID,
    CONF_FAN_ENTITY_NAME,
    CONF_FAN_POWER_KEY,
    CONF_FAN_POWER_ACTION_AIID,
    CONF_FAN_POWER_ACTION_PIID,
    CONF_FAN_POWER_ACTION_SIID,
    CONF_FAN_POWER_OFF_VALUE,
    CONF_FAN_POWER_ON_VALUE,
    CONF_FAN_STATUS_KEY,
    CONF_FAN_STATUS_OFF_VALUE,
    CONF_FAN_STATUS_ON_VALUE,
    CONF_FAN_SPEED_KEY,
    CONF_FAN_SPEED_MAP,
    CONF_MAC,
    CONF_NUMBER_MAPPINGS,
    CONF_PROBE_MAX_PIID,
    CONF_PROBE_MAX_SIID,
    CONF_SCAN_INTERVAL,
    CONF_SELECT_MAPPINGS,
    CONF_SENSOR_MAPPINGS,
    CONF_SWITCH_MAPPINGS,
    CONF_WATCHED_KEYS,
    DEFAULT_NAME,
    DEFAULT_PROBE_MAX_PIID,
    DEFAULT_PROBE_MAX_SIID,
    DEFAULT_SCAN_INTERVAL,
)
from ..utils import coerce_option_value, parse_csv_keys, parse_key, safe_json_loads


@dataclass(slots=True)
class DreameDeviceDescriptor:
    did: str
    name: str
    model: str
    bind_domain: str
    mac: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DreameFanMapping:
    entity_name: str
    power_key: str | None
    power_on_value: Any
    power_off_value: Any
    status_key: str | None
    status_on_value: Any
    status_off_value: Any
    speed_key: str | None
    speed_map: dict[str, Any]
    power_action_siid: int | None
    power_action_aiid: int | None
    power_action_piid: int | None


@dataclass(slots=True)
class DreameIntegrationOptions:
    scan_interval: int
    watched_keys: list[str]
    polled_keys: list[str]
    sensor_mappings: dict[str, dict[str, Any]]
    switch_mappings: dict[str, dict[str, Any]]
    number_mappings: dict[str, dict[str, Any]]
    select_mappings: dict[str, dict[str, Any]]
    fan_mapping: DreameFanMapping
    probe_max_siid: int
    probe_max_piid: int


MODEL_DEFAULTS: dict[str, dict[str, Any]] = {
    "dreame.airp.u2513": {
        CONF_WATCHED_KEYS: "2.1,2.2,2.3,2.4,2.5,3.4,3.5,3.6,3.7,3.8,3.13,4.1,4.2,4.4,4.5",
        CONF_SENSOR_MAPPINGS: {
            "display_value": {
                "key": "3.13",
                "name": "当前显示值",
                "icon": "mdi:blur",
            },
            "air_quality_level": {
                "key": "3.4",
                "name": "空气质量等级",
                "icon": "mdi:weather-windy",
                "value_map": {
                    "1": "优",
                    "2": "良",
                    "3": "中",
                    "4": "差"
                }
            },
            "pm25": {
                "key": "3.5",
                "name": "PM2.5",
                "unit": "ug/m3",
                "icon": "mdi:blur"
            },
            "pm10": {
                "key": "3.6",
                "name": "PM10",
                "unit": "ug/m3",
                "icon": "mdi:blur-linear"
            },
            "tvoc": {
                "key": "3.7",
                "name": "TVOC",
                "unit": "ug/m3",
                "icon": "mdi:molecule"
            },
            "aq": {
                "key": "3.8",
                "name": "AQ",
                "icon": "mdi:weather-windy"
            },
            "hepa_filter_life": {
                "key": "4.1",
                "name": "HEPA滤芯寿命",
                "unit": "%",
                "icon": "mdi:air-filter",
            },
            "hepa_filter_life_days": {
                "key": "4.2",
                "name": "HEPA滤芯剩余天数",
                "unit": "d",
                "icon": "mdi:calendar-clock",
            },
            "combbox_life": {
                "key": "4.4",
                "name": "集毛盒寿命",
                "unit": "%",
                "icon": "mdi:gauge",
            },
            "combbox_life_days": {
                "key": "4.5",
                "name": "集毛盒剩余天数",
                "unit": "d",
                "icon": "mdi:gauge",
            },
            "status_code": {
                "key": "2.1",
                "name": "运行状态代码",
                "icon": "mdi:information-outline",
                "value_map": {
                    "1": "工作中",
                    "2": "待机"
                }
            },
            "error_code": {
                "key": "2.2",
                "name": "错误代码",
                "icon": "mdi:alert-circle-outline",
            },
            "current_speed": {
                "key": "2.4",
                "name": "当前风速",
                "icon": "mdi:fan",
            },
        },
        CONF_SWITCH_MAPPINGS: {
            "child_lock": {
                "key": "2.5",
                "name": "童锁",
                "on": 1,
                "off": 0,
                "icon": "mdi:account-lock",
            }
        },
        CONF_NUMBER_MAPPINGS: {
            "fan_speed": {
                "key": "2.4",
                "name": "风速",
                "min": 1,
                "max": 10,
                "step": 1,
                "mode": "slider",
                "icon": "mdi:fan"
            }
        },
        CONF_SELECT_MAPPINGS: {
            "wind_mode": {
                "key": "2.3",
                "name": "净化模式",
                "options": {
                    "智能净化": 0,
                    "强净化": 1,
                    "睡眠净化": 2,
                    "自定义": 3,
                    "宠物模式": 4,
                },
            },
        },
        CONF_FAN_ENTITY_NAME: "净化器",
        CONF_FAN_POWER_KEY: "",
        CONF_FAN_SPEED_KEY: "2.3",
        CONF_FAN_SPEED_MAP: {
            "auto": 0,
            "强净化": 1,
            "睡眠净化": 2,
            "自定义": 3,
            "宠物模式": 4,
        },
        CONF_FAN_STATUS_KEY: "2.1",
        CONF_FAN_STATUS_ON_VALUE: 1,
        CONF_FAN_STATUS_OFF_VALUE: 2,
        CONF_FAN_POWER_ACTION_SIID: 2,
        CONF_FAN_POWER_ACTION_AIID: 1,
        CONF_FAN_POWER_ACTION_PIID: 1,
    }
}


def _append_key(target: list[str], key: Any) -> None:
    if not isinstance(key, str):
        return
    normalized = key.strip()
    if not normalized:
        return
    try:
        parse_key(normalized)
    except (AttributeError, TypeError, ValueError):
        return
    if normalized not in target:
        target.append(normalized)


def _extend_mapping_keys(target: list[str], mappings: dict[str, dict[str, Any]]) -> None:
    for mapping in mappings.values():
        if isinstance(mapping, dict):
            _append_key(target, mapping.get("key"))


def _build_polled_keys(
    watched_keys: list[str],
    sensor_mappings: dict[str, dict[str, Any]],
    switch_mappings: dict[str, dict[str, Any]],
    number_mappings: dict[str, dict[str, Any]],
    select_mappings: dict[str, dict[str, Any]],
    fan_mapping: DreameFanMapping,
) -> list[str]:
    keys = list(watched_keys)
    _extend_mapping_keys(keys, sensor_mappings)
    _extend_mapping_keys(keys, switch_mappings)
    _extend_mapping_keys(keys, number_mappings)
    _extend_mapping_keys(keys, select_mappings)
    _append_key(keys, fan_mapping.power_key)
    _append_key(keys, fan_mapping.status_key)
    _append_key(keys, fan_mapping.speed_key)
    return keys


def load_options(data: dict[str, Any], options: dict[str, Any]) -> DreameIntegrationOptions:
    merged: dict[str, Any] = {}
    model = str(data.get(CONF_DEVICE_MODEL, "")).lower()
    if model in MODEL_DEFAULTS:
        merged.update(MODEL_DEFAULTS[model])
    merged.update(data)
    merged.update(options)
    fan_speed_map = safe_json_loads(merged.get(CONF_FAN_SPEED_MAP, ""), {})
    sensor_mappings = merged.get(CONF_SENSOR_MAPPINGS, {})
    switch_mappings = merged.get(CONF_SWITCH_MAPPINGS, {})
    number_mappings = merged.get(CONF_NUMBER_MAPPINGS, {})
    select_mappings = merged.get(CONF_SELECT_MAPPINGS, {})
    if isinstance(sensor_mappings, str):
        sensor_mappings = safe_json_loads(sensor_mappings, {})
    if isinstance(switch_mappings, str):
        switch_mappings = safe_json_loads(switch_mappings, {})
    if isinstance(number_mappings, str):
        number_mappings = safe_json_loads(number_mappings, {})
    if isinstance(select_mappings, str):
        select_mappings = safe_json_loads(select_mappings, {})
    watched_keys = parse_csv_keys(merged.get(CONF_WATCHED_KEYS, ""))
    fan_mapping = DreameFanMapping(
        entity_name=merged.get(CONF_FAN_ENTITY_NAME, DEFAULT_NAME),
        power_key=merged.get(CONF_FAN_POWER_KEY) or None,
        power_on_value=coerce_option_value(str(merged.get(CONF_FAN_POWER_ON_VALUE, "1"))),
        power_off_value=coerce_option_value(str(merged.get(CONF_FAN_POWER_OFF_VALUE, "0"))),
        status_key=merged.get(CONF_FAN_STATUS_KEY) or None,
        status_on_value=coerce_option_value(str(merged.get(CONF_FAN_STATUS_ON_VALUE, "1"))),
        status_off_value=coerce_option_value(str(merged.get(CONF_FAN_STATUS_OFF_VALUE, ""))),
        speed_key=merged.get(CONF_FAN_SPEED_KEY) or None,
        speed_map=fan_speed_map if isinstance(fan_speed_map, dict) else {},
        power_action_siid=int(merged[CONF_FAN_POWER_ACTION_SIID]) if merged.get(CONF_FAN_POWER_ACTION_SIID) not in (None, "") else None,
        power_action_aiid=int(merged[CONF_FAN_POWER_ACTION_AIID]) if merged.get(CONF_FAN_POWER_ACTION_AIID) not in (None, "") else None,
        power_action_piid=int(merged[CONF_FAN_POWER_ACTION_PIID]) if merged.get(CONF_FAN_POWER_ACTION_PIID) not in (None, "") else None,
    )
    return DreameIntegrationOptions(
        scan_interval=max(int(merged.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)), 15),
        watched_keys=watched_keys,
        polled_keys=_build_polled_keys(
            watched_keys,
            sensor_mappings if isinstance(sensor_mappings, dict) else {},
            switch_mappings if isinstance(switch_mappings, dict) else {},
            number_mappings if isinstance(number_mappings, dict) else {},
            select_mappings if isinstance(select_mappings, dict) else {},
            fan_mapping,
        ),
        sensor_mappings=sensor_mappings if isinstance(sensor_mappings, dict) else {},
        switch_mappings=switch_mappings if isinstance(switch_mappings, dict) else {},
        number_mappings=number_mappings if isinstance(number_mappings, dict) else {},
        select_mappings=select_mappings if isinstance(select_mappings, dict) else {},
        fan_mapping=fan_mapping,
        probe_max_siid=int(merged.get(CONF_PROBE_MAX_SIID, DEFAULT_PROBE_MAX_SIID)),
        probe_max_piid=int(merged.get(CONF_PROBE_MAX_PIID, DEFAULT_PROBE_MAX_PIID)),
    )


def descriptor_from_entry(data: dict[str, Any]) -> DreameDeviceDescriptor:
    return DreameDeviceDescriptor(
        did=data[CONF_DID],
        name=data[CONF_DEVICE_NAME],
        model=data[CONF_DEVICE_MODEL],
        bind_domain=data[CONF_BIND_DOMAIN],
        mac=data.get(CONF_MAC),
        raw={},
    )
