"""DataUpdateCoordinator for Dreame FP10 Air Purifier."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Mapping
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
from .mqtt import DreameMqttPushClient, build_dreame_ssl_context
from .protocol import (
    DreameAuthError,
    DreameDeviceDescriptor,
    DreameError,
    DreameState,
    parse_key,
    resolve_child_lock_key,
    resolve_key_sound_key,
)

_LOGGER = logging.getLogger(__name__)

type DreameConfigEntry = ConfigEntry[DreameCoordinator]


class DreameCoordinator(DataUpdateCoordinator[DreameState]):
    """Coordinate Dreame FP10 cloud MQTT push, HTTP fallback polling, and write commands."""

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
        self._base_scan_interval = C.clamp_scan_interval(
            entry.options.get(C.CONF_SCAN_INTERVAL, C.DEFAULT_SCAN_INTERVAL)
        )
        self._fw_version: str | None = None
        self._master_uid: str | None = None
        self._metadata_fetched = False
        self._follow_up_task: asyncio.Task[None] | None = None
        self._push_task: asyncio.Task[None] | None = None
        self._push_client: DreameMqttPushClient | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{C.DOMAIN}_{self.descriptor.did}",
            update_interval=timedelta(seconds=self._base_scan_interval),
        )

    @property
    def fw_version(self) -> str | None:
        return self._fw_version

    @property
    def mqtt_connected(self) -> bool:
        return bool(self._push_client and self._push_client.connected)

    @property
    def child_lock_prop_key(self) -> str:
        props = self.data.properties if self.data else {}
        return resolve_child_lock_key(props, self._fw_version)

    @property
    def key_sound_prop_key(self) -> str:
        props = self.data.properties if self.data else {}
        return resolve_key_sound_key(props, self._fw_version)

    async def _async_refresh_device_metadata(self) -> None:
        if self._metadata_fetched:
            return
        try:
            info = await self.client.async_get_device_info(self.descriptor.did)
        except DreameAuthError:
            raise
        except DreameError as err:
            _LOGGER.debug("Optional Dreame device/info fetch failed: %s", err)
            return
        self._metadata_fetched = True
        ver = info.get("ver")
        if ver:
            self._fw_version = str(ver)
        master_uid = info.get("masterUid")
        if master_uid:
            self._master_uid = str(master_uid)

    async def _async_update_data(self) -> DreameState:
        try:
            otc_info = await self.client.async_get_otc_info(self.descriptor.did)
            properties = await self.client.async_get_props(self.descriptor.did, C.FP10_POLLED_KEYS)
            await self._async_refresh_device_metadata()
        except DreameAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DreameError as err:
            raise UpdateFailed(str(err)) from err
        return DreameState(
            descriptor=self.descriptor,
            properties=properties,
            otc_info=otc_info,
            fw_version=self._fw_version,
            mqtt_connected=self.mqtt_connected,
        )

    def async_start_push(self) -> None:
        """Start the background Dreame Cloud MQTT push listener."""
        if not self.descriptor.bind_domain:
            return
        if self._push_task and not self._push_task.done():
            return

        async def _create_ssl_context():
            return await self.hass.async_add_executor_job(build_dreame_ssl_context)

        self._push_client = DreameMqttPushClient(
            did=self.descriptor.did,
            model=self.descriptor.model,
            bind_domain=self.descriptor.bind_domain,
            get_region=lambda: self.client.region,
            get_master_uid=lambda: self._master_uid or self.client.uid,
            ensure_auth=lambda force: self.client.async_ensure_auth(force_refresh=force),
            create_ssl_context=_create_ssl_context,
            on_properties=self._handle_push_properties,
            on_otc_info=self._handle_push_otc_info,
            on_connection_change=self._handle_push_connection_change,
            on_reconnected=self.async_request_refresh,
        )
        if hasattr(self.hass, "async_create_background_task"):
            self._push_task = self.hass.async_create_background_task(
                self._push_client.async_run_forever(),
                name=f"{C.DOMAIN}_mqtt_{self.descriptor.did}",
            )
        else:
            self._push_task = self.hass.async_create_task(self._push_client.async_run_forever())

    def _handle_push_properties(self, updates: Mapping[str, Any]) -> None:
        current = self.data or DreameState(
            descriptor=self.descriptor,
            fw_version=self._fw_version,
            mqtt_connected=self.mqtt_connected,
        )
        self.async_set_updated_data(current.with_properties(updates))

    def _handle_push_otc_info(self, otc_updates: Mapping[str, Any]) -> None:
        current = self.data or DreameState(
            descriptor=self.descriptor,
            fw_version=self._fw_version,
            mqtt_connected=self.mqtt_connected,
        )
        self.async_set_updated_data(current.with_otc_info(otc_updates))

    def _handle_push_connection_change(self, connected: bool) -> None:
        target_interval = (
            max(self._base_scan_interval, C.MQTT_FALLBACK_SCAN_INTERVAL)
            if connected
            else self._base_scan_interval
        )
        self.update_interval = timedelta(seconds=target_interval)
        if self.data is not None:
            self.async_set_updated_data(self.data.with_mqtt_connected(connected))

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
            current = self.data or DreameState(
                descriptor=self.descriptor,
                fw_version=self._fw_version,
                mqtt_connected=self.mqtt_connected,
            )
            self.async_set_updated_data(current.with_property(*optimistic_property))
        if schedule_refresh:
            delays = (5.0,) if self.mqtt_connected else (2.0, 5.0)
            self.async_schedule_follow_up_refresh(delays=delays)

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
        for attr in ("_push_task", "_follow_up_task"):
            task = getattr(self, attr)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            setattr(self, attr, None)
        self._push_client = None
