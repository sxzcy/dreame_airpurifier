"""Base entity for Dreame FP10 Air Purifier."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DreameCoordinator


class DreameEntity(CoordinatorEntity[DreameCoordinator]):
    """Common base entity sharing DeviceInfo and coordinator state access."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        descriptor = coordinator.descriptor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, descriptor.did)},
            name=descriptor.name,
            manufacturer="Dreame",
            model=descriptor.model,
        )

    @property
    def _properties(self) -> Mapping[str, Any]:
        """Return the latest polled MIOT property snapshot."""
        return self.coordinator.data.properties if self.coordinator.data else {}
