# Cloudflare Route Control
## Motivation
Cloudflare published applications are a simple and useful mechanism to host a server on a home network without opening ports on your router. Opening ports on a home network router is not recommended and becoming impossible for many due to more and more ISPs using Carrier-Grade NAT (CGNAT) to save on IPv4 addresses. A Cloudflare tunnel side-steps this by having a process on the home network open a port on Cloudflare thus creating a tunnel between the two. This tunnel can then be exposed to the Internet via a hostname.

However, in some instances, you may want to have a Cloudflare route to a specific application just for certain occasions. Specifically, I host an application that I want to make available on the Internet with no authentication so that my guests can access it with just the URL. I don't want to keep that open all the time because it is essentially a mechanism anybody could use to interact with a web server on my internal network. With the advent of AI driven hacks, this has become a much more risky prospect. 

This Home Assistant integration uses the Cloudflare API and allows the user to enable or disable a route with by simply flipping a toggle on a dashboard. These toggles are also kept up to date by periodically polling Cloudflare in case they are turned off outside the integration.

## Install
### Option 1: HACS (recommended)
The repository is compatible with HACS custom repository requirements. To add either:

1) Open HACS (or Marketplace depending upon your version).
2) In the top right of the page click **Custom Repositories**.
3) Copy the URL of this webpage (```https://github.com/markrad/cloudflare-route-control```) and paste it into the Repository field, set the type to Integration and click ADD. 
4) **Restart** Home Assistant.
5) Go to **Settings** → **Devices & Services** and click **+ Add Integration**.

Alternatively, you can click the button below which will prefill the dialog box in step 3.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=markrad&repository=cloudflare-route-control&category=integration)

Continue on from step 4.

### Option 2: Manual Copy

1) Clone this GitHub repository to your local disk. 
2) Copy the directory Cloudflare_route_control to your Home Assistant's ```config/custom_components``` directory.
3) **Restart** Home Assistant.
4) Got **Settings** → **Devices & Services** and click **+ Add Integration**.

## Set up
In the Add Integration form, you will need to provide the following from your Cloudflare account which are all obtained from their website (https://dash.cloudflare.com):
* Cloudflare Account ID:
  
  From the Cloudflare homepage click **Domains** → **Overview**.

  Click the domain you wish to control.

  On the right-hand side of the page towards the bottom, you will see Account ID. Copy that and paste it into the integration's Account ID box in the form.
* Tunnel ID:

  From the Cloudflare homepage, click **Networking** → **Tunnels**.

  Click the tunnel name you wish to control.

  Copy the Tunnel ID from the **Tunnel details** box on the right. Paste that into the integration's Tunnel ID box in the form.

* API Token: 

  Generate this by clicking the person icon in the top right corner and pick **Profile** from the menu. 
  
  Click **API Tokens** from the left-hand tabs. 

  Click **+ Create Token**
  
  Use **Start from scratch** and click **Start with an Account policy**.

  In the next screen, give it a name, leave it at include All accounts. Enter tunnel in the permissions search and for the Cloudflare Tunnel, grant **Edit** access.

  I left the expiration at **No expiration** and did not add any IP address filtering rules since my IP address can change.

  Click **Continue to summary** and, if you are happy, click **Create Token**.

  Copy the string in the top box. This is the value you need to provide as your API Token. Paste it into the integration's API box in the form.

  Using the curl command to test the token is probably not a bad idea, but optional.



Add the Cloudflare published application domain names along with the service URL that you wish to manipulate. Each one will create a switch entity. Turning these on will enable the route, and turning them off will disable the route.