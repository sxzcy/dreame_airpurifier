"""Constants for the Dreame FP10 Air Purifier integration."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

DOMAIN = "dreame_airpurifier"
DEFAULT_NAME = "Dreame FP10"
FP10_MODEL = "dreame.airp.u2513"

REGION_AUTO = "auto"
DEFAULT_REGION = REGION_AUTO
REGION_OPTIONS: dict[str, str] = {
    REGION_AUTO: "Auto detect",
    "eu": "Europe (eu)",
    "us": "United States (us)",
    "cn": "China (cn)",
    "ru": "Russia (ru)",
    "sg": "Singapore (sg)",
    "kr": "Korea (kr)",
}
KNOWN_REGIONS: tuple[str, ...] = ("eu", "us", "cn", "ru", "sg", "kr")

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 300
OTC_REFRESH_INTERVAL = 1800
DEFAULT_REQUEST_TIMEOUT = 20
AUTO_REGION_CONNECT_TIMEOUT = 3
AUTO_REGION_TOTAL_TIMEOUT = 5

CONF_BIND_DOMAIN = "bind_domain"
CONF_DID = "did"
CONF_DEVICE_MODEL = "device_model"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_REGION = "region"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_TENANT_ID = "000000"
USER_AGENT = "Dreame_Smarthome/1.5.59 (iPhone; iOS 16.0; Scale/3.00)"
DREAME_RLC = "1c80b3787b2266776bcdc481f37d8fa42ba10a30af81a6df-1"
BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"

TOKEN_PATH = "/dreame-auth/oauth/token"
DEVICE_LIST_PATH = "/dreame-user-iot/iotuserbind/device/listV2"
OTC_INFO_PATH = "/dreame-user-iot/iotstatus/devOTCInfo"
PROPS_PATH = "/dreame-user-iot/iotstatus/props"
SEND_COMMAND_PREFIX = "/dreame-iot-com-"
SEND_COMMAND_SUFFIX = "/device/sendCommand"

# FP10 (dreame.airp.u2513) MIOT SIID.PIID keys & hardware values
PROP_STATUS, PROP_ERROR_CODE, PROP_WIND_MODE, PROP_FAN_SPEED, PROP_CHILD_LOCK = (
    "2.1", "2.2", "2.3", "2.4", "2.5",
)
PROP_AIR_QUALITY_LEVEL, PROP_PM25, PROP_PM10, PROP_TVOC, PROP_AQ, PROP_DISPLAY_VALUE = (
    "3.4", "3.5", "3.6", "3.7", "3.8", "3.13",
)
PROP_HEPA_FILTER_LIFE, PROP_HEPA_FILTER_DAYS, PROP_COMBBOX_LIFE, PROP_COMBBOX_DAYS = (
    "4.1", "4.2", "4.4", "4.5",
)
FP10_POLLED_KEYS: tuple[str, ...] = (
    PROP_STATUS, PROP_ERROR_CODE, PROP_WIND_MODE, PROP_FAN_SPEED, PROP_CHILD_LOCK,
    PROP_AIR_QUALITY_LEVEL, PROP_PM25, PROP_PM10, PROP_TVOC, PROP_AQ,
    PROP_DISPLAY_VALUE, PROP_HEPA_FILTER_LIFE, PROP_HEPA_FILTER_DAYS,
    PROP_COMBBOX_LIFE, PROP_COMBBOX_DAYS,
)

FP10_STATUS_ON, FP10_STATUS_OFF = 1, 2
FP10_POWER_ACTION_SIID, FP10_POWER_ACTION_AIID, FP10_POWER_ACTION_PIID = 2, 1, 1
FP10_POWER_ON_VALUE, FP10_POWER_OFF_VALUE = 1, 0
FP10_CHILD_LOCK_ON, FP10_CHILD_LOCK_OFF = 1, 0
FP10_SPEED_MIN, FP10_SPEED_MAX = 1, 10
FP10_SPEED_RANGE: tuple[int, int] = (FP10_SPEED_MIN, FP10_SPEED_MAX)

WIND_MODE_OPTIONS: Mapping[str, int] = MappingProxyType(
    {"智能净化": 0, "强净化": 1, "睡眠净化": 2, "自定义": 3, "宠物模式": 4}
)
FAN_PRESET_MODES: Mapping[str, int] = MappingProxyType(
    {"auto": 0, "强净化": 1, "睡眠净化": 2, "自定义": 3, "宠物模式": 4}
)
AIR_QUALITY_LEVEL_MAP: Mapping[str, str] = MappingProxyType(
    {"1": "优", "2": "良", "3": "中", "4": "差"}
)
STATUS_CODE_MAP: Mapping[str, str] = MappingProxyType({"1": "工作中", "2": "待机"})


def clamp_scan_interval(value: Any) -> int:
    """Coerce and clamp polling interval to [MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL]."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, parsed))
