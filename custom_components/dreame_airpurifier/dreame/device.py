from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from ..utils import maybe_json, parse_key
from .models import DreameDeviceDescriptor
from .protocol import DreameSmartlifeClient


@dataclass(slots=True)
class DreameSmartlifeState:
    descriptor: DreameDeviceDescriptor
    otc_info: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    discovered_properties: dict[str, Any] = field(default_factory=dict)
    last_probe_at: datetime | None = None


class DreameSmartlifeDevice:
    def __init__(self, client: DreameSmartlifeClient, descriptor: DreameDeviceDescriptor) -> None:
        self._client = client
        self._descriptor = descriptor
        self.state = DreameSmartlifeState(descriptor=descriptor)

    @property
    def descriptor(self) -> DreameDeviceDescriptor:
        return self._descriptor

    async def async_refresh(self, watched_keys: list[str]) -> DreameSmartlifeState:
        self.state.otc_info = await self._client.async_get_otc_info(self._descriptor.did)
        props = await self._client.async_get_props(self._descriptor.did, watched_keys)
        current: dict[str, Any] = {}
        for item in props:
            key = item.get("key")
            if not key:
                continue
            current[str(key)] = maybe_json(item.get("value"))
        self.state.properties = current
        return self.state

    async def async_probe_properties(self, max_siid: int, max_piid: int) -> DreameSmartlifeState:
        self.state.discovered_properties = await self._client.async_probe_properties(
            self._descriptor.bind_domain,
            self._descriptor.did,
            max_siid,
            max_piid,
        )
        self.state.last_probe_at = dt_util.utcnow()
        return self.state

    async def async_set_property(self, key: str, value: Any) -> Any:
        siid, piid = parse_key(key)
        result = await self._client.async_set_properties(
            self._descriptor.bind_domain,
            self._descriptor.did,
            [{"siid": siid, "piid": piid, "value": value}],
        )
        self.state.properties[key] = value
        return result

    async def async_action(self, siid: int, aiid: int, inputs: list[dict[str, Any]] | None = None) -> Any:
        return await self._client.async_action(
            self._descriptor.bind_domain,
            self._descriptor.did,
            siid,
            aiid,
            inputs or [],
        )

    async def async_send_raw_command(self, method: str, params: Any) -> Any:
        return await self._client.async_send_command(
            self._descriptor.bind_domain,
            self._descriptor.did,
            method,
            params,
        )
