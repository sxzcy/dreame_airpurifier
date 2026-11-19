"""Select platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PROP_WIND_MODE, WIND_MODE_OPTIONS
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import values_equal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreame FP10 purification mode select entity."""
    async_add_entities([DreameWindModeSelect(entry.runtime_data)])


class DreameWindModeSelect(DreameEntity, SelectEntity):
    """Purification mode selector."""

    _attr_translation_key = "wind_mode"
    _attr_icon = "mdi:fan-auto"
    _attr_options = list(WIND_MODE_OPTIONS)

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_select_wind_mode"

    @property
    def current_option(self) -> str | None:
        current = self._properties.get(PROP_WIND_MODE)
        for label, raw in WIND_MODE_OPTIONS.items():
            if values_equal(current, raw):
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in WIND_MODE_OPTIONS:
            raise HomeAssistantError(f"Unsupported option: {option}")
        await self.coordinator.async_set_property(
            PROP_WIND_MODE,
            WIND_MODE_OPTIONS[option],
        )
