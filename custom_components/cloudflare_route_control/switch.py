"""Switch platform for the Cloudflare Route Control integration."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CloudflareApiError
from .const import CONF_HOSTS, CONF_TUNNEL_ID, DOMAIN
from .coordinator import CloudflareRouteCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cloudflare route switches from a config entry."""
    coordinator: CloudflareRouteCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CloudflareRouteSwitch(coordinator, entry, host)
        for host in entry.options.get(CONF_HOSTS, [])
    )


class CloudflareRouteSwitch(
    CoordinatorEntity[CloudflareRouteCoordinator], SwitchEntity
):
    """A switch that enables or disables one Cloudflare tunnel route."""

    def __init__(
        self,
        coordinator: CloudflareRouteCoordinator,
        entry: ConfigEntry,
        host: dict[str, str],
    ) -> None:
        super().__init__(coordinator)
        self._hostname = host["hostname"]
        self._service = host["service"]
        self._attr_unique_id = f"{entry.entry_id}_{self._hostname}"
        self._attr_name = self._hostname
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_TUNNEL_ID])},
            name=f"Cloudflare Tunnel {entry.data[CONF_TUNNEL_ID][:8]}",
            manufacturer="Cloudflare",
            model="Cloudflare Tunnel",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the route is currently enabled."""
        if self.coordinator.data is None:
            return None
        return self._hostname in self.coordinator.data

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the service the route points at when enabled."""
        return {"service": self._service}

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the route."""
        await self._async_set_route(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the route."""
        await self._async_set_route(False)

    async def _async_set_route(self, enabled: bool) -> None:
        _LOGGER.debug(
            "Turning route %s %s", self._hostname, "on" if enabled else "off"
        )
        try:
            await self.coordinator.client.set_route(
                self._hostname, self._service, enabled
            )
        except CloudflareApiError as err:
            raise HomeAssistantError(
                f"Failed to set route {self._hostname}: {err}"
            ) from err
        await self.coordinator.async_refresh()
