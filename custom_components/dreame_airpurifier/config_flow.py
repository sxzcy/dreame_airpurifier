from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
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

_LOGGER = logging.getLogger(__name__)


class DreameSmartlifeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._session = None
        self._client: DreameSmartlifeClient | None = None
        self._credentials: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []

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
                    return await self.async_step_select_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(REGION_OPTIONS),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL)
                ),
                vol.Optional(CONF_WATCHED_KEYS, default=options.get(CONF_WATCHED_KEYS, "")): str,
                vol.Optional(CONF_SENSOR_MAPPINGS, default=options.get(CONF_SENSOR_MAPPINGS, "")): str,
                vol.Optional(CONF_SWITCH_MAPPINGS, default=options.get(CONF_SWITCH_MAPPINGS, "")): str,
                vol.Optional(CONF_SELECT_MAPPINGS, default=options.get(CONF_SELECT_MAPPINGS, "")): str,
                vol.Optional(CONF_NUMBER_MAPPINGS, default=options.get(CONF_NUMBER_MAPPINGS, "")): str,
                vol.Optional(CONF_FAN_ENTITY_NAME, default=options.get(CONF_FAN_ENTITY_NAME, "Purifier")): str,
                vol.Optional(CONF_FAN_POWER_KEY, default=options.get(CONF_FAN_POWER_KEY, "")): str,
                vol.Optional(CONF_FAN_POWER_ON_VALUE, default=options.get(CONF_FAN_POWER_ON_VALUE, "1")): str,
                vol.Optional(CONF_FAN_POWER_OFF_VALUE, default=options.get(CONF_FAN_POWER_OFF_VALUE, "0")): str,
                vol.Optional(CONF_FAN_STATUS_KEY, default=options.get(CONF_FAN_STATUS_KEY, "")): str,
                vol.Optional(CONF_FAN_STATUS_ON_VALUE, default=options.get(CONF_FAN_STATUS_ON_VALUE, "1")): str,
                vol.Optional(CONF_FAN_STATUS_OFF_VALUE, default=options.get(CONF_FAN_STATUS_OFF_VALUE, "")): str,
                vol.Optional(CONF_FAN_SPEED_KEY, default=options.get(CONF_FAN_SPEED_KEY, "")): str,
                vol.Optional(CONF_FAN_SPEED_MAP, default=options.get(CONF_FAN_SPEED_MAP, "")): str,
                vol.Optional(CONF_FAN_POWER_ACTION_SIID, default=options.get(CONF_FAN_POWER_ACTION_SIID, "")): str,
                vol.Optional(CONF_FAN_POWER_ACTION_AIID, default=options.get(CONF_FAN_POWER_ACTION_AIID, "")): str,
                vol.Optional(CONF_FAN_POWER_ACTION_PIID, default=options.get(CONF_FAN_POWER_ACTION_PIID, "")): str,
                vol.Optional(
                    CONF_PROBE_MAX_SIID, default=options.get(CONF_PROBE_MAX_SIID, DEFAULT_PROBE_MAX_SIID)
                ): vol.All(int, vol.Range(min=1, max=64)),
                vol.Optional(
                    CONF_PROBE_MAX_PIID, default=options.get(CONF_PROBE_MAX_PIID, DEFAULT_PROBE_MAX_PIID)
                ): vol.All(int, vol.Range(min=1, max=256)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
