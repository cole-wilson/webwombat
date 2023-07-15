import ssl
import socket
from . import messages, filters, buffers, certs, WOMBAT
from . import WOMBAT
from .config import get_config

def main(browser, port, usessl):
    request = messages.Message(browser, "request")
    request.read_statusline()
    request.read_headers()

    request = filters.filter(request)

    if request.messagetype == 'response': # return without proxying anything
        response = request
        response_thread = response.send_to(browser)
        response_thread.start()
        response_thread.join()
        browser.flush()
        return

    remote = buffers.SocketBuffer.from_address(request['host'], request.port or port, usessl, fstring = "│ {m} │    │", rcolor = "red", wcolor = "yellow", read_mark = "->", write_mark = "<-")

    send_thread = request.send_to(remote)
    send_thread.start()

    response = messages.Message(remote, "response")
    response.read_statusline()
    response.read_headers()

    response = filters.filter(response)

    get_thread = response.send_to(browser)
    get_thread.start()

    send_thread.join()
    get_thread.join()

    remote.close()
    browser.flush()
    return

def handler(sock, port):
    config = get_config()
    start_byte = sock.recv(1, socket.MSG_PEEK)
    usessl = False
    if start_byte == b"\x16":
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.set_servername_callback(certs.handle_ssl)
        sock = ssl_context.wrap_socket(sock, server_side=True)
        usessl = True
    rfile, wfile = sock.makefile('rb'), sock.makefile('wb', buffering=0)
    browser = buffers.SocketBuffer(rfile, wfile, fstring = "│    │ {m} │", read_mark = "<-", write_mark = "->")
    try:
        main(browser, port, usessl=usessl)
    except Exception as error:
        if config.raise_errors:
            raise error
        error_text = WOMBAT.encode() + type(error).__name__.encode('utf-8') + b":\n" + str(error).encode('utf-8')
        browser.write(b"HTTP/1.1 502 Broken Wombat\r\nContent-Length: " + str(len(error_text)).encode('utf-8') + b"\r\n\r\n" + error_text)
    browser.flush()
    sock.close()
