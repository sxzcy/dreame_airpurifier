from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .const import DOMAIN
from .coordinator import DreameSmartlifeCoordinator
from .entity import DreameSmartlifeEntity
from .utils import values_equal


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: DreameSmartlifeCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.options.fan_mapping.power_key or coordinator.options.fan_mapping.power_action_siid:
        async_add_entities([DreameSmartlifeFanEntity(coordinator)])


class DreameSmartlifeFanEntity(DreameSmartlifeEntity, FanEntity):
    def __init__(self, coordinator: DreameSmartlifeCoordinator) -> None:
        super().__init__(coordinator)
        self._mapping = coordinator.options.fan_mapping
        self._attr_name = self._mapping.entity_name
        self._attr_unique_id = f"{coordinator.device.descriptor.did}_fan"
        self._attr_preset_modes = list(self._mapping.speed_map.keys()) or None
        self._attr_percentage_step = 100

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._mapping.speed_key and self._mapping.speed_map:
            features |= FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED
        return features

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data or self.coordinator.device.state
        if self._mapping.status_key:
            current = state.properties.get(self._mapping.status_key)
            if current is None:
                return None
            return values_equal(current, self._mapping.status_on_value)
        current = state.properties.get(self._mapping.power_key or "")
        if current is None:
            return None
        return not values_equal(current, self._mapping.power_off_value)

    @property
    def preset_mode(self) -> str | None:
        if not self._mapping.speed_key or not self._mapping.speed_map:
            return None
        current = (self.coordinator.data or self.coordinator.device.state).properties.get(self._mapping.speed_key)
        for label, raw in self._mapping.speed_map.items():
            if values_equal(current, raw):
                return label
        return None

    @property
    def percentage(self) -> int | None:
        if self.is_on is False:
            return 0
        return 100

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        if self._mapping.power_action_siid and self._mapping.power_action_aiid and self._mapping.power_action_piid:
            await self.coordinator.device.async_action(
                self._mapping.power_action_siid,
                self._mapping.power_action_aiid,
                [{"piid": self._mapping.power_action_piid, "value": self._mapping.power_on_value}],
            )
            self.coordinator.async_set_local_property(self._mapping.status_key, self._mapping.status_on_value)
        elif self._mapping.power_key:
            await self.coordinator.device.async_set_property(self._mapping.power_key, self._mapping.power_on_value)
            self.coordinator.async_set_local_property(self._mapping.power_key, self._mapping.power_on_value)
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        self.coordinator.async_schedule_follow_up_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._mapping.power_action_siid and self._mapping.power_action_aiid and self._mapping.power_action_piid:
            await self.coordinator.device.async_action(
                self._mapping.power_action_siid,
                self._mapping.power_action_aiid,
                [{"piid": self._mapping.power_action_piid, "value": self._mapping.power_off_value}],
            )
            self.coordinator.async_set_local_property(self._mapping.status_key, self._mapping.status_off_value)
        elif self._mapping.power_key:
            await self.coordinator.device.async_set_property(self._mapping.power_key, self._mapping.power_off_value)
            self.coordinator.async_set_local_property(self._mapping.power_key, self._mapping.power_off_value)
        self.coordinator.async_schedule_follow_up_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if not self._mapping.speed_key:
            return
        if self.is_on is False:
            await self.async_turn_on()
        value = self._mapping.speed_map[preset_mode]
        await self.coordinator.device.async_set_property(self._mapping.speed_key, value)
        self.coordinator.async_set_local_property(self._mapping.speed_key, value)
        self.coordinator.async_schedule_follow_up_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage <= 0:
            await self.async_turn_off()
            return
        await self.async_set_preset_mode("强净化")
