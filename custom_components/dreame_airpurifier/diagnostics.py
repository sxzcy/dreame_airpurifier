"""Diagnostics support for Dreame FP10 Air Purifier."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_BIND_DOMAIN, CONF_DID, CONF_MAC
from .coordinator import DreameConfigEntry

TO_REDACT = {
    CONF_USERNAME, CONF_PASSWORD, CONF_DID, CONF_MAC, CONF_BIND_DOMAIN,
    "bindDomain", "uid", "user_id", "userId", "tenant_id",
    "token", "access_token", "refresh_token", "auth_token", "Dreame-Auth",
    "ip", "local_ip", "localIp", "gw", "bssid", "ssid", "wifi_mac", "wifiMac",
    "sn", "serial", "serial_number", "serialNumber",
    "secret", "api_key", "app_key", "auth_key", "host", "broker", "device_id", "deviceId",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DreameConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data
    state = coordinator.data
    payload = {
        "entry": {"title": entry.title, "data": dict(entry.data), "options": dict(entry.options)},
        "device": asdict(coordinator.descriptor),
        "region": coordinator.client.region,
        "otc_info": dict(state.otc_info) if state else {},
        "properties": dict(state.properties) if state else {},
    }
    return async_redact_data(payload, TO_REDACT)
