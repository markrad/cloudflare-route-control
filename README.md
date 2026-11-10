# cloudflare-route-control
## Motivation
Cloudflare published applications are a simple and useful mechanism to host a server on a home network without opening ports on your router, not recommended and becoming impossible for many due to more and more ISPs using CGNAT to save on IPv4 addresses.

However, in some instances, you may want to have a Cloudflare route to a specific application just for certain occasions. Specifically, I host and application that I want to make available on the Internet with no authentication so that my guests can access with just the URL. I don't want to keep that open all the time because it is essentially a mechanism anybody could use to interact with a web server on my internal network. With the advent of AI driven hacks, this has become a much more risky prospect. 

This project uses the Cloudflare API and allows the user to enable or disable a route with a simple script, thus one can keep it open only for the time it is being used and make it inaccesible the rest of the time.

Since I also use Home Assistant, which I can always access from outside my network, there is also a Home Assistant Lovelace card and instructions describing how to enable route enabling and diabling from that card. There is currently no simple HACS install because frankly I have not researched that.

## Components
In the repository, you will find the following components:
  * cloudflare_routing
  * .cf-env-sample
  * cloudflare_shell_commands.yaml
  * cloudflare_managed_hosts.yaml
  * cloudflare-hosts-card.js
  * cloudflare-script.yaml

1) ```cloudflare_routing```: This is the script that interacts with Cloudflare to manipulate the routes. It has a variety of options as described in the script's help description.
    ```
    Usage: cloudflare_routing action host service [options]

    Arguments:
    action:        The action to perform
                    status-all - returns all active cloudflare routes
                    status - returns the status of a specified route - requires host
                    on - turns on a route - requires host and service
                    off - turns off a route - requires host
    host:          The host name associated with the route as in myapp.example.com
    service:       The service to call on your local network - a reverse proxy for example
    -h, --help     Show this help message

    Examples:
    cloudflare_routing status-all
    cloudflare_routing on your.example.com http://nginx:80

    Note:
    A file called .cf-env must be in the same directory. It's format is:

    ACCOUNT_ID=<Cloudflare account id>
    TUNNEL_ID=<Cloudflare tunnel id>
    CF_API_TOKEN=<Cloudflare API token>
    ``` 
    In essence, this script will allow you to enable or disable a cloudflare route into your home network, or show the status of a specific host or all hosts. Note that the script is unable to acquire information about disabled hosts so any host it can't find will be deemed as inactive.

    #### Save this file in your Home Assistant config directory

2) ```.cf-env-sample```: This file is an example of how the .cf-env file needs to be. Fill in the required information and save it as ```.cf-env```. It looks like this:
    ```
    # Rename this to .cf-env and fill out the required fields below

    ACCOUNT_ID=<Cloudflare Account Id>
    TUNNEL_ID=<Cloudflare Tunnel Id>
    CF_API_TOKEN=<Cloudflare API Token>
    ```

    #### Save .cf-env in your Home Assistant config directory

The remaining components enable the routes to be enabled or disabled from a page in Home Assistant.

3) ```cloudflare_shell_commands.yaml```: This should be added to your Home Assistant ```config/configuration.yaml```. It is designed to be added using the structure
    ```yaml
    shell_command: !include cloudflare_shell_commands.yaml
    ```
    If you already have other shell commands you may need to modify this.

    #### Save this file in your Home Assistant config directory
4) ```cloudflare_managed_hosts.yaml```: This file lists the routes that you wish to control. All of the other Home Assistant automations use this as their source of truth. It is a block of embedded JSON that lists one or more sections each containing one or more hosts. The Lovelace card will use the sections to group hosts together with a heading from the section text.

    Modify this file to list the hosts you wish to control and merge it into the template section of the configuration.yaml file. 

5) ```cloudflare-hosts-card.js```: This will present each host with a route into your network and
    a toggle switch. When the toggle is turned off, it will disable the route. When it is turned on,
    it will enable the route. To add this file:

    1. Create a directory in home assistant's ```config/www directory``` called ```cloudflare-hosts-card```. Copy this file to that directory. 
    
    2. In Home Assistant, navigate to Settings -> Dashboards. On that screen click the three buttons in the top right and select Resources from the menu. 
    
    3. Click the + Add resource button. In the dialog set the radio button to JavaScript module and the URL to ```/local/cloudflare-hosts-card/cloudflare-hosts-card.js```. This card can now be added to a Lovelace dashboard.

6) ```cloudflare_script.yaml``` This is a home assistant script that actually calls the shell script. It will need to be added to the scripts in home assistant's config directory.