# Cloudflare Route Control

Enable and disable Cloudflare Tunnel routes to published applications from
Home Assistant, so a route is only open while it is being used.

Each managed host appears as a switch. Turning a switch on adds an ingress
rule for that host to the tunnel configuration; turning it off removes the
rule. The integration polls the tunnel configuration, so the switches
always reflect the real state, even if a route is changed outside Home
Assistant.
