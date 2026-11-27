"""Select platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from collections.abc import Mapping

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COLOR_TEMPERATURE_OPTIONS,
    LIGHT_BRIGHTNESS_OPTIONS,
    PROP_COLOR_TEMPERATURE,
    PROP_LIGHT_BRIGHTNESS,
    PROP_WIND_MODE,
    WIND_MODE_OPTIONS,
)
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import values_equal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreame FP10 select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DreameWindModeSelect(coordinator),
            DreameLightBrightnessSelect(coordinator),
            DreameColorTemperatureSelect(coordinator),
        ]
    )


class _DreameMappedSelect(DreameEntity, SelectEntity):
    """Base mapped select entity backed by a single MIOT property."""

    _prop_key: str
    _option_map: Mapping[str, int]

    @property
    def current_option(self) -> str | None:
        current = self._properties.get(self._prop_key)
        for label, raw in self._option_map.items():
            if values_equal(current, raw):
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in self._option_map:
            raise HomeAssistantError(f"Unsupported option: {option}")
        await self.coordinator.async_set_property(
            self._prop_key,
            self._option_map[option],
        )


class DreameWindModeSelect(_DreameMappedSelect):
    """Purification mode selector."""

    _attr_translation_key = "wind_mode"
    _attr_icon = "mdi:fan-auto"
    _prop_key = PROP_WIND_MODE
    _option_map = WIND_MODE_OPTIONS
    _attr_options = list(WIND_MODE_OPTIONS)

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_select_wind_mode"


class DreameLightBrightnessSelect(_DreameMappedSelect):
    """Ambient light brightness level selector (off/dim/natural/bright)."""

    _attr_translation_key = "light_brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_entity_category = EntityCategory.CONFIG
    _prop_key = PROP_LIGHT_BRIGHTNESS
    _option_map = LIGHT_BRIGHTNESS_OPTIONS
    _attr_options = list(LIGHT_BRIGHTNESS_OPTIONS)

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_select_light_brightness"


class DreameColorTemperatureSelect(_DreameMappedSelect):
    """Ambient light color temperature selector (2700K/4000K/5700K, MCU > 62)."""

    _attr_translation_key = "color_temperature"
    _attr_icon = "mdi:thermometer-lines"
    _attr_entity_category = EntityCategory.CONFIG
    _prop_key = PROP_COLOR_TEMPERATURE
    _option_map = COLOR_TEMPERATURE_OPTIONS
    _attr_options = list(COLOR_TEMPERATURE_OPTIONS)

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_select_color_temperature"
