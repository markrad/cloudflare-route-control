# Cloudflare Route Control
## Motivation
Cloudflare published applications are a simple and useful mechanism to host a server on a home network without opening ports on your router. Opening ports on a home network router is not recommended and becoming impossible for many due to more and more ISPs using CGNAT to save on IPv4 addresses. A Cloudflare tunnel side-steps this by having a process on the home network open a port on Cloudflare thus creating a tunnel between the two. This tunnel can then be exposed to the Internet via a hostname.

However, in some instances, you may want to have a Cloudflare route to a specific application just for certain occasions. Specifically, I host and application that I want to make available on the Internet with no authentication so that my guests can access it with just the URL. I don't want to keep that open all the time because it is essentially a mechanism anybody could use to interact with a web server on my internal network. With the advent of AI driven hacks, this has become a much more risky prospect. 

This Home Assistant integration uses the Cloudflare API and allows the user to enable or disable a route with by simply flipping a toggle on a dashboard. These toggles are also kept uptodate by periodically polling Cloudflare in case they are turned off outside the integration.

## Install
### Option 1: HACS (recommended)
The repository is compatible with HACS custom repository requirements. To add either:

1) Open HACS (or Marketplace depending upon your version).
2) In the top right of the page click **Custom Repositories**.
3) Copy the URL of this webpage (```https://github.com/markrad/cloudflare-route-control```) and paste it into the Repository field, set the type to Integration and click ADD. 
4) **Restart** Home Assistant.
5) Got **Settings** → **Devices & Services** and click **+ Add Integration**.

Alternatively, you can click the button below which will prefill the dialog box in step 3.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=markrad&repository=cloudflare-route-control)

Continue on from step 4.

### Option 2: Manual Copy

1) Clone this github repository to your local disk. 
2) Copy the directory cloudflare_route_control to your Home Assistant's ```config/custom_components``` directory.
3) **Restart** Home Assistant.
4) Got **Settings** → **Devices & Services** and click **+ Add Integration**.

## Set up
In the Add Integration form, add the Cloudflare published application domain names along with the service url that wish to manipulate. Each one will create a switch entity. Turing these on will enable the route, and turning them off will disable the route.