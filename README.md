# webwombat
a socket-level HTTP proxy with extensive configuration options and uses

> [!WARNING]
> You should always check with the owner of a site before creating a mirror of it. Editing websites in order to phish, impersonate someone, or spread disinformation is almost always illegal. In addition, many sites are "blocked" or filtered for a reason.
> 
> THE AUTHOR OF THIS SOFTWARE CLAIMS NO RESPONSIBILITY FOR POOR CHOICES OR ACTIONS, AND ONLY PROVIDES THIS SOFTWARE UNDER THE CONDITION THAT IT IS USED FOR POSITIVE, CONSTRUCTIVE REASONS.

## Overview
webwombat will auto-generate site certificates for you in order to "edit" HTTPS traffic

webwombat has several uses:
 - site mirror
 - reverse proxy
 - web server
 - authenticator: wrap websites with Basic Auth
 - content editor (rotate images, etc.)
 - HTTPS Tunneling
 - HTTP Proxy Compatibility
 - MITM Traffic viewer (for research purposes)
 - anything else you want

## Installation
```shell
# to use restricted ports like 80, 443, install with root privileges
sudo pip3 install webwombat
```

## Usage
Use the `wombat config.cube` command (or `python3 -m webwombat config.cube`) with a `.cube` config file (see below for config).
```shell
usage: wombat configfile [--help] [-options]

an extensive HTTP forward proxy with many configuration options

positional arguments:
  config                the path of the configuration file

options:
  -p [PORTS ...], --ports [PORTS ...]
                        the port(s) to listen on
  -h HOST, --host HOST  the host to bind to
  -w WEBSOCKET_PORT, --websocket-port WEBSOCKET_PORT
                        the port that the logging webserver listens on (<1 disables)
  -d, --raise-errors    whether or not to raise errors or handle them (debug only)
  -v {CONFIG,SSL,SOCKET,DEBUG,REQUEST,INFO,WARNING,ERROR,CRITICAL}, --log-level {CONFIG,SSL,SOCKET,DEBUG,REQUEST,INFO,WARNING,ERROR,CRITICAL}
                        sets the log level and verbosity of the server
  --help

advanced certificate options:
  advanced certificate storage and signing options

  --certdir CERTDIR     Location to store signed domain certificates
  --ca-certdir CACERTDIR
                        Location of root certificates (will be created at ~/.config/womat if empty)
  --ca-name CA_NAME     Name of CA Organization
  --cert-country CERT_COUNTRY
                        country code of certificate issuer
  --cert-email CERT_EMAIL
                        email for certificates

webwombat v0.0.0
```

## Configuration
The basic `.cube` file looks like this:
```cube
/* basic options (this is a comment) */
ports = 80, 443 /*LIST of numbers, no trailing comma*/
boolean = yes /* or no, false, true, yah, nah, etc. */
string = "hello there"
word = hello /* no spaces or symbols, etc. */
env = $HOME

/* request rewrite */
[request GET POST *.localhost /index.html /] -> [GET * /] /* strip .localhost off of domain, force GET method and redirect /index.html and / to / */
Via: Web Wombat v0.0.2 /* add Via header */

/* response rewrite */
[response 200 *] -> [*]
Via: "Web Wombat v0.0.2"
/example/TEST/gi /* replace all "example" bytes in response body with "TEST" using global and case-insensitive flags */
/\./,/gi /* replace all periods with commas */

[response 404 *] -> @returntext "404 not found" /* use custom function to return text for all 404 pages (see Transformers section below) */

[request localhost /logs] -> @showlogs /* use a custom function to show special log page on localhost root */

[request localhost] -> @setip /* use custom function for localhost root to show root cert to download */

[request CONNECT *] -> [TUNNEL *.localhost] /* any SSL requests with the method CONNECT will be forwarded to *.localhost with the special TUNNEL command for HTTPS proxy */
```

