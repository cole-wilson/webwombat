from webwombat.messages import Message
import io
import os

def returnfile(_, path, code=200, contentType="text/plain", reason=""):
    with open(path, 'rb') as file:
        filedata = file.read()
    response = _bytestomessage(filedata, code, reason=reason, headers={"Content-Type": contentType})
    return response

def returntext(_, t, code=200, contentType="text/plain", reason=""):
    return _bytestomessage(t.encode(), code, reason=reason, headers={"Content-Type": contentType})

def notfound(m):
    return returntext(m, "404 Page Not Found", code=404, reason="Not Found")

def switchport(m, port):
    m.port = port
    return m

def redirect(m, url):
    return _bytestomessage(b"redirect", code=302, reason="Redirect", headers={"Location":url})

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

    return message


def showlogs(m):
    return returnfile(m, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/logs.html", code=200, contentType='text/html', reason="Okay")
