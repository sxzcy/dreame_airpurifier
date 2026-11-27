"""The Dreame FP10 Air Purifier integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_REGION, REGION_AUTO
from .coordinator import DreameConfigEntry, DreameCoordinator

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)


async def async_setup_entry(hass: HomeAssistant, entry: DreameConfigEntry) -> bool:
    """Set up Dreame FP10 Air Purifier from a config entry."""
    coordinator = DreameCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    if entry.data.get(CONF_REGION) == REGION_AUTO and coordinator.client.region != REGION_AUTO:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REGION: coordinator.client.region}
        )
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_push()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DreameConfigEntry) -> bool:
    """Unload a Dreame FP10 Air Purifier config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
