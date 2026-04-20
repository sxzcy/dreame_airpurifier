from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity
from .utils import values_equal


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data["dreame_smartlife"][entry.entry_id]
    entities = [
        DreameSmartlifeMappedSelect(coordinator, name, mapping)
        for name, mapping in coordinator.options.select_mappings.items()
        if mapping.get("key") and isinstance(mapping.get("options"), dict)
    ]
    async_add_entities(entities)


class DreameSmartlifeMappedSelect(DreameSmartlifeEntity, SelectEntity):
    def __init__(self, coordinator: DreameSmartlifeCoordinator, name: str, mapping: dict) -> None:
        super().__init__(coordinator)
        self._mapping = mapping
        self._key = mapping["key"]
        self._options_map = mapping["options"]
        self._attr_name = mapping.get("name", name.replace("_", " ").title())
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_select_{name}"
        self._attr_options = list(self._options_map.keys())
        self._attr_icon = mapping.get("icon")

    @property
    def current_option(self) -> str | None:
        current = (self.coordinator.data or self.coordinator.device.state).properties.get(self._key)
        for label, raw in self._options_map.items():
            if values_equal(current, raw):
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        value = self._options_map[option]
        await self.coordinator.device.async_set_property(self._key, value)
        self.coordinator.async_set_local_property(self._key, value)
        self.coordinator.async_schedule_follow_up_refresh()
