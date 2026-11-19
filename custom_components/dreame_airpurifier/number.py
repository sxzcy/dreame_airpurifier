"""Number platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FP10_SPEED_MAX, FP10_SPEED_MIN, PROP_FAN_SPEED
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreame FP10 fan speed number entity."""
    async_add_entities([DreameFanSpeedNumber(entry.runtime_data)])


class DreameFanSpeedNumber(DreameEntity, NumberEntity):
    """Manual fan speed control (1-10)."""

    _attr_translation_key = "fan_speed"
    _attr_icon = "mdi:fan-speed-3"
    _attr_native_min_value = float(FP10_SPEED_MIN)
    _attr_native_max_value = float(FP10_SPEED_MAX)
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_number_fan_speed"

    @property
    def native_value(self) -> float | None:
        current = self._properties.get(PROP_FAN_SPEED)
        if current is None or isinstance(current, bool):
            return None
        try:
            return float(current)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        level = max(FP10_SPEED_MIN, min(FP10_SPEED_MAX, round(value)))
        await self.coordinator.async_set_property(PROP_FAN_SPEED, level)
