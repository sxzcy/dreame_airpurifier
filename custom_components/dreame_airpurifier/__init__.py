from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS, SERVICE_PROBE_PROPERTIES, SERVICE_SEND_RAW_COMMAND
from .coordinator import DreameSmartlifeCoordinator

_LOGGER = logging.getLogger(__name__)
CONF_METHOD = "method"
CONF_PARAMS = "params"

SERVICE_PROBE_SCHEMA = vol.Schema({vol.Required("config_entry_id"): cv.string})
SERVICE_SEND_RAW_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(CONF_METHOD): cv.string,
        vol.Required(CONF_PARAMS): object,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def _get_coordinator(entry_id: str) -> DreameSmartlifeCoordinator:
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Unknown Dreame Air Purifier FP10 entry: {entry_id}")
        return coordinator

    async def handle_probe(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_probe_properties()
        await hass.config_entries.async_reload(coordinator.entry.entry_id)

    async def handle_send_raw(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call.data["config_entry_id"])
        await coordinator.async_send_raw_command(call.data[CONF_METHOD], call.data[CONF_PARAMS])
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_PROBE_PROPERTIES):
        hass.services.async_register(DOMAIN, SERVICE_PROBE_PROPERTIES, handle_probe, schema=SERVICE_PROBE_SCHEMA)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND):
        hass.services.async_register(DOMAIN, SERVICE_SEND_RAW_COMMAND, handle_send_raw, schema=SERVICE_SEND_RAW_SCHEMA)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DreameSmartlifeCoordinator(hass, entry)
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
