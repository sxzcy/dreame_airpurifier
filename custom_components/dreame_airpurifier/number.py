from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode

from .const import DOMAIN
from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DreameSmartlifeMappedNumber(coordinator, name, mapping)
        for name, mapping in coordinator.options.number_mappings.items()
        if mapping.get("key")
    ]
    async_add_entities(entities)


class DreameSmartlifeMappedNumber(DreameSmartlifeEntity, NumberEntity):
    def __init__(self, coordinator: DreameSmartlifeCoordinator, name: str, mapping: dict) -> None:
        super().__init__(coordinator)
        self._mapping = mapping
        self._key = mapping["key"]
        self._attr_name = mapping.get("name", name.replace("_", " ").title())
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_number_{name}"
        self._attr_native_min_value = float(mapping.get("min", 0))
        self._attr_native_max_value = float(mapping.get("max", 100))
        self._attr_native_step = float(mapping.get("step", 1))
        self._attr_mode = NumberMode(mapping.get("mode", "auto"))
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_icon = mapping.get("icon")

    @property
    def native_value(self) -> float | None:
        current = (self.coordinator.data or self.coordinator.device.state).properties.get(self._key)
        if current is None:
            return None
        try:
            return float(current)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        write_value = int(value) if self._attr_native_step == 1 else value
        await self.coordinator.device.async_set_property(self._key, write_value)
        self.coordinator.async_set_local_property(self._key, write_value)
        self.coordinator.async_schedule_follow_up_refresh()
