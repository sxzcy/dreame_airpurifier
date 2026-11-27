"""Binary sensor platform for Dreame FP10 Air Purifier diagnostics."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame FP10 diagnostic binary sensors."""
    async_add_entities([DreameCloudPushBinarySensor(entry.runtime_data)])


class DreameCloudPushBinarySensor(DreameEntity, BinarySensorEntity):
    """Report whether the Dreame Cloud MQTT real-time push link is connected."""

    _attr_translation_key = "cloud_push"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_binary_sensor_cloud_push"

    @property
    def is_on(self) -> bool:
        if self.coordinator.data is not None:
            return self.coordinator.data.mqtt_connected
        return self.coordinator.mqtt_connected
