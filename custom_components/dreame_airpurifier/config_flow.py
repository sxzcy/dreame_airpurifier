from __future__ import annotations

import json
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
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
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_SELECT_MAPPINGS,
    CONF_SENSOR_MAPPINGS,
    CONF_SWITCH_MAPPINGS,
    CONF_WATCHED_KEYS,
    DEFAULT_NAME,
    DEFAULT_PROBE_MAX_PIID,
    DEFAULT_PROBE_MAX_SIID,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    REGION_OPTIONS,
)
from .dreame.exceptions import DreameSmartlifeAuthError, DreameSmartlifeError
from .dreame.protocol import DreameSmartlifeClient
from .utils import parse_csv_keys, parse_key

JSON_OBJECT_OPTION_FIELDS = {
    CONF_SENSOR_MAPPINGS,
    CONF_SWITCH_MAPPINGS,
    CONF_SELECT_MAPPINGS,
    CONF_NUMBER_MAPPINGS,
    CONF_FAN_SPEED_MAP,
}
PROPERTY_KEY_OPTION_FIELDS = {
    CONF_FAN_POWER_KEY,
    CONF_FAN_STATUS_KEY,
    CONF_FAN_SPEED_KEY,
}
INTEGER_TEXT_OPTION_FIELDS = {
    CONF_FAN_POWER_ACTION_SIID,
    CONF_FAN_POWER_ACTION_AIID,
    CONF_FAN_POWER_ACTION_PIID,
}
TEXT_OPTION_FIELDS = {
    CONF_WATCHED_KEYS,
    CONF_FAN_ENTITY_NAME,
    CONF_FAN_POWER_ON_VALUE,
    CONF_FAN_POWER_OFF_VALUE,
    CONF_FAN_STATUS_ON_VALUE,
    CONF_FAN_STATUS_OFF_VALUE,
    *JSON_OBJECT_OPTION_FIELDS,
    *PROPERTY_KEY_OPTION_FIELDS,
    *INTEGER_TEXT_OPTION_FIELDS,
}


class OptionsValidationError(ValueError):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(reason)
        self.field = field
        self.reason = reason


def _option_string_default(options: dict[str, Any], key: str) -> str:
    value = options.get(key, "")
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _option_int_default(options: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(options.get(key, default))
    except (TypeError, ValueError):
        return default


def _normalize_text_option(key: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if key == CONF_WATCHED_KEYS:
        try:
            return ",".join(parse_csv_keys(text))
        except (AttributeError, TypeError, ValueError) as err:
            raise OptionsValidationError(key, "invalid_key") from err

    if key in PROPERTY_KEY_OPTION_FIELDS:
        try:
            parse_key(text)
        except (AttributeError, TypeError, ValueError) as err:
            raise OptionsValidationError(key, "invalid_key") from err
        return text

    if key in INTEGER_TEXT_OPTION_FIELDS:
        try:
            parsed = int(text)
        except (TypeError, ValueError) as err:
            raise OptionsValidationError(key, "invalid_number") from err
        if parsed <= 0:
            raise OptionsValidationError(key, "invalid_number")
        return str(parsed)

    if key in JSON_OBJECT_OPTION_FIELDS:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as err:
            raise OptionsValidationError(key, "invalid_json") from err
        if not isinstance(parsed, dict):
            raise OptionsValidationError(key, "invalid_json")
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))

    return text


def _normalize_options(user_input: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        CONF_SCAN_INTERVAL: max(int(user_input[CONF_SCAN_INTERVAL]), MIN_SCAN_INTERVAL),
        CONF_PROBE_MAX_SIID: int(user_input[CONF_PROBE_MAX_SIID]),
        CONF_PROBE_MAX_PIID: int(user_input[CONF_PROBE_MAX_PIID]),
    }
    for key in TEXT_OPTION_FIELDS:
        value = _normalize_text_option(key, user_input.get(key))
        if value is not None:
            normalized[key] = value
    return normalized


def _options_schema(options: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=_option_int_default(options, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
            vol.Optional(CONF_WATCHED_KEYS, default=_option_string_default(options, CONF_WATCHED_KEYS)): str,
            vol.Optional(CONF_SENSOR_MAPPINGS, default=_option_string_default(options, CONF_SENSOR_MAPPINGS)): str,
            vol.Optional(CONF_SWITCH_MAPPINGS, default=_option_string_default(options, CONF_SWITCH_MAPPINGS)): str,
            vol.Optional(CONF_SELECT_MAPPINGS, default=_option_string_default(options, CONF_SELECT_MAPPINGS)): str,
            vol.Optional(CONF_NUMBER_MAPPINGS, default=_option_string_default(options, CONF_NUMBER_MAPPINGS)): str,
            vol.Optional(CONF_FAN_ENTITY_NAME, default=_option_string_default(options, CONF_FAN_ENTITY_NAME)): str,
            vol.Optional(CONF_FAN_POWER_KEY, default=_option_string_default(options, CONF_FAN_POWER_KEY)): str,
            vol.Optional(CONF_FAN_POWER_ON_VALUE, default=_option_string_default(options, CONF_FAN_POWER_ON_VALUE)): str,
            vol.Optional(CONF_FAN_POWER_OFF_VALUE, default=_option_string_default(options, CONF_FAN_POWER_OFF_VALUE)): str,
            vol.Optional(CONF_FAN_STATUS_KEY, default=_option_string_default(options, CONF_FAN_STATUS_KEY)): str,
            vol.Optional(CONF_FAN_STATUS_ON_VALUE, default=_option_string_default(options, CONF_FAN_STATUS_ON_VALUE)): str,
            vol.Optional(CONF_FAN_STATUS_OFF_VALUE, default=_option_string_default(options, CONF_FAN_STATUS_OFF_VALUE)): str,
            vol.Optional(CONF_FAN_SPEED_KEY, default=_option_string_default(options, CONF_FAN_SPEED_KEY)): str,
            vol.Optional(CONF_FAN_SPEED_MAP, default=_option_string_default(options, CONF_FAN_SPEED_MAP)): str,
            vol.Optional(
                CONF_FAN_POWER_ACTION_SIID,
                default=_option_string_default(options, CONF_FAN_POWER_ACTION_SIID),
            ): str,
            vol.Optional(
                CONF_FAN_POWER_ACTION_AIID,
                default=_option_string_default(options, CONF_FAN_POWER_ACTION_AIID),
            ): str,
            vol.Optional(
                CONF_FAN_POWER_ACTION_PIID,
                default=_option_string_default(options, CONF_FAN_POWER_ACTION_PIID),
            ): str,
            vol.Optional(
                CONF_PROBE_MAX_SIID,
                default=_option_int_default(options, CONF_PROBE_MAX_SIID, DEFAULT_PROBE_MAX_SIID),
            ): vol.All(int, vol.Range(min=1, max=64)),
            vol.Optional(
                CONF_PROBE_MAX_PIID,
                default=_option_int_default(options, CONF_PROBE_MAX_PIID, DEFAULT_PROBE_MAX_PIID),
            ): vol.All(int, vol.Range(min=1, max=256)),
        }
    )


class DreameSmartlifeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._client: DreameSmartlifeClient | None = None
        self._credentials: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []
        self._reauth_entry_data: dict[str, Any] = {}

    def _user_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=self._reauth_entry_data.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(
                    CONF_REGION,
                    default=self._reauth_entry_data.get(CONF_REGION, DEFAULT_REGION),
                ): vol.In(REGION_OPTIONS),
            }
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        self._reauth_entry_data = dict(entry_data)
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            region = str(user_input[CONF_REGION]).lower()
            session = async_get_clientsession(self.hass)
            self._client = DreameSmartlifeClient(
                session,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                region,
            )
            try:
                await self._client.async_login()
                self._devices = await self._client.async_list_devices()
            except DreameSmartlifeAuthError:
                errors["base"] = "invalid_auth"
            except DreameSmartlifeError:
                errors["base"] = "cannot_connect"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    self._credentials = {**user_input, CONF_REGION: self._client.region}
                    if self.context.get("source") == SOURCE_REAUTH:
                        reauth_entry = self._get_reauth_entry()
                        did = str(reauth_entry.data[CONF_DID])
                        if not any(str(device.get("did")) == did for device in self._devices):
                            errors["base"] = "reauth_device_missing"
                        else:
                            await self.async_set_unique_id(did)
                            return self.async_update_reload_and_abort(
                                reauth_entry,
                                data_updates={
                                    CONF_USERNAME: user_input[CONF_USERNAME],
                                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                                    CONF_REGION: self._client.region,
                                },
                            )
                    return await self.async_step_select_device()

        return self.async_show_form(step_id="user", data_schema=self._user_schema(), errors=errors)

    async def async_step_select_device(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        device_map = {}
        for device in self._devices:
            did = str(device.get("did"))
            label = (
                f"{device.get('customName') or device.get('name') or DEFAULT_NAME}"
                f" [{device.get('model', 'unknown')}]"
            )
            device_map[did] = label

        if user_input is not None:
            selected = next(device for device in self._devices if str(device.get("did")) == user_input[CONF_DID])
            await self.async_set_unique_id(str(selected["did"]))
            self._abort_if_unique_id_configured()
            title = selected.get("customName") or selected.get("name") or selected.get("model") or DEFAULT_NAME
            data = {
                **self._credentials,
                CONF_DID: str(selected["did"]),
                CONF_DEVICE_NAME: title,
                CONF_DEVICE_MODEL: str(selected.get("model", "")),
                CONF_BIND_DOMAIN: str(selected.get("bindDomain", "")),
                CONF_MAC: selected.get("mac"),
            }
            return self.async_create_entry(title=title, data=data)

        schema = vol.Schema({vol.Required(CONF_DID): vol.In(device_map)})
        return self.async_show_form(step_id="select_device", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return DreameSmartlifeOptionsFlow(config_entry)


class DreameSmartlifeOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                return self.async_create_entry(title="", data=_normalize_options(user_input))
            except OptionsValidationError as err:
                errors[err.field] = err.reason

        options = user_input if errors and user_input is not None else self.config_entry.options
        return self.async_show_form(step_id="init", data_schema=_options_schema(options), errors=errors)
