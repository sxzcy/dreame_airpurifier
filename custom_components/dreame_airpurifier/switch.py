"""Switch platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FP10_CHILD_LOCK_OFF, FP10_CHILD_LOCK_ON, PROP_CHILD_LOCK
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import values_equal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreame FP10 child lock switch entity."""
    async_add_entities([DreameChildLockSwitch(entry.runtime_data)])


class DreameChildLockSwitch(DreameEntity, SwitchEntity):
    """Child lock switch."""

    _attr_translation_key = "child_lock"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_switch_child_lock"

    @property
    def is_on(self) -> bool | None:
        current = self._properties.get(PROP_CHILD_LOCK)
        if current is None:
            return None
        return values_equal(current, FP10_CHILD_LOCK_ON)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_CHILD_LOCK, FP10_CHILD_LOCK_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_CHILD_LOCK, FP10_CHILD_LOCK_OFF)
