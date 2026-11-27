"""Declarative sensor platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfDensity,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const as C
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import DreameState, extract_wifi_rssi

_UGM3 = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
_MEAS = SensorStateClass.MEASUREMENT
_DIAG = EntityCategory.DIAGNOSTIC


@dataclass(frozen=True, kw_only=True)
class DreameSensorDescription(SensorEntityDescription):
    """Describe a Dreame FP10 sensor backed by a MIOT property or state helper."""

    prop_key: str | None = None
    numeric: bool = False
    value_map: Mapping[str, str] | None = None
    value_fn: Callable[[DreameState], Any] | None = None


SENSOR_DESCRIPTIONS: tuple[DreameSensorDescription, ...] = (
    DreameSensorDescription(key="pm25", translation_key="pm25", prop_key=C.PROP_PM25, device_class=SensorDeviceClass.PM25, native_unit_of_measurement=_UGM3, state_class=_MEAS, icon="mdi:molecule", numeric=True),
    DreameSensorDescription(key="pm10", translation_key="pm10", prop_key=C.PROP_PM10, device_class=SensorDeviceClass.PM10, native_unit_of_measurement=_UGM3, state_class=_MEAS, icon="mdi:molecule", numeric=True),
    DreameSensorDescription(key="tvoc", translation_key="tvoc", prop_key=C.PROP_TVOC, native_unit_of_measurement=_UGM3, state_class=_MEAS, icon="mdi:chemical-weapon", numeric=True),
    DreameSensorDescription(key="aq", translation_key="aq", prop_key=C.PROP_AQ, icon="mdi:weather-windy"),
    DreameSensorDescription(key="air_quality_level", translation_key="air_quality_level", prop_key=C.PROP_AIR_QUALITY_LEVEL, icon="mdi:air-filter", value_map=C.AIR_QUALITY_LEVEL_MAP),
    DreameSensorDescription(key="display_value", translation_key="display_value", prop_key=C.PROP_DISPLAY_VALUE, icon="mdi:counter"),
    DreameSensorDescription(key="current_speed", translation_key="current_speed", prop_key=C.PROP_FAN_SPEED, state_class=_MEAS, icon="mdi:fan", numeric=True),
    DreameSensorDescription(key="temperature", translation_key="temperature", prop_key=C.PROP_TEMPERATURE, device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=_MEAS, icon="mdi:thermometer", numeric=True),
    DreameSensorDescription(key="humidity", translation_key="humidity", prop_key=C.PROP_HUMIDITY, device_class=SensorDeviceClass.HUMIDITY, native_unit_of_measurement=PERCENTAGE, state_class=_MEAS, icon="mdi:water-percent", numeric=True),
    DreameSensorDescription(key="self_cleaning_status", translation_key="self_cleaning_status", prop_key=C.PROP_SELF_CLEAN_STATUS, device_class=SensorDeviceClass.ENUM, options=list(C.SELF_CLEAN_STATUS_MAP.values()), icon="mdi:broom", value_map=C.SELF_CLEAN_STATUS_MAP),
    DreameSensorDescription(key="hepa_filter_life", translation_key="hepa_filter_life", prop_key=C.PROP_HEPA_FILTER_LIFE, native_unit_of_measurement=PERCENTAGE, state_class=_MEAS, entity_category=_DIAG, icon="mdi:air-filter", numeric=True),
    DreameSensorDescription(key="hepa_filter_life_days", translation_key="hepa_filter_life_days", prop_key=C.PROP_HEPA_FILTER_DAYS, native_unit_of_measurement=UnitOfTime.DAYS, state_class=_MEAS, entity_category=_DIAG, icon="mdi:calendar-clock", numeric=True),
    DreameSensorDescription(key="combbox_life", translation_key="combbox_life", prop_key=C.PROP_COMBBOX_LIFE, native_unit_of_measurement=PERCENTAGE, state_class=_MEAS, entity_category=_DIAG, icon="mdi:tray-full", numeric=True),
    DreameSensorDescription(key="combbox_life_days", translation_key="combbox_life_days", prop_key=C.PROP_COMBBOX_DAYS, native_unit_of_measurement=UnitOfTime.DAYS, state_class=_MEAS, entity_category=_DIAG, icon="mdi:calendar-clock", numeric=True),
    DreameSensorDescription(key="status_code", translation_key="status_code", prop_key=C.PROP_STATUS, entity_category=_DIAG, icon="mdi:power-cycle", value_map=C.STATUS_CODE_MAP),
    DreameSensorDescription(key="error_code", translation_key="error_code", prop_key=C.PROP_ERROR_CODE, entity_category=_DIAG, icon="mdi:alert-circle-outline"),
    DreameSensorDescription(key="wifi_rssi", translation_key="wifi_rssi", device_class=SensorDeviceClass.SIGNAL_STRENGTH, native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT, state_class=_MEAS, entity_category=_DIAG, icon="mdi:wifi", value_fn=lambda state: extract_wifi_rssi(state.otc_info)),
)


def _parse_number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            try:
                return float(value.strip())
            except ValueError:
                return None
    return None


async def async_setup_entry(
    hass: HomeAssistant, entry: DreameConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DreameSensorEntity(coordinator, desc) for desc in SENSOR_DESCRIPTIONS)


class DreameSensorEntity(DreameEntity, SensorEntity):
    """Sensor entity backed by a declarative FP10 MIOT property description."""

    entity_description: DreameSensorDescription

    def __init__(self, coordinator: DreameCoordinator, description: DreameSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.descriptor.did}_sensor_{description.key}"

    @property
    def native_value(self) -> Any:
        if self.entity_description.value_fn is not None:
            if self.coordinator.data is None:
                return None
            return self.entity_description.value_fn(self.coordinator.data)
        if self.entity_description.prop_key is None:
            return None
        raw = self._properties.get(self.entity_description.prop_key)
        if raw is None:
            return None
        if self.entity_description.value_map is not None:
            mapped = self.entity_description.value_map.get(str(raw))
            if mapped is not None:
                return mapped
            if self.entity_description.device_class == SensorDeviceClass.ENUM:
                return None
            return raw
        if self.entity_description.numeric:
            return _parse_number(raw)
        if isinstance(raw, (dict, list)):
            return json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        return raw
