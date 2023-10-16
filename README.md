# webwombat
a socket-level HTTP proxy with extensive configuration options and uses

> [!WARNING]
> You should always check with the owner of a site before creating a mirror of it. Editing websites in order to phish, impersonate someone, or spread disinformation is almost always illegal. In addition, many sites are "blocked" or filtered for a reason.
> 
> THE AUTHOR OF THIS SOFTWARE CLAIMS NO RESPONSIBILITY FOR POOR CHOICES OR ACTIONS, AND ONLY PROVIDES THIS SOFTWARE UNDER THE CONDITION THAT IT IS USED FOR POSITIVE, CONSTRUCTIVE REASONS.

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Configuration](#configuration)
5. [Transformers](#transformers)
6. [Examples](#examples)
7. [the Message Object](#the-message-object)

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
Use the `wombat config.cube` command (or `python3 -m webwombat config.cube`) with a `.cube` config file (see [configuration](#configuration) section below).
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

## Transformers
You can use any python function to modify a request or response you want by using the `@module.module:function args...` syntax. 

### Making your own transformer
```python3
def switchport(message: wombat.messages.Message, arg1, arg2=None):
    message.port = arg1
    return message
```
You can modify the Message object that is passed as the first argument, or return an entirely new message using the constructor (see [Message objects](#the-message-object)).

You can also use the built-in `_bytestomessage(bytes, code, reason="", headers={})` function in webwombat.transformers you return a basic message.

If you want to prevent any other functions from editing the message you return, you can set the `message.skiprest = True` flag, which will immediately bypass any other modifications.

### Provided Transformers
A few common transformers are provided in the [webwombat/transformers.py](./webwombat/transformers.py) file. These are the default namespace, so you can refer to them just using `@function`.

|name|arguments|description|
|----|---------|-----------|
|`@returnfile`|path, code=200, contentType="text/plain", reason="", headers={}|return the file at `path` with the provided metadata (WARNING: no sandboxing, use at own risk)|
|`@returntext`|text, code=200, contentType="text/plain", reason="", headers={}|return the given text (utf-8) in the same manner as `@returnfile`|
|`@notfound`|(n/a)|return a simple not found page|
|`@switchport`|newport|switch the request port (from default like 80 to something like 8080)|
|`@basicauth`|username, password, proxy=True, realm="authentication required", message="auth required"|require basic auth for authentication, if proxy==True then it uses the proxy prefix in headers|
|`@setup`|proxyDomain=None|sets up a basic site where you can download the ca cert and also has a /proxy.pac auto-config file (if proxyDomain is set)|
|`@showlogs`|(n/a)|load a basic logging website where you can view requests using streaming websockets (not very secure)|

## the `Message` object
The `Message` object has a lot of stuff in it, but the main things are as follows:
### properties
|property|default value|description|
|--------|-------------|-----------|
|messagetype|None|'response' or 'request'|
|sourcefile|BytesIO(b"")|file object of body|
|skiprest|False|whether to skip further modifications}
|port|None (changed to original request port)|port used|
|method|None|request method|
|locator|None|path (or proxy domain) of file|
|version|None|such as HTTP/1.1|
|status|None|such as 200|
|reason|None|such as "Not Found"|
|headers|CaseInsensitiveDict({})|headers for request|
|statusline|(@property)|returns the statusline in a string|
|body_type|(@property)|body type (normal, encoded_chunks, empty, chunked)|

### methods
|method|description|
|------|-----------|
|read_statusline() -> None|fill out the above properties and read the statusline of the file object|
|read_headers() -> None|fill out headers object and read the remainder of the header of the file object|
|send_to(destination) -> Thread|return a Threead object that will send to a given SocketBuffer (you shouldn't need to use this at all)|
|get_dencoders() -> tuple[list, list]|return a list of decoders and encoders (you shouldn't need to use this at all either)|
|__bytes__(*_)|return the bytes of the head (including statusline and headers)
