from . import WOMBAT
from .config import load as load_config, get_config
from .handler import handler
import sys
import socket
from time import sleep
import argparse
import os
from threading import Thread

from webwombat import config

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
    parser = argparse.ArgumentParser(description=WOMBAT + 'a filter-bypass proxy and site mirror with extensive configuration options', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('config', default="~/.config/wombat/config.cube", help='the path of the configuration file')
    parser.add_argument('-p', '--port', type=int, default=443, help='the port to listen on')
    args = parser.parse_args(args)

    default_config = {
        "ports": [80, 443],
        "certdir": "~/.cache/wombat/",
        "cacertdir": "~/.config/wombat/",
        "ca_name": "Wombat Networking Authority",
        "cert_country": "en",
        "cert_email": "m.wombat@hogwarts.edu",
    }
    load_config(args.config, default_config)
    config = get_config()

    portthreads = []
    for port in config.ports:
        thread = Thread(target=server, args=[port])
        thread.start()
        portthreads.append(thread)
    for child in portthreads:
        child.join()
    # print('all ports are shut down')

    return 0

if __name__ == "__main__":
    exit(main())
