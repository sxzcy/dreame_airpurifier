from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data["dreame_smartlife"][entry.entry_id]
    async_add_entities([DreameSmartlifeProbeButton(coordinator)])


class DreameSmartlifeProbeButton(DreameSmartlifeEntity, ButtonEntity):
    _attr_name = "探测属性"
    _attr_icon = "mdi:radar"

    def __init__(self, coordinator: DreameSmartlifeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_probe"

    async def async_press(self) -> None:
        await self.coordinator.async_probe_properties()
        await self.coordinator.hass.config_entries.async_reload(self.coordinator.entry.entry_id)
