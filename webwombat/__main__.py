from . import WOMBAT, certs
from .config import load as load_config, get_config
from .handler import handler
from .logger import handler as loghandler, log, LogLevel
from websockets.sync.server import serve
import ssl
from . import __version__
import sys
import socket
import argparse
from threading import Thread
import websockets

from webwombat import config


def logserver():
    config = get_config()

    print(f"listening on {config.host}:{config.websocket_port} [logging websocket]")
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    ssl_context.set_servername_callback(certs.handle_ssl)
    with serve(loghandler, host=config.host, port=config.websocket_port, ssl_context=ssl_context) as server:
        server.serve_forever()

def server(port):
    config = get_config()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((config.host, port))

    print(f'listening on {config.host}:{port}')
    listener.listen()

    threads = []
    while True:
        try:
            conn, _ = listener.accept()
            thread = Thread(target=handler, args=[conn, port])
            threads.append(thread)
            thread.start()
        except KeyboardInterrupt:
            break
    print(f"port {port} process shutting down...")
    while len(threads) > 0:
        threads.pop(0).join()

def main(args = sys.argv[1:]):
    log(LogLevel.INFO, f"started webwombat server v{__version__}")

    parser = argparse.ArgumentParser(description=WOMBAT + 'a filter-bypass proxy and site mirror with extensive configuration options', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('config', default="~/.config/wombat/config.cube", help='the path of the configuration file')
    # parser.add_argument('-p', '--port', type=int, default=443, help='the port to listen on')
    args, unknown = parser.parse_known_args(args)
    print(unknown)

    default_config = {
        "ports": [80, 443],
        "websocket_port": 842,
        "raise_errors": False,
        "certdir": "~/.cache/wombat/",
        "cacertdir": "~/.config/wombat/",
        "ca_name": "Wombat Networking Authority",
        "cert_country": "en",
        "cert_email": "m.wombat@hogwarts.edu",
    }
    load_config(args.config, default_config)
    config = get_config()

    portthreads = []

    if config.websocket_port > 0:
        websocketThread = Thread(target=logserver)
        websocketThread.start()
        portthreads.append(websocketThread)
    if not isinstance(config.ports, list):
        config.ports = [config.ports]
    for port in config.ports:
        thread = Thread(target=server, args=[port])
        thread.start()
        portthreads.append(thread)
    try:
        for child in portthreads:
            child.join()
    except KeyboardInterrupt:
        print('shutting down...')
    # print('all ports are shut down')

    return 0

if __name__ == "__main__":
    exit(main())
