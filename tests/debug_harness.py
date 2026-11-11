"""Step-through debugging harness for the Cloudflare Route Control integration.

Run it under the VS Code debugger (see .vscode/launch.json,
"Debug HACS integration (harness)") and set breakpoints in
``custom_components/cloudflare_route_control/api.py``,
``coordinator.py`` or ``switch.py``.

No Home Assistant installation is needed and nothing talks to the real
Cloudflare API: the Home Assistant modules and the HTTP session are
stubbed out, and the "Cloudflare" side is an in-memory tunnel
configuration that you can watch change as you step through
``set_route``.

Good breakpoint spots:
  * ``switch.py`` ``_async_set_route`` -- a switch being flipped
  * ``api.py`` ``set_route`` -- the fresh GET, the rule change, the PUT
  * ``api.py`` ``update_ingress_rules`` -- the ingress list manipulation
  * ``coordinator.py`` ``_async_update`` -- a poll turning the config
    into the set of enabled hostnames

To try the real API instead, point the client at a real
``aiohttp.ClientSession`` with real credentials -- but note that turning
a switch on or off would then really change your tunnel routes.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import sys
import types
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "custom_components"))

# ---------------------------------------------------------------------------
# Stub out aiohttp
# ---------------------------------------------------------------------------

aiohttp_stub = types.ModuleType("aiohttp")


class ClientError(Exception):
    """Stub for aiohttp.ClientError."""


class ClientResponseError(ClientError):
    """Stub for aiohttp.ClientResponseError."""

    def __init__(self, *args, status=None, **kwargs):
        super().__init__(*args)
        self.status = status


class ClientSession:
    """Stub for aiohttp.ClientSession."""


aiohttp_stub.ClientError = ClientError
aiohttp_stub.ClientResponseError = ClientResponseError
aiohttp_stub.ClientSession = ClientSession
sys.modules["aiohttp"] = aiohttp_stub

# ---------------------------------------------------------------------------
# Stub out the Home Assistant modules the integration imports
# ---------------------------------------------------------------------------


class UpdateFailed(Exception):
    """Stub for homeassistant.helpers.update_coordinator.UpdateFailed."""


class DataUpdateCoordinator:
    """Minimal stand-in for HA's DataUpdateCoordinator."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(
        self, hass, logger, *, name=None, update_method=None, update_interval=None
    ):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True

    async def async_refresh(self):
        try:
            self.data = await self.update_method()
            self.last_update_success = True
        except Exception as err:
            self.last_update_success = False
            raise UpdateFailed(err) from err

    async def async_config_entry_first_refresh(self):
        await self.async_refresh()


class CoordinatorEntity:
    """Minimal stand-in for HA's CoordinatorEntity."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator, context=None):
        self.coordinator = coordinator

    async def async_write_ha_state(self):
        pass


class SwitchEntity:
    """Stub for homeassistant.components.switch.SwitchEntity."""


class HomeAssistantError(Exception):
    """Stub for homeassistant.exceptions.HomeAssistantError."""


class HomeAssistant:
    """Stub for homeassistant.core.HomeAssistant."""


class ConfigEntry:
    """Stub for homeassistant.config_entries.ConfigEntry."""

    def __init__(self, entry_id, data, options):
        self.entry_id = entry_id
        self.data = data
        self.options = options


class DeviceInfo(dict):
    """Stub for homeassistant.helpers.device_registry.DeviceInfo."""

    def __init__(self, **kwargs):
        super().__init__(kwargs)


def _async_get_clientsession(hass):
    raise NotImplementedError("the harness does not use real HTTP sessions")


def _register_stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


_register_stub("homeassistant")
_register_stub("homeassistant.config_entries", ConfigEntry=ConfigEntry)
_register_stub("homeassistant.core", HomeAssistant=HomeAssistant)
_register_stub("homeassistant.components")
_register_stub("homeassistant.components.switch", SwitchEntity=SwitchEntity)
_register_stub("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
_register_stub("homeassistant.helpers")
_register_stub(
    "homeassistant.helpers.aiohttp_client",
    async_get_clientsession=_async_get_clientsession,
)
_register_stub("homeassistant.helpers.device_registry", DeviceInfo=DeviceInfo)
_register_stub(
    "homeassistant.helpers.entity_platform",
    AddEntitiesCallback=object,  # only used in a type hint
)
_register_stub(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=DataUpdateCoordinator,
    UpdateFailed=UpdateFailed,
    CoordinatorEntity=CoordinatorEntity,
)

# ---------------------------------------------------------------------------
# Fake Cloudflare API: an in-memory tunnel configuration
# ---------------------------------------------------------------------------


class FakeResponse:
    """Minimal stand-in for an aiohttp response."""

    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status >= 400:
            raise ClientResponseError(status=self.status)


class FakeSession:
    """Fake aiohttp session backed by an in-memory tunnel config."""

    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.put_bodies = []

    def request(self, method, url, headers=None, json=None):
        if method == "GET":
            return FakeResponse(
                200, {"success": True, "result": {"config": self.config}}
            )
        if method == "PUT":
            self.put_bodies.append(json)
            self.config = json["config"]
            return FakeResponse(200, {"success": True, "result": {}})
        raise AssertionError(f"unexpected method {method}")


SAMPLE_CONFIG = {
    "ingress": [
        {"hostname": "site1.example.com", "service": "http://one:80"},
        {"hostname": "site2.example.com", "service": "http://two:80"},
        {"service": "http_status:404"},
    ],
    "warp-routing": {"enabled": False},
}

# Import the real integration code (stubs above must be registered first).
from cloudflare_route_control.api import CloudflareApiClient  # noqa: E402
from cloudflare_route_control.const import CONF_HOSTS, CONF_TUNNEL_ID  # noqa: E402
from cloudflare_route_control.coordinator import (  # noqa: E402
    CloudflareRouteCoordinator,
)
from cloudflare_route_control.switch import CloudflareRouteSwitch  # noqa: E402


async def main():
    session = FakeSession(SAMPLE_CONFIG)
    client = CloudflareApiClient(session, "acct", "tunnel", "token")
    coordinator = CloudflareRouteCoordinator(HomeAssistant(), client, scan_interval=30)
    entry = ConfigEntry(
        "test-entry",
        {CONF_TUNNEL_ID: "abcdef1234567890"},
        {
            CONF_HOSTS: [
                {"hostname": "site1.example.com", "service": "http://one:80"}
            ]
        },
    )

    # First poll: fills coordinator.data with the enabled hostnames.
    await coordinator.async_config_entry_first_refresh()
    print("enabled after first refresh:", sorted(coordinator.data))

    switch = CloudflareRouteSwitch(
        coordinator,
        entry,
        {"hostname": "site1.example.com", "service": "http://one:80"},
    )
    print("site1 switch is_on:", switch.is_on)

    await switch.async_turn_off()
    print("enabled after turn_off:", sorted(coordinator.data))
    print("ingress now:", session.config["ingress"])

    await switch.async_turn_on()
    print("enabled after turn_on:", sorted(coordinator.data))
    print("ingress now:", session.config["ingress"])


if __name__ == "__main__":
    asyncio.run(main())
