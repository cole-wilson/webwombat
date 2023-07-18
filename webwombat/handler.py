from io import BytesIO
import ssl
import socket

from webwombat.logger import LogLevel, log, sharemessage
import traceback
from . import messages, filters, buffers, certs, WOMBAT
from . import WOMBAT, get_config
from uuid import uuid4
# from .config import get_config

def main(browser, port, usessl, uuid):
    request = messages.Message(browser, "request")
    request.read_statusline()
    request.read_headers()

    sharemessage(uuid, 1, request) #unfiltered request
    log(LogLevel.REQUEST, f"recieved request {request}", requestid=uuid, socketid="request")
    log(LogLevel.DEBUG, f"{request} headers: {request.headers}", requestid=uuid, socketid="request")

    request = filters.filter(request)

    if request.messagetype == 'response': # return without proxying anything
        sharemessage(uuid, 4, request) #filtered request
        log(LogLevel.DEBUG, f"returning directly via custom function", requestid=uuid, socketid="response")
        response = request
        response_thread = response.send_to(browser)
        response_thread.start()
        response_thread.join()
        browser.flush()
        return
    sharemessage(uuid, 2, request) #filtered request

    remote = buffers.SocketBuffer.from_address(request['host'], request.port or port, usessl=usessl, requestid=uuid, socketid="remote")
    log(LogLevel.DEBUG, f"requesting remote for filtered {request}", requestid=uuid, socketid="remote")

    send_thread = request.send_to(remote)
    send_thread.start()

    if request.method == 'TUNNEL':
        remote.disablelogging()
        browser.disablelogging()
        while True:
            data = remote.read(1)
            if data == b"":
                break
            try:
                browser.write(data)
            except BrokenPipeError:
                break
        remote.enablelogging()
        browser.enablelogging()
        response = messages.Message(BytesIO(), "response")
        response.status = 200
        response.reason = "Connection Established"
        sharemessage(uuid, 4, response)

    else:
        response = messages.Message(remote, "response")
        response.read_statusline()
        response.read_headers()
        log(LogLevel.DEBUG, f"got remote answer {response}", requestid=uuid, socketid="remote")
        sharemessage(uuid, 3, response)#unfiltered response

        response = filters.filter(response)

        sharemessage(uuid, 4, response)#filtered response

        log(LogLevel.DEBUG, f"sending response to browser/requester {response}", requestid=uuid, socketid="request")

        get_thread = response.send_to(browser)
        get_thread.start()

        send_thread.join()
        get_thread.join()

        remote.close()
        browser.flush()

    return

def handler(sock, port, uuid):
    config = get_config()
    start_byte = sock.recv(1, socket.MSG_PEEK)
    log(LogLevel.SSL, f"reading start byte... {start_byte}", uuid, "request")
    usessl = False
    if start_byte == b"\x16":
        log(LogLevel.SSL, f"using SSL for request {uuid}", uuid, "request")
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.set_servername_callback(certs.handle_ssl)
        sock = ssl_context.wrap_socket(sock, server_side=True)
        usessl = True
    else:
        log(LogLevel.SSL, f"NOT using SSL {uuid} (plain HTTP request)", uuid, "request")

    rfile, wfile = sock.makefile('rb'), sock.makefile('wb', buffering=0)


    browser = buffers.SocketBuffer(rfile, wfile, requestid=uuid, socketid="request")
    try:
        main(browser, port, usessl=usessl, uuid=uuid)
    except Exception as error:
        error_text = traceback.format_exc()
        log(LogLevel.ERROR, error_text, requestid=uuid)

        if not config.raise_errors:
            error_text = WOMBAT + type(error).__name__ + ":\n" + str(error)

        browser.write(b"HTTP/1.1 502 Broken Wombat\r\nContent-Length: " + str(len(error_text.encode())).encode() + b"\r\n\r\n" + error_text.encode())

        if config.raise_errors:
            raise error
    browser.flush()
    sock.close()
