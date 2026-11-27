"""Pure-asyncio Dreame Cloud MQTT push subscriber (zero HA imports)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
import secrets
import ssl
from typing import Any

from . import const as C
from . import protocol as P

_LOGGER = logging.getLogger(__name__)

try:
    import aiomqtt
except ImportError:  # pragma: no cover - installed in HA runtime
    aiomqtt = None  # type: ignore[assignment]


def build_dreame_ssl_context() -> ssl.SSLContext:
    """Create a verified TLS client context anchored to the Dreame broker Root CA."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cadata=C.DREAME_CLIENT_ROOT_CA)
    return ctx


class DreameMqttPushClient:
    """Maintain a resilient MQTTv311 TLS push subscription to Dreame Cloud."""

    def __init__(
        self,
        *,
        did: str,
        model: str,
        bind_domain: str,
        get_region: Callable[[], str],
        get_master_uid: Callable[[], str | None],
        ensure_auth: Callable[[bool], Awaitable[tuple[str, str]]],
        create_ssl_context: Callable[[], Awaitable[ssl.SSLContext]],
        on_properties: Callable[[dict[str, Any]], None],
        on_otc_info: Callable[[dict[str, Any]], None],
        on_connection_change: Callable[[bool], None],
        on_reconnected: Callable[[], Awaitable[None]] | None = None,
        reconnect_delays: tuple[float, ...] = C.MQTT_RECONNECT_DELAYS,
    ) -> None:
        self._did = did
        self._model = model
        self._bind_domain = bind_domain
        self._get_region = get_region
        self._get_master_uid = get_master_uid
        self._ensure_auth = ensure_auth
        self._create_ssl_context = create_ssl_context
        self._on_properties = on_properties
        self._on_otc_info = on_otc_info
        self._on_connection_change = on_connection_change
        self._on_reconnected = on_reconnected
        self._reconnect_delays = reconnect_delays
        self._ssl_context: ssl.SSLContext | None = None
        self._connected = False
        self._has_connected_once = False

    @property
    def connected(self) -> bool:
        return self._connected

    def _set_connected(self, connected: bool) -> None:
        if self._connected != connected:
            self._connected = connected
            self._on_connection_change(connected)

    async def async_run_forever(self) -> None:
        """Connect, subscribe, and dispatch push updates until cancelled."""
        if aiomqtt is None:
            _LOGGER.warning("aiomqtt is unavailable; staying on HTTP cloud polling")
            return

        attempt = 0
        force_refresh = False
        try:
            while True:
                try:
                    uid, token = await self._ensure_auth(force_refresh)
                    force_refresh = False
                    region = self._get_region()
                    host, port = P.parse_bind_domain(self._bind_domain, region)
                    if self._ssl_context is None:
                        self._ssl_context = await self._create_ssl_context()

                    master_uid = self._get_master_uid() or uid
                    client_id = P.build_mqtt_client_id(self._did, secrets.token_hex(16))
                    topics = P.build_mqtt_topics(self._did, master_uid, self._model, region)

                    _LOGGER.debug("Connecting Dreame MQTT push to %s:%s", host, port)
                    async with aiomqtt.Client(
                        hostname=host,
                        port=port,
                        username=uid,
                        password=token,
                        identifier=client_id,
                        tls_context=self._ssl_context,
                        protocol=aiomqtt.ProtocolVersion.V311,
                        clean_session=True,
                        keepalive=C.MQTT_KEEPALIVE,
                    ) as mqtt_client:
                        for topic in topics:
                            await mqtt_client.subscribe(topic, qos=0)
                        was_reconnect = self._has_connected_once
                        self._has_connected_once = True
                        attempt = 0
                        self._set_connected(True)
                        _LOGGER.debug("Subscribed Dreame MQTT push topics=%s", topics)
                        if was_reconnect and self._on_reconnected is not None:
                            try:
                                await self._on_reconnected()
                            except Exception:
                                _LOGGER.debug("Post-reconnect refresh failed", exc_info=True)

                        async for message in mqtt_client.messages:
                            kind, payload = P.parse_mqtt_message(message.payload)
                            if kind == "properties" and payload:
                                self._on_properties(payload)
                            elif kind == "otc" and payload:
                                self._on_otc_info(payload)
                except asyncio.CancelledError:
                    raise
                except P.DreameAuthError as err:
                    self._set_connected(False)
                    force_refresh = True
                    delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
                    attempt += 1
                    _LOGGER.warning("Dreame MQTT auth failed (%s); retrying in %.0fs", err, delay)
                    await asyncio.sleep(delay)
                except Exception as err:
                    self._set_connected(False)
                    # Force token refresh on MQTT auth rejection (rc=4/5) or unexpected disconnects after connect
                    err_text = str(err).lower()
                    if any(k in err_text for k in ("not authorized", "bad user", "code:5", "code 5", "rc=5")):
                        force_refresh = True
                    delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
                    attempt += 1
                    _LOGGER.debug("Dreame MQTT push disconnected (%s); retrying in %.0fs", err, delay)
                    await asyncio.sleep(delay)
        finally:
            self._set_connected(False)
