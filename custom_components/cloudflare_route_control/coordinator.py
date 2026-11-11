"""DataUpdateCoordinator for the Cloudflare Route Control integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CloudflareApiClient, CloudflareApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class CloudflareRouteCoordinator(DataUpdateCoordinator[set[str]]):
    """Poll the tunnel configuration for the set of enabled hostnames."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CloudflareApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self._async_update,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update(self) -> set[str]:
        try:
            return await self.client.get_enabled_hostnames()
        except CloudflareApiError as err:
            raise UpdateFailed(err) from err
