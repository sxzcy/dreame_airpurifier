"""DataUpdateCoordinator for Dreame FP10 Air Purifier."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import const as C
from .client import DreameClient
from .protocol import DreameAuthError, DreameDeviceDescriptor, DreameError, DreameState, parse_key

_LOGGER = logging.getLogger(__name__)

type DreameConfigEntry = ConfigEntry[DreameCoordinator]


class DreameCoordinator(DataUpdateCoordinator[DreameState]):
    """Coordinate Dreame FP10 cloud polling and write commands."""

    config_entry: DreameConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DreameConfigEntry) -> None:
        self.descriptor = DreameDeviceDescriptor(
            did=str(entry.data[C.CONF_DID]),
            name=str(entry.data.get(C.CONF_DEVICE_NAME) or C.DEFAULT_NAME),
            model=str(entry.data.get(C.CONF_DEVICE_MODEL) or C.FP10_MODEL),
            bind_domain=str(entry.data.get(C.CONF_BIND_DOMAIN) or ""),
            mac=entry.data.get(C.CONF_MAC),
        )
        self.client = DreameClient(
            async_get_clientsession(hass),
            str(entry.data[CONF_USERNAME]),
            str(entry.data[CONF_PASSWORD]),
            str(entry.data.get(C.CONF_REGION) or C.DEFAULT_REGION),
        )
        self._follow_up_task: asyncio.Task[None] | None = None
        interval = C.clamp_scan_interval(entry.options.get(C.CONF_SCAN_INTERVAL, C.DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{C.DOMAIN}_{self.descriptor.did}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> DreameState:
        try:
            otc_info = await self.client.async_get_otc_info(self.descriptor.did)
            properties = await self.client.async_get_props(self.descriptor.did, C.FP10_POLLED_KEYS)
        except DreameAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DreameError as err:
            raise UpdateFailed(str(err)) from err
        return DreameState(descriptor=self.descriptor, properties=properties, otc_info=otc_info)

    async def _async_write(
        self,
        awaitable: Awaitable[None],
        *,
        optimistic_property: tuple[str, Any] | None = None,
        schedule_refresh: bool = True,
    ) -> None:
        try:
            await awaitable
        except DreameAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except DreameError as err:
            raise HomeAssistantError(str(err)) from err

        if optimistic_property is not None:
            current = self.data or DreameState(descriptor=self.descriptor)
            self.async_set_updated_data(current.with_property(*optimistic_property))
        if schedule_refresh:
            self.async_schedule_follow_up_refresh()

    async def async_set_property(
        self, key: str, value: Any, *, schedule_refresh: bool = True
    ) -> None:
        siid, piid = parse_key(key)
        await self._async_write(
            self.client.async_set_property(
                self.descriptor.bind_domain, self.descriptor.did, siid, piid, value
            ),
            optimistic_property=(key, value),
            schedule_refresh=schedule_refresh,
        )

    async def async_send_action(
        self,
        siid: int,
        aiid: int,
        inputs: list[dict[str, Any]] | None = None,
        *,
        optimistic_property: tuple[str, Any] | None = None,
        schedule_refresh: bool = True,
    ) -> None:
        await self._async_write(
            self.client.async_action(
                self.descriptor.bind_domain, self.descriptor.did, siid, aiid, inputs
            ),
            optimistic_property=optimistic_property,
            schedule_refresh=schedule_refresh,
        )

    def async_schedule_follow_up_refresh(self, delays: tuple[float, ...] = (2.0, 5.0)) -> None:
        if self._follow_up_task and not self._follow_up_task.done():
            self._follow_up_task.cancel()
        self._follow_up_task = self.hass.async_create_task(self._async_follow_up_refresh(delays))

    async def _async_follow_up_refresh(self, delays: tuple[float, ...]) -> None:
        try:
            for delay in delays:
                await asyncio.sleep(delay)
                await self.async_request_refresh()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.debug("Follow-up Dreame refresh failed", exc_info=True)

    async def async_shutdown(self) -> None:
        if self._follow_up_task and not self._follow_up_task.done():
            self._follow_up_task.cancel()
            try:
                await self._follow_up_task
            except asyncio.CancelledError:
                pass
        self._follow_up_task = None
