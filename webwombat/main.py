import os
import ssl
import buffers
import messages
import filters
import certs
import socket
from pathlib import Path
from threading import Thread

PORT = 443
WOMBAT = rb"""   ^=---=^-="'````'"=_      
  /       \           ""\   
  | .  .  |              \  
   \_Q___/        /      /  
    \ \/   _==_   \     /   
    |_/___;"   \___\___;    
"""

def main(browser): 
    request = messages.Message(browser, filters.normalize)
    remote = buffers.SocketBuffer.from_address(request.host, request.port, read_mark=" > ", write_mark=" < ", fstring="|{m}|   |",wcolor="yellow", rcolor="red")
    send_thread = request.transfer_body(remote)
    send_thread.start()

    response = messages.Message(remote, filters.wombatize)
    get_thread = response.transfer_body(browser)
    get_thread.start()

    send_thread.join()
    get_thread.join()

    browser.flush()
    remote.close()

def handler(conn):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    ssl_context.set_servername_callback(certs.handle_ssl)
    sock = ssl_context.wrap_socket(conn, server_side=True)
    rfile, wfile = sock.makefile('rb'), sock.makefile('wb', buffering=0)
    browser = buffers.SocketBuffer(rfile, wfile, fstring="|   |{m}|")
    try:
        main(browser)
    except Exception as error:
        error_text = WOMBAT + type(error).__name__.encode('utf-8') + b":\n" + str(error).encode('utf-8')
        browser.write(b"HTTP/1.1 502 Broken Wombat\r\nContent-Length: " + str(len(error_text)).encode('utf-8') + b"\r\n\r\n" + error_text)
    browser.flush()
    sock.close()

if __name__ == "__main__":
    threads = []
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('', PORT))
    listener.listen()

    while True:
        try:
            conn, _ = listener.accept()
            thread = Thread(target=handler, args=[conn])
            threads.append(thread)
            thread.start()
        except KeyboardInterrupt:
            break

    print('\n\nwaiting for threads to close...')
    while len(threads) > 0:
        threads.pop(0).join()

