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
MQTT_FALLBACK_SCAN_INTERVAL = 300
MQTT_KEEPALIVE = 60
MQTT_DEFAULT_PORT = 19973
MQTT_RECONNECT_DELAYS: tuple[float, ...] = (2.0, 5.0, 10.0, 30.0, 60.0)
TOKEN_REFRESH_MARGIN = 300.0
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
DEVICE_INFO_PATH = "/dreame-user-iot/iotuserbind/device/info"
OTC_INFO_PATH = "/dreame-user-iot/iotstatus/devOTCInfo"
PROPS_PATH = "/dreame-user-iot/iotstatus/props"
SEND_COMMAND_PREFIX = "/dreame-iot-com-"
SEND_COMMAND_SUFFIX = "/device/sendCommand"

# Public Dreame IoT MQTT broker Root CA (1970-2969 self-signed root used by *.mt.*.iot.dreame.tech:19973)
DREAME_CLIENT_ROOT_CA = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDDzCCAfegAwIBAgIJAPvMK3fFXUEgMA0GCSqGSIb3DQEBCwUAMB0xGzAZBgNV\n"
    "BAMMEkdsb2JhbFNpZ24gUm9vdCBDQTAgFw02OTEyMzExNjAwMDBaGA8yOTY5MDUw\n"
    "MjE2MDAwMFowHTEbMBkGA1UEAwwSR2xvYmFsU2lnbiBSb290IENBMIIBIjANBgkq\n"
    "hkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtdVI+1rZpIpB8YlmnzWFnvJyGzlBbxEh\n"
    "RwgSanox6OypwX27htEFFJzMxz5YGv9nABm3b3SUB+0zcAkJYw/Q9lZoT1w0m9Cr\n"
    "5KJMxofpD8JjsZWFE5hvJ5NIyRS4tOgimGsIfvHGMzihZ9sLnq7kBtX7u5hIv/A5\n"
    "eSvifaroS2NombTFMQrV6ZNIvpFALbMUbp02+mexm7P59c7OzJVupQAWJSFOepIu\n"
    "UwhyYLe1oR/HTiKcIuzDSp49QxhSNYuLpSUOYo/YU4GTMoKEhXD7u+AyeOzuHrnV\n"
    "H7+/U7TlXFtMkyt+ZwQw+s8+/jzi4v9jG5XL82uVbr2FN0EC0PEhrwIDAQABo1Aw\n"
    "TjAdBgNVHQ4EFgQUQXiLQz2aun8vl2Hy1RCja8nZ4qMwHwYDVR0jBBgwFoAUQXiL\n"
    "Qz2aun8vl2Hy1RCja8nZ4qMwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC\n"
    "AQEAaAuVj1RNRRXfV7wk2VtLr6aKPoi7mlG9OSijHxAbmwV1KMyGR6gUpqToBpe/\n"
    "xQN+AjJK1Unex0hkN7+RZhpe8ajWqtniZ+oq9Xd+be0JW2KqZmA18r5arJj4DiCt\n"
    "Asa557/RNxuiIMc/uwvPtVq2C9uPX562esS02e2bRODH+l+aKcFzeCKotccJGej7\n"
    "NrfwypYpmoqrwko/4pe9cMBc3O1CLl2ZYy+YreHMFitmL6xGnC4a6HuTcZgK/ntj\n"
    "zewB8u+e2dMQwnBclahtLtb8oMmCHCWlgMTVU1MrjlWldvULalpMnIE5gsHKNXeC\n"
    "z0PJitlGIfun4TuQQhVCf5B2aA==\n"
    "-----END CERTIFICATE-----\n"
)

# FP10 (dreame.airp.u2513) MIOT SIID.PIID keys & hardware values
PROP_STATUS, PROP_ERROR_CODE, PROP_WIND_MODE, PROP_FAN_SPEED, PROP_CHILD_LOCK = (
    "2.1", "2.2", "2.3", "2.4", "2.5",
)
PROP_HUMIDITY, PROP_TEMPERATURE = "3.2", "3.3"
PROP_AIR_QUALITY_LEVEL, PROP_PM25, PROP_PM10, PROP_TVOC, PROP_AQ, PROP_DISPLAY_VALUE = (
    "3.4", "3.5", "3.6", "3.7", "3.8", "3.13",
)
PROP_HEPA_FILTER_LIFE, PROP_HEPA_FILTER_DAYS, PROP_COMBBOX_LIFE, PROP_COMBBOX_DAYS = (
    "4.1", "4.2", "4.4", "4.5",
)
PROP_LIGHT_BRIGHTNESS = "6.6"
PROP_KEY_SOUND_LEGACY = "6.7"
PROP_TIMER_HOURS = "6.8"
PROP_CHILD_LOCK_V2 = "6.10"
PROP_AMBIENT_BREATHING = "6.12"
PROP_COLOR_TEMPERATURE = "6.13"
PROP_KEY_SOUND = "6.17"
PROP_SELF_CLEAN_STATUS = "7.1"

FP10_V2_MCU_MIN = 1062

FP10_POLLED_KEYS: tuple[str, ...] = (
    PROP_STATUS, PROP_ERROR_CODE, PROP_WIND_MODE, PROP_FAN_SPEED, PROP_CHILD_LOCK,
    PROP_HUMIDITY, PROP_TEMPERATURE,
    PROP_AIR_QUALITY_LEVEL, PROP_PM25, PROP_PM10, PROP_TVOC, PROP_AQ, PROP_DISPLAY_VALUE,
    PROP_HEPA_FILTER_LIFE, PROP_HEPA_FILTER_DAYS, PROP_COMBBOX_LIFE, PROP_COMBBOX_DAYS,
    PROP_LIGHT_BRIGHTNESS, PROP_KEY_SOUND_LEGACY, PROP_TIMER_HOURS,
    PROP_CHILD_LOCK_V2, PROP_AMBIENT_BREATHING, PROP_COLOR_TEMPERATURE, PROP_KEY_SOUND,
    PROP_SELF_CLEAN_STATUS,
)

FP10_STATUS_ON, FP10_STATUS_OFF = 1, 2
FP10_POWER_ACTION_SIID, FP10_POWER_ACTION_AIID, FP10_POWER_ACTION_PIID = 2, 1, 1
FP10_POWER_ON_VALUE, FP10_POWER_OFF_VALUE = 1, 0
FP10_CHILD_LOCK_ON, FP10_CHILD_LOCK_OFF = 1, 0
FP10_BOOL_ON, FP10_BOOL_OFF = 1, 0
FP10_SPEED_MIN, FP10_SPEED_MAX = 1, 10
FP10_SPEED_RANGE: tuple[int, int] = (FP10_SPEED_MIN, FP10_SPEED_MAX)
FP10_TIMER_MIN, FP10_TIMER_MAX = 0, 12

# Filter & Self-cleaning actions (verified against official u2513 plugin bundle)
FP10_FILTER_RESET_SIID = 4
FP10_HEPA_RESET_AIID = 1
FP10_COMBBOX_RESET_AIID = 3
FP10_SELF_CLEAN_SIID = 7
FP10_SELF_CLEAN_START_AIID = 1
FP10_SELF_CLEAN_CONFIRM_AIID = 2

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
LIGHT_BRIGHTNESS_OPTIONS: Mapping[str, int] = MappingProxyType(
    {"off": 0, "dim": 30, "natural": 50, "bright": 80}
)
COLOR_TEMPERATURE_OPTIONS: Mapping[str, int] = MappingProxyType(
    {"warm": 2700, "neutral": 4000, "cool": 5700}
)
SELF_CLEAN_STATUS_MAP: Mapping[str, str] = MappingProxyType(
    {"0": "idle", "1": "running", "2": "complete", "3": "error"}
)


def clamp_scan_interval(value: Any) -> int:
    """Coerce and clamp polling interval to [MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL]."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, parsed))
