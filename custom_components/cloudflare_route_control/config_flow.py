"""Config flow for the Cloudflare Route Control integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import CloudflareApiClient, CloudflareApiError, CloudflareAuthError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_ADD_HOSTNAME,
    CONF_ADD_SERVICE,
    CONF_API_TOKEN,
    CONF_HOSTS,
    CONF_REMOVE_HOSTS,
    CONF_SCAN_INTERVAL,
    CONF_TUNNEL_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_ID): TextSelector(),
        vol.Required(CONF_TUNNEL_ID): TextSelector(),
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class CloudflareRouteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cloudflare Route Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = CloudflareApiClient(
                async_get_clientsession(self.hass),
                user_input[CONF_ACCOUNT_ID],
                user_input[CONF_TUNNEL_ID],
                user_input[CONF_API_TOKEN],
            )
            try:
                await client.get_config()
            except CloudflareAuthError:
                errors["base"] = "invalid_auth"
            except CloudflareApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surface any other failure plainly
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_TUNNEL_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Cloudflare Tunnel {user_input[CONF_TUNNEL_ID][:8]}",
                    data=user_input,
                    options={
                        CONF_HOSTS: [],
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return CloudflareRouteOptionsFlow(config_entry)


class CloudflareRouteOptionsFlow(OptionsFlow):
    """Handle options for Cloudflare Route Control.

    Hosts are managed here: add a host with its service, or remove hosts
    that are no longer needed. The service must be stored for each host
    because a disabled route cannot be seen in the tunnel configuration,
    so it cannot be rediscovered from Cloudflare.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._hosts: list[dict[str, str]] = list(
            config_entry.options.get(CONF_HOSTS, [])
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            add_hostname = (user_input.get(CONF_ADD_HOSTNAME) or "").strip()
            add_service = (user_input.get(CONF_ADD_SERVICE) or "").strip()
            if add_hostname and add_service:
                if " " in add_hostname or "://" in add_hostname:
                    errors["base"] = "invalid_hostname"
                elif "://" not in add_service:
                    errors["base"] = "invalid_service"
                elif any(
                    host["hostname"] == add_hostname for host in self._hosts
                ):
                    errors["base"] = "host_exists"
                else:
                    self._hosts.append(
                        {"hostname": add_hostname, "service": add_service}
                    )
            elif add_hostname or add_service:
                errors["base"] = "host_incomplete"

            for hostname in user_input.get(CONF_REMOVE_HOSTS, []):
                self._hosts = [
                    host for host in self._hosts if host["hostname"] != hostname
                ]

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        **self.config_entry.options,
                        CONF_HOSTS: self._hosts,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )

        hosts_text = (
            "\n".join(
                f"• {host['hostname']} → {host['service']}" for host in self._hosts
            )
            or "None yet."
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_ADD_HOSTNAME): TextSelector(),
                vol.Optional(CONF_ADD_SERVICE): TextSelector(),
                vol.Optional(CONF_REMOVE_HOSTS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=[host["hostname"] for host in self._hosts],
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=10, max=3600, step=5, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"hosts": hosts_text},
        )
