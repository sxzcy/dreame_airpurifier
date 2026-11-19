"""Config and options flow for Dreame FP10 Air Purifier."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from . import const as C
from .client import DreameClient
from .protocol import DreameAuthError, DreameError


def _credentials_schema(username: str = "", region: str = C.DEFAULT_REGION) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=username): str,
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(C.CONF_REGION, default=region): vol.In(C.REGION_OPTIONS),
        }
    )


class DreameConfigFlow(ConfigFlow, domain=C.DOMAIN):
    """Handle config and reauth flows for Dreame FP10 Air Purifier."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []

    async def _async_validate_credentials(
        self, user_input: dict[str, Any]
    ) -> tuple[str | None, list[dict[str, Any]], dict[str, str]]:
        client = DreameClient(
            async_get_clientsession(self.hass),
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
            str(user_input[C.CONF_REGION]).lower(),
        )
        try:
            await client.async_login()
            devices = await client.async_list_devices()
        except DreameAuthError:
            return None, [], {"base": "invalid_auth"}
        except DreameError:
            return None, [], {"base": "cannot_connect"}
        return client.region, devices, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            resolved_region, devices, errors = await self._async_validate_credentials(user_input)
            if not errors:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._credentials = {
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        C.CONF_REGION: resolved_region,
                    }
                    self._devices = devices
                    return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema(
                username=(user_input or {}).get(CONF_USERNAME, ""),
                region=(user_input or {}).get(C.CONF_REGION, C.DEFAULT_REGION),
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        device_map = {
            str(d["did"]): f"{d.get('customName') or d.get('name') or C.DEFAULT_NAME} [{d.get('model', 'unknown')}]"
            for d in self._devices
            if d.get("did") is not None
        }
        if user_input is not None:
            selected = next(d for d in self._devices if str(d.get("did")) == user_input[C.CONF_DID])
            did = str(selected["did"])
            await self.async_set_unique_id(did)
            self._abort_if_unique_id_configured()
            title = str(
                selected.get("customName") or selected.get("name") or selected.get("model") or C.DEFAULT_NAME
            )
            return self.async_create_entry(
                title=title,
                data={
                    **self._credentials,
                    C.CONF_DID: did,
                    C.CONF_DEVICE_NAME: title,
                    C.CONF_DEVICE_MODEL: str(selected.get("model", "")),
                    C.CONF_BIND_DOMAIN: str(selected.get("bindDomain", "")),
                    C.CONF_MAC: selected.get("mac"),
                },
            )
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required(C.CONF_DID): vol.In(device_map)}),
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        reauth_entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            resolved_region, devices, errors = await self._async_validate_credentials(user_input)
            if not errors:
                did = str(reauth_entry.data[C.CONF_DID])
                matched = next((d for d in devices if str(d.get("did")) == did), None)
                if matched is None:
                    errors["base"] = "reauth_device_missing"
                else:
                    updates: dict[str, Any] = {
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        C.CONF_REGION: resolved_region,
                    }
                    if matched.get("bindDomain"):
                        updates[C.CONF_BIND_DOMAIN] = str(matched["bindDomain"])
                    await self.async_set_unique_id(did)
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(reauth_entry, data_updates=updates)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(
                username=(user_input or {}).get(CONF_USERNAME, str(reauth_entry.data.get(CONF_USERNAME, ""))),
                region=(user_input or {}).get(C.CONF_REGION, str(reauth_entry.data.get(C.CONF_REGION, C.DEFAULT_REGION))),
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        return DreameOptionsFlow()


class DreameOptionsFlow(OptionsFlowWithReload):
    """Handle polling interval option with automatic entry reload."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={C.CONF_SCAN_INTERVAL: C.clamp_scan_interval(user_input[C.CONF_SCAN_INTERVAL])},
            )
        current = C.clamp_scan_interval(
            self.config_entry.options.get(C.CONF_SCAN_INTERVAL, C.DEFAULT_SCAN_INTERVAL)
        )
        schema = vol.Schema(
            {
                vol.Required(C.CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=C.MIN_SCAN_INTERVAL, max=C.MAX_SCAN_INTERVAL)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
