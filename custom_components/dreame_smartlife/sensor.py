from __future__ import annotations

import json
import re
from typing import Any

from homeassistant.components.sensor import SensorEntity

from .const import ATTR_DEVICE_INFO, ATTR_DISCOVERED_PROPERTIES, ATTR_LAST_PROBE_AT, ATTR_OTC_INFO, ATTR_PROPERTIES
from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data["dreame_smartlife"][entry.entry_id]
    entities: list[SensorEntity] = [DreameSmartlifeDiagnosticsSensor(coordinator)]

    for name, mapping in coordinator.options.sensor_mappings.items():
        key = mapping.get("key")
        if key:
            entities.append(DreameSmartlifeMappedSensor(coordinator, name, mapping))

    async_add_entities(entities)


class DreameSmartlifeDiagnosticsSensor(DreameSmartlifeEntity, SensorEntity):
    _attr_name = "诊断"
    _attr_icon = "mdi:stethoscope"

    def __init__(self, coordinator: DreameSmartlifeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_diagnostics"

    @property
    def native_value(self) -> int:
        discovered = self.coordinator.data.discovered_properties if self.coordinator.data else {}
        return len(discovered)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self.coordinator.data or self.coordinator.device.state
        return {
            ATTR_DEVICE_INFO: state.descriptor.raw or {
                "did": state.descriptor.did,
                "name": state.descriptor.name,
                "model": state.descriptor.model,
                "bind_domain": state.descriptor.bind_domain,
                "mac": state.descriptor.mac,
            },
            ATTR_OTC_INFO: state.otc_info,
            ATTR_PROPERTIES: state.properties,
            ATTR_DISCOVERED_PROPERTIES: state.discovered_properties,
            ATTR_LAST_PROBE_AT: state.last_probe_at.isoformat() if state.last_probe_at else None,
        }


class DreameSmartlifeMappedSensor(DreameSmartlifeEntity, SensorEntity):
    def __init__(self, coordinator: DreameSmartlifeCoordinator, name: str, mapping: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._mapping = mapping
        self._key = mapping["key"]
        self._attr_name = mapping.get("name", name.replace("_", " ").title())
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_sensor_{name}"
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_device_class = mapping.get("device_class")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")

    @property
    def native_value(self) -> Any:
        value = (self.coordinator.data or self.coordinator.device.state).properties.get(self._key)
        value_map = self._mapping.get("value_map")
        if value_map and value is not None:
            mapped = value_map.get(str(value))
            if mapped is not None:
                return mapped
        extract_regex = self._mapping.get("extract_regex")
        if extract_regex and value is not None:
            match = re.search(str(extract_regex), str(value))
            if match:
                extracted = match.group(1)
                if extracted.isdigit():
                    return int(extracted)
                return extracted
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return value
