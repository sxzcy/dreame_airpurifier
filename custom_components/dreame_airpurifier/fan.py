"""Fan platform for Dreame FP10 Air Purifier."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import const as C
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity
from .protocol import values_equal


async def async_setup_entry(
    hass: HomeAssistant, entry: DreameConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([DreameFanEntity(entry.runtime_data)])


class DreameFanEntity(DreameEntity, FanEntity):
    """Main air purifier fan entity with speed percentage and preset modes."""

    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = list(C.FAN_PRESET_MODES)
    _attr_speed_count = int_states_in_range(C.FP10_SPEED_RANGE)

    def __init__(self, coordinator: DreameCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.descriptor.did}_fan"

    @property
    def is_on(self) -> bool | None:
        raw = self._properties.get(C.PROP_STATUS)
        return None if raw is None else values_equal(raw, C.FP10_STATUS_ON)

    @property
    def percentage(self) -> int | None:
        if self.is_on is None:
            return None
        if not self.is_on:
            return 0
        raw = self._properties.get(C.PROP_FAN_SPEED)
        if raw is None or isinstance(raw, bool):
            return None
        try:
            speed = int(float(raw))
        except (TypeError, ValueError):
            return None
        if speed < C.FP10_SPEED_MIN:
            return None
        return ranged_value_to_percentage(C.FP10_SPEED_RANGE, min(speed, C.FP10_SPEED_MAX))

    @property
    def preset_mode(self) -> str | None:
        current = self._properties.get(C.PROP_WIND_MODE)
        return next((k for k, v in C.FAN_PRESET_MODES.items() if values_equal(current, v)), None)

    @staticmethod
    def _speed_from_percentage(percentage: int) -> int:
        raw = math.ceil(percentage_to_ranged_value(C.FP10_SPEED_RANGE, percentage))
        return max(C.FP10_SPEED_MIN, min(C.FP10_SPEED_MAX, raw))

    async def _async_power(self, on: bool, *, schedule_refresh: bool = True) -> None:
        await self.coordinator.async_send_action(
            C.FP10_POWER_ACTION_SIID,
            C.FP10_POWER_ACTION_AIID,
            [{"piid": C.FP10_POWER_ACTION_PIID, "value": C.FP10_POWER_ON_VALUE if on else C.FP10_POWER_OFF_VALUE}],
            optimistic_property=(C.PROP_STATUS, C.FP10_STATUS_ON if on else C.FP10_STATUS_OFF),
            schedule_refresh=schedule_refresh,
        )

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if percentage is not None and percentage <= 0:
            await self.async_turn_off()
            return
        if preset_mode is not None and preset_mode not in C.FAN_PRESET_MODES:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")
        has_followup = preset_mode is not None or percentage is not None
        await self._async_power(True, schedule_refresh=not has_followup)
        if preset_mode is not None:
            await self.coordinator.async_set_property(
                C.PROP_WIND_MODE, C.FAN_PRESET_MODES[preset_mode], schedule_refresh=percentage is None
            )
        if percentage is not None:
            await self.coordinator.async_set_property(
                C.PROP_FAN_SPEED, self._speed_from_percentage(percentage)
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_power(False)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in C.FAN_PRESET_MODES:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")
        if self.is_on is not True:
            await self._async_power(True, schedule_refresh=False)
        await self.coordinator.async_set_property(C.PROP_WIND_MODE, C.FAN_PRESET_MODES[preset_mode])

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage <= 0:
            await self.async_turn_off()
            return
        if self.is_on is not True:
            await self._async_power(True, schedule_refresh=False)
        await self.coordinator.async_set_property(
            C.PROP_FAN_SPEED, self._speed_from_percentage(percentage)
        )
