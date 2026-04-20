from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "dreame_smartlife"

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

DEFAULT_NAME = "Dreame Air Purifier FP10"
REGION_AUTO = "auto"
REGION_OPTIONS: dict[str, str] = {
    REGION_AUTO: "Auto detect",
    "eu": "Europe (eu)",
    "us": "United States (us)",
    "cn": "China (cn)",
    "ru": "Russia (ru)",
    "sg": "Singapore (sg)",
    "kr": "Korea (kr)",
}
KNOWN_REGIONS: tuple[str, ...] = tuple(region for region in REGION_OPTIONS if region != REGION_AUTO)
DEFAULT_REGION = REGION_AUTO
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_PROBE_MAX_SIID = 8
DEFAULT_PROBE_MAX_PIID = 16
DEFAULT_PROBE_CHUNK_SIZE = 20
MIN_SCAN_INTERVAL = 15

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

CONF_BIND_DOMAIN = "bind_domain"
CONF_DID = "did"
CONF_DEVICE_MODEL = "device_model"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_REGION = "region"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_WATCHED_KEYS = "watched_keys"
CONF_SENSOR_MAPPINGS = "sensor_mappings"
CONF_SWITCH_MAPPINGS = "switch_mappings"
CONF_SELECT_MAPPINGS = "select_mappings"
CONF_NUMBER_MAPPINGS = "number_mappings"
CONF_FAN_ENTITY_NAME = "fan_entity_name"
CONF_FAN_POWER_KEY = "fan_power_key"
CONF_FAN_POWER_ON_VALUE = "fan_power_on_value"
CONF_FAN_POWER_OFF_VALUE = "fan_power_off_value"
CONF_FAN_STATUS_KEY = "fan_status_key"
CONF_FAN_STATUS_ON_VALUE = "fan_status_on_value"
CONF_FAN_STATUS_OFF_VALUE = "fan_status_off_value"
CONF_FAN_SPEED_KEY = "fan_speed_key"
CONF_FAN_SPEED_MAP = "fan_speed_map"
CONF_FAN_POWER_ACTION_SIID = "fan_power_action_siid"
CONF_FAN_POWER_ACTION_AIID = "fan_power_action_aiid"
CONF_FAN_POWER_ACTION_PIID = "fan_power_action_piid"
CONF_PROBE_MAX_SIID = "probe_max_siid"
CONF_PROBE_MAX_PIID = "probe_max_piid"

ATTR_BIND_DOMAIN = "bind_domain"
ATTR_DEVICE = "device"
ATTR_DEVICE_INFO = "device_info"
ATTR_DISCOVERED_PROPERTIES = "discovered_properties"
ATTR_LAST_PROBE_AT = "last_probe_at"
ATTR_OTC_INFO = "otc_info"
ATTR_PROPERTIES = "properties"
ATTR_RAW_RESPONSE = "raw_response"
ATTR_WATCHED_PROPERTIES = "watched_properties"

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}_probe_"

SERVICE_PROBE_PROPERTIES = "probe_properties"
SERVICE_SEND_RAW_COMMAND = "send_raw_command"

USER_AGENT = "Dreame_Smarthome/1.5.59 (iPhone; iOS 16.0; Scale/3.00)"
DREAME_RLC = "1c80b3787b2266776bcdc481f37d8fa42ba10a30af81a6df-1"
BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"

TOKEN_PATH = "/dreame-auth/oauth/token"
DEVICE_LIST_PATH = "/dreame-user-iot/iotuserbind/device/listV2"
DEVICE_INFO_PATH = "/dreame-user-iot/iotuserbind/device/info"
OTC_INFO_PATH = "/dreame-user-iot/iotstatus/devOTCInfo"
PROPS_PATH = "/dreame-user-iot/iotstatus/props"
HISTORY_PATH = "/dreame-user-iot/iotstatus/history"
SEND_COMMAND_PREFIX = "/dreame-iot-com-"
SEND_COMMAND_SUFFIX = "/device/sendCommand"
