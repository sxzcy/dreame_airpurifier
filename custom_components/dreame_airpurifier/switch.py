"""Switch platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    FP10_BOOL_OFF,
    FP10_BOOL_ON,
    FP10_CHILD_LOCK_OFF,
    FP10_CHILD_LOCK_ON,
    PROP_AMBIENT_BREATHING,
)
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import values_equal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dreame FP10 switch entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DreameChildLockSwitch(coordinator),
            DreameAmbientBreathingSwitch(coordinator),
            DreameKeySoundSwitch(coordinator),
        ]
    )


class DreameChildLockSwitch(DreameEntity, SwitchEntity):
    """Child lock switch (adapts 6.10 on 1.9.3_1072+ and 2.5 on legacy firmware)."""

    _attr_translation_key = "child_lock"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_switch_child_lock"

    @property
    def is_on(self) -> bool | None:
        current = self._properties.get(self.coordinator.child_lock_prop_key)
        if current is None:
            return None
        return values_equal(current, FP10_CHILD_LOCK_ON)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(
            self.coordinator.child_lock_prop_key, FP10_CHILD_LOCK_ON
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(
            self.coordinator.child_lock_prop_key, FP10_CHILD_LOCK_OFF
        )


class DreameAmbientBreathingSwitch(DreameEntity, SwitchEntity):
    """Ambient light breathing mode switch (0 = steady, 1 = breathing)."""

    _attr_translation_key = "ambient_breathing"
    _attr_icon = "mdi:led-on"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_switch_ambient_breathing"

    @property
    def is_on(self) -> bool | None:
        current = self._properties.get(PROP_AMBIENT_BREATHING)
        if current is None:
            return None
        return values_equal(current, FP10_BOOL_ON)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_AMBIENT_BREATHING, FP10_BOOL_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_AMBIENT_BREATHING, FP10_BOOL_OFF)


class DreameKeySoundSwitch(DreameEntity, SwitchEntity):
    """Keypress tone switch (adapts 6.17 on 1.9.3_1072+ and 6.7 on legacy firmware)."""

    _attr_translation_key = "key_sound"
    _attr_icon = "mdi:volume-high"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_switch_key_sound"

    @property
    def is_on(self) -> bool | None:
        current = self._properties.get(self.coordinator.key_sound_prop_key)
        if current is None:
            return None
        return values_equal(current, FP10_BOOL_ON)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(
            self.coordinator.key_sound_prop_key, FP10_BOOL_ON
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(
            self.coordinator.key_sound_prop_key, FP10_BOOL_OFF
        )
