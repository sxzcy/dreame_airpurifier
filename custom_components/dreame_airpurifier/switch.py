from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity
from .utils import values_equal


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DreameSmartlifeMappedSwitch(coordinator, name, mapping)
        for name, mapping in coordinator.options.switch_mappings.items()
        if mapping.get("key")
    ]
    async_add_entities(entities)


class DreameSmartlifeMappedSwitch(DreameSmartlifeEntity, SwitchEntity):
    def __init__(self, coordinator: DreameSmartlifeCoordinator, name: str, mapping: dict) -> None:
        super().__init__(coordinator)
        self._mapping = mapping
        self._key = mapping["key"]
        self._on_value = mapping.get("on", 1)
        self._off_value = mapping.get("off", 0)
        self._attr_name = mapping.get("name", name.replace("_", " ").title())
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_switch_{name}"
        self._attr_icon = mapping.get("icon")

    @property
    def is_on(self) -> bool | None:
        current = (self.coordinator.data or self.coordinator.device.state).properties.get(self._key)
        if current is None:
            return None
        return values_equal(current, self._on_value)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.async_set_property(self._key, self._on_value)
        self.coordinator.async_set_local_property(self._key, self._on_value)
        self.coordinator.async_schedule_follow_up_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.async_set_property(self._key, self._off_value)
        self.coordinator.async_set_local_property(self._key, self._off_value)
        self.coordinator.async_schedule_follow_up_refresh()
