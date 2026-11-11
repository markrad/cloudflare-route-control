"""Standalone tests for the Cloudflare API client logic.

Run with plain Python, no Home Assistant installation needed:

    python3 tests/test_api.py

``aiohttp`` is stubbed out, and ``api.py`` is loaded directly by path so
the package ``__init__`` (which imports Home Assistant) is never executed.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

# --- Stub out aiohttp (not installed in this environment) -------------------

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

# --- Load api.py directly, bypassing the package __init__ -------------------

API_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "cloudflare_route_control"
    / "api.py"
)
spec = importlib.util.spec_from_file_location("cf_api", API_PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

update_ingress_rules = api.update_ingress_rules
CloudflareApiClient = api.CloudflareApiClient
CloudflareApiError = api.CloudflareApiError
CloudflareAuthError = api.CloudflareAuthError

SAMPLE_CONFIG = {
    "ingress": [
        {"hostname": "site1.example.com", "service": "http://one:80"},
        {"hostname": "site2.example.com", "service": "http://two:80"},
        {"service": "http_status:404"},
    ],
    "warp-routing": {"enabled": False},
}


def test_update_ingress_rules() -> None:
    # Enable a new host: inserted before the catch-all, others untouched.
    result = update_ingress_rules(
        SAMPLE_CONFIG["ingress"], "site3.example.com", "http://three:80", True
    )
    assert [r.get("hostname") for r in result] == [
        "site1.example.com",
        "site2.example.com",
        "site3.example.com",
        None,
    ], result
    assert result[2] == {"hostname": "site3.example.com", "service": "http://three:80"}
    assert result[-1] == {"service": "http_status:404"}

    # Enable an existing host with a new service: replaced in place.
    result = update_ingress_rules(
        SAMPLE_CONFIG["ingress"], "site1.example.com", "http://one-new:80", True
    )
    assert [r.get("hostname") for r in result] == [
        "site2.example.com",
        "site1.example.com",
        None,
    ], result
    assert result[1]["service"] == "http://one-new:80"

    # Disable a host: removed, everything else unchanged.
    result = update_ingress_rules(SAMPLE_CONFIG["ingress"], "site2.example.com", "", False)
    assert [r.get("hostname") for r in result] == ["site1.example.com", None], result

    # Disable a host that is not there: unchanged.
    result = update_ingress_rules(SAMPLE_CONFIG["ingress"], "nope.example.com", "", False)
    assert result == SAMPLE_CONFIG["ingress"], result

    # Empty ingress: the rule is simply appended.
    assert update_ingress_rules([], "a.example.com", "http://a:80", True) == [
        {"hostname": "a.example.com", "service": "http://a:80"}
    ]

    # Only the catch-all: the rule goes before it.
    assert update_ingress_rules(
        [{"service": "http_status:404"}], "a.example.com", "http://a:80", True
    ) == [
        {"hostname": "a.example.com", "service": "http://a:80"},
        {"service": "http_status:404"},
    ]

    # Rules with extra keys (for example a path) keep those keys. The new
    # rule is inserted before the last rule, mirroring the shell script,
    # which assumes the last rule is the catch-all.
    ingress = [{"hostname": "a.example.com", "path": "/x", "service": "http://a:80"}]
    result = update_ingress_rules(ingress, "b.example.com", "http://b:80", True)
    assert result[0] == {"hostname": "b.example.com", "service": "http://b:80"}
    assert result[1] == {"hostname": "a.example.com", "path": "/x", "service": "http://a:80"}


class FakeResponse:
    """Minimal stand-in for an aiohttp response."""

    def __init__(self, status: int, payload: dict):
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

    def __init__(self, config: dict):
        self._config = config
        self.put_bodies: list[dict] = []
        self.requests: list[tuple[str, str]] = []

    def request(self, method: str, url: str, headers=None, json=None):
        self.requests.append((method, url))
        if method == "GET":
            return FakeResponse(
                200, {"success": True, "result": {"config": self._config}}
            )
        if method == "PUT":
            self.put_bodies.append(json)
            self._config = json["config"]
            return FakeResponse(200, {"success": True, "result": {}})
        raise AssertionError(f"unexpected method {method}")


class AuthFailingSession(FakeSession):
    """Fake session that rejects the credentials."""

    def request(self, method: str, url: str, headers=None, json=None):
        return FakeResponse(
            401,
            {
                "success": False,
                "errors": [{"code": 9109, "message": "Invalid access token"}],
            },
        )


class ErrorSession(FakeSession):
    """Fake session whose API reports failure."""

    def request(self, method: str, url: str, headers=None, json=None):
        return FakeResponse(
            200,
            {
                "success": False,
                "errors": [{"code": 1001, "message": "Something went wrong"}],
            },
        )


async def test_client() -> None:
    config = {
        "ingress": [
            {"hostname": "site1.example.com", "service": "http://one:80"},
            {"hostname": "site2.example.com", "service": "http://two:80"},
            {"service": "http_status:404"},
        ],
        "warp-routing": {"enabled": False},
    }
    session = FakeSession(config)
    client = CloudflareApiClient(session, "acct", "tunnel", "token")

    assert await client.get_enabled_hostnames() == {
        "site1.example.com",
        "site2.example.com",
    }

    # Enabling a new host PUTs a config with the rule before the catch-all
    # and keeps the rest of the configuration (warp-routing) intact.
    await client.set_route("site3.example.com", "http://three:80", True)
    put = session.put_bodies[-1]["config"]
    assert [r.get("hostname") for r in put["ingress"]] == [
        "site1.example.com",
        "site2.example.com",
        "site3.example.com",
        None,
    ], put
    assert put["warp-routing"] == {"enabled": False}
    assert await client.get_enabled_hostnames() == {
        "site1.example.com",
        "site2.example.com",
        "site3.example.com",
    }

    # Disabling removes the rule.
    await client.set_route("site1.example.com", "http://one:80", False)
    put = session.put_bodies[-1]["config"]
    assert [r.get("hostname") for r in put["ingress"]] == [
        "site2.example.com",
        "site3.example.com",
        None,
    ], put

    # Bad credentials surface as an auth error.
    auth_client = CloudflareApiClient(
        AuthFailingSession(config), "acct", "tunnel", "bad-token"
    )
    try:
        await auth_client.get_config()
    except CloudflareAuthError:
        pass
    else:
        raise AssertionError("expected CloudflareAuthError")

    # An unsuccessful API response surfaces as an API error.
    error_client = CloudflareApiClient(
        ErrorSession(config), "acct", "tunnel", "token"
    )
    try:
        await error_client.get_config()
    except CloudflareApiError as err:
        assert "1001" in str(err), err
    else:
        raise AssertionError("expected CloudflareApiError")


def main() -> None:
    test_update_ingress_rules()
    asyncio.run(test_client())
    print("All API tests passed.")


if __name__ == "__main__":
    main()
