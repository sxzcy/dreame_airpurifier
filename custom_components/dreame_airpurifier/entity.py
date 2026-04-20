from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DreameSmartlifeCoordinator
from .const import DOMAIN


class DreameSmartlifeEntity(CoordinatorEntity[DreameSmartlifeCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameSmartlifeCoordinator) -> None:
        super().__init__(coordinator)
        descriptor = coordinator.device.descriptor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, descriptor.did)},
            name=descriptor.name,
            manufacturer="Dreame",
            model=descriptor.model,
            sw_version=None,
        )
