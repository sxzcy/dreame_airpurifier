from __future__ import annotations

import asyncio
from dataclasses import asdict
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .dreame.device import DreameSmartlifeDevice, DreameSmartlifeState
from .dreame.exceptions import DreameSmartlifeError
from .dreame.models import descriptor_from_entry, load_options
from .dreame.protocol import DreameSmartlifeClient

_LOGGER = logging.getLogger(__name__)


class DreameSmartlifeCoordinator(DataUpdateCoordinator[DreameSmartlifeState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.options = load_options(entry.data, entry.options)
        self._follow_up_refresh_task: asyncio.Task | None = None
        client = DreameSmartlifeClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_REGION],
        )
        self.device = DreameSmartlifeDevice(client, descriptor_from_entry(entry.data))
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}")
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device.descriptor.did}",
            update_interval=self._build_interval(),
        )

    def _build_interval(self):
        from datetime import timedelta

        return timedelta(seconds=max(self.options.scan_interval, MIN_SCAN_INTERVAL))

    async def _async_update_data(self) -> DreameSmartlifeState:
        try:
            return await self.device.async_refresh(self.options.polled_keys)
        except DreameSmartlifeError as err:
            raise UpdateFailed(str(err)) from err

    async def async_reload_options(self) -> None:
        self.options = load_options(self.entry.data, self.entry.options)
        self.update_interval = self._build_interval()
        await self.async_request_refresh()

    async def async_initialize(self) -> None:
        cached = await self._store.async_load()
        if not cached:
            return
        self.device.state.discovered_properties = cached.get("discovered_properties", {})
        last_probe_at = cached.get("last_probe_at")
        if last_probe_at:
            from homeassistant.util import dt as dt_util

            self.device.state.last_probe_at = dt_util.parse_datetime(last_probe_at)

    async def async_probe_properties(self) -> DreameSmartlifeState:
        state = await self.device.async_probe_properties(self.options.probe_max_siid, self.options.probe_max_piid)
        await self._store.async_save(
            {
                "discovered_properties": state.discovered_properties,
                "last_probe_at": state.last_probe_at.isoformat() if state.last_probe_at else None,
            }
        )
        self.async_set_updated_data(state)
        return self.data

    async def async_send_raw_command(self, method: str, params: Any) -> Any:
        return await self.device.async_send_raw_command(method, params)

    def async_publish_state(self) -> None:
        self.async_set_updated_data(self.device.state)

    def async_set_local_property(self, key: str | None, value: Any) -> None:
        if not key:
            return
        self.device.state.properties[key] = value
        self.async_publish_state()

    def async_schedule_follow_up_refresh(self, delays: tuple[float, ...] = (2.0, 4.0, 8.0)) -> None:
        if self._follow_up_refresh_task and not self._follow_up_refresh_task.done():
            self._follow_up_refresh_task.cancel()
        self._follow_up_refresh_task = self.hass.async_create_task(self._async_follow_up_refresh(delays))

    async def _async_follow_up_refresh(self, delays: tuple[float, ...]) -> None:
        try:
            for delay in delays:
                await asyncio.sleep(delay)
                await self.async_request_refresh()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.debug("Delayed Dreame Smart Life refresh failed", exc_info=True)

    @property
    def diagnostics(self) -> dict[str, Any]:
        state = self.data or self.device.state
        return {
            "device": asdict(state.descriptor),
            "otc_info": state.otc_info,
            "properties": state.properties,
            "discovered_properties": state.discovered_properties,
            "last_probe_at": state.last_probe_at.isoformat() if state.last_probe_at else None,
        }
