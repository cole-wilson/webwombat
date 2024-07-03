from webwombat import get_config, get_rules
from webwombat.messages import Message
import io
import os
import json
import base64

def returnfile(_, path, code=200, contentType="text/plain", reason="", headers={}):
    with open(path, 'rb') as file:
        filedata = file.read()
    response = _bytestomessage(filedata, code, reason=reason, headers={"Content-Type": contentType, **headers})
    return response

def returntext(_, t, code=200, contentType="text/plain", reason="", headers={}):
    return _bytestomessage(t.encode(), code, reason=reason, headers={"Content-Type": contentType, **headers})

def notfound(m):
    return returntext(m, "404 Page Not Found", code=404, reason="Not Found")

def switchport(m, port):
    m.port = port
    return m

def redirect(m, url):
    return returntext(m, "redirect", code=302, reason="Redirect", headers={"Location":url})

def basicauth(m, username, password, proxy=True, realm="authentication required", message="auth required"):
    prefix = ('proxy-' if proxy else '')
    if prefix + 'authorization' in m:
        userpass = m[prefix + 'authorization']
        given_u, given_p = base64.b64decode(userpass.strip("Basic ").encode()+b"=").decode().split(":")
        if given_p == password and given_u == username:
            return m
    headers = {"Proxy-Authenticate":f"Basic realm=\"{realm}\""} if proxy else {"WWW-Authenticate":f"Basic realm=\"{realm}\""}
    return returntext(m, message, code=401, headers=headers)


def _bytestomessage(b, code, reason="", headers={}):
    response = io.BytesIO()
    response.write(b"HTTP/1.1 " + str(code).encode() + b" " + reason.encode() + b" \r\n")
    response.write(b"Content-Length: " + str(len(b)).encode() + b"\r\n")
    response.write(b"\n")
    response.write(b)
    response.flush()
    response.seek(0)

    message = Message(response, 'response')
    message.read_statusline()
    message.read_headers()

    for k, v in headers.items():
        message[k] = v

    message.skiprest = True

    return message

def servedirectory(m, files={}):
    if m.locator in files:
        localpath, mime = files[m.locator]
        return returnfile(m, localpath, contentType=mime)
    else:
        return notfound(m)

def setup(m, proxyDomain=None):
    config = get_config()
    if m.locator == "/":
        return returnfile(m, _staticpath("setup/index.html"), code=200, contentType='text/html', reason="Okay")
    elif m.locator == "/proxy.pac" and proxyDomain is not None:
        return returntext(m, "function FindProxyForURL(url, host) {return 'PROXY " + proxyDomain + ":" + str(config.ports[0]) + "'}", contentType="application/x-ns-proxy-autoconfig")
    elif m.locator == "/cert.pem":
        return returnfile(m, os.path.expanduser(config.cacertdir) + "ca_cert.pem")
    else:
        return notfound(m)

def _staticpath(subpath):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/webwombat/static/" + subpath.lstrip("/")

def configurator(m):
    class CustomEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__
    rules = get_rules()

    if m.locator == "/rules.json":
        return returntext(m, json.dumps(rules, cls=CustomEncoder), contentType="application/json")
    else:
        return servedirectory(m, {
            "/": (_staticpath("configurator/index.html"), "text/html"),
            "/main.js": (_staticpath("configurator/main.js"), "application/javascript"),
            "/style.css": (_staticpath("configurator/style.css"), "text/css"),
            "/vue.js": (_staticpath("vue.js"), "application/javascript"),
        })

def showlogs(m):
    return servedirectory(m, {
        "/": (_staticpath("logs/index.html"), "text/html"),
        "/main.js": (_staticpath("logs/main.js"), "application/javascript"),
        "/vue.js": (_staticpath("vue.js"), "application/javascript"),
    })
