"""Cloudflare API client for the Cloudflare Route Control integration.

The client talks to the Cloudflare tunnel configuration endpoint and
mirrors the behaviour of the original ``cloudflare_routing`` shell script:
enabling a route inserts an ingress rule just before the final catch-all
rule, disabling a route removes it, and the whole configuration is then
put back.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareApiError(Exception):
    """Raised when the Cloudflare API returns an error."""


class CloudflareAuthError(CloudflareApiError):
    """Raised when the Cloudflare API rejects the credentials."""


def update_ingress_rules(
    ingress: list[dict[str, Any]],
    hostname: str,
    service: str,
    enabled: bool,
) -> list[dict[str, Any]]:
    """Return a new ingress list with the route for hostname enabled or disabled.

    Enabling inserts a ``{"hostname": ..., "service": ...}`` rule just before
    the final rule (the catch-all). Disabling removes every rule for the
    hostname. Rules for other hosts are returned unchanged, as are any
    other keys on the rules themselves.
    """
    rules = [rule for rule in ingress if rule.get("hostname") != hostname]
    if enabled:
        rule = {"hostname": hostname, "service": service}
        if rules:
            rules.insert(len(rules) - 1, rule)
        else:
            rules.append(rule)
    return rules


class CloudflareApiClient:
    """Minimal async client for the Cloudflare tunnel configuration API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        account_id: str,
        tunnel_id: str,
        api_token: str,
    ) -> None:
        self._session = session
        self._account_id = account_id
        self._tunnel_id = tunnel_id
        self._api_token = api_token

    @property
    def _url(self) -> str:
        return (
            f"{API_BASE}/accounts/{self._account_id}"
            f"/cfd_tunnel/{self._tunnel_id}/configurations"
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    async def _request(self, method: str, **kwargs: Any) -> dict[str, Any]:
        """Send a request and return the decoded ``result`` payload."""
        try:
            async with self._session.request(
                method, self._url, headers=self._headers, **kwargs
            ) as response:
                payload = await response.json()
                _LOGGER.debug(
                    "Cloudflare API %s %s -> HTTP %s",
                    method,
                    self._url,
                    response.status,
                )
                if response.status in (401, 403):
                    raise CloudflareAuthError(
                        "Cloudflare API rejected the credentials "
                        f"(HTTP {response.status})"
                    )
                response.raise_for_status()
        except aiohttp.ClientError as err:
            raise CloudflareApiError(f"Cloudflare API request failed: {err}") from err
        if not payload.get("success", False):
            errors = payload.get("errors", [])
            detail = "; ".join(
                f"{error.get('code')}: {error.get('message')}" for error in errors
            ) or "unknown error"
            raise CloudflareApiError(f"Cloudflare API error: {detail}")
        if "result" not in payload:
            raise CloudflareApiError("Cloudflare API returned no result")
        return payload["result"]

    async def get_config(self) -> dict[str, Any]:
        """Fetch the tunnel configuration."""
        result = await self._request("GET")
        return result["config"]

    async def get_enabled_hostnames(self) -> set[str]:
        """Return the hostnames that currently have an ingress rule."""
        config = await self.get_config()
        hostnames = {
            rule["hostname"]
            for rule in config.get("ingress", [])
            if rule.get("hostname")
        }
        _LOGGER.debug("Enabled routes: %s", sorted(hostnames))
        return hostnames

    async def set_route(self, hostname: str, service: str, enabled: bool) -> None:
        """Enable or disable the route for hostname.

        Fetches a fresh configuration first so a change made outside
        Home Assistant is not overwritten by a stale copy.
        """
        _LOGGER.debug(
            "Setting route %s (%s) %s",
            hostname,
            service,
            "on" if enabled else "off",
        )
        config = await self.get_config()
        new_ingress = update_ingress_rules(
            config.get("ingress", []), hostname, service, enabled
        )
        await self._request("PUT", json={"config": {**config, "ingress": new_ingress}})
