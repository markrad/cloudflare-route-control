# Cloudflare Route Control

Enable and disable Cloudflare Tunnel routes to published applications from
Home Assistant, so a route is only open while it is being used.

Each managed host appears as a switch. Turning a switch on adds an ingress
rule for that host to the tunnel configuration; turning it off removes the
rule. The integration polls the tunnel configuration, so the switches
always reflect the real state, even if a route is changed outside Home
Assistant.

## Setup

1. Install this repository through HACS as a custom repository, then restart
   Home Assistant.
2. Add the Cloudflare Route Control integration and enter the account ID,
   tunnel ID, and API token (the values from your `.cf-env` file). The
   token needs permission to edit the Cloudflare Tunnel configuration.
3. Open the integration's **Configure** options and add each host you want
   to manage, with the service it points to when enabled, for example
   `http://nginx:80`.

The service is stored for each host because a disabled route cannot be
seen in the tunnel configuration, so it cannot be rediscovered from
Cloudflare.

This replaces the earlier shell script, shell commands, template sensor,
input booleans, and Lovelace card in this repository.
