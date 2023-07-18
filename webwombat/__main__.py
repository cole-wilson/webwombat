from uuid import uuid4

from webwombat.messages import CaseInsensitiveDict
from . import WOMBAT, get_config
from .configs import load as load_config
from .handler import handler
from .logger import logserver, log, LogLevel
from . import __version__
import sys
import socket
import argparse
from time import sleep
from threading import Thread
import threading
import traceback


this = sys.modules[__name__]


def server(port):
    try:
        config = get_config()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((config.host, port))

        log(LogLevel.INFO, f'listening on {config.host}:{port}')
        listener.listen()

        threads = []
        while True:
            try:
                conn, _ = listener.accept()
                uuid = uuid4().hex[:6]
                thread = Thread(target=handler, args=[conn, port, uuid], name=f":{port}:{uuid}")
                threads.append(thread)
                thread.start()
            except KeyboardInterrupt:
                break
        log(LogLevel.DEBUG, f"port {port} processes shutting down...")
        while len(threads) > 0:
            threads.pop(0).join()
    except Exception:
        log(LogLevel.CRITICAL, "Exception in main server() function:\n" + traceback.format_exc())

def run(**kwargs):
    return main(args=kwargs)

def main(args = sys.argv[1:]):
    default_config = {
        "ports": [80, 443],
        "host": "",
        "websocket_port": 842,
        "raise_errors": False,
        "loglevel": "INFO",

        "certdir": "~/.cache/wombat/",
        "cacertdir": "~/.config/wombat/",
        "ca_name": "Wombat Networking Authority",
        "cert_country": "en",
        "cert_email": "m.wombat@hogwarts.edu",
    }
    if isinstance(args, list):
        parser = argparse.ArgumentParser(
            description=WOMBAT + '\nan extensive HTTP forward proxy with many configuration options',
            epilog="webwombat v"+__version__,
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False,
            usage='%(prog)s configfile [--help] [-options]',
            argument_default=argparse.SUPPRESS,
        )
        parser.add_argument('config', default="~/.config/wombat/config.cube", help='the path of the configuration file')
        parser.add_argument('-p', '--ports', dest='ports', type=int, nargs='*', help='the port(s) to listen on')
        parser.add_argument('-h', '--host', dest='host', type=str, help='the host to bind to')
        parser.add_argument('-w', '--websocket-port', dest='websocket_port', type=int, help='the port that the logging webserver listens on (<1 disables)')
        parser.add_argument('-d', '--raise-errors', dest='raise_errors', action='store_true', help="whether or not to raise errors or handle them (debug only)")
        parser.add_argument('-v', '--log-level', dest='loglevel', choices=["CONFIG", "SSL", "SOCKET", "DEBUG",  "REQUEST","INFO", "WARNING", "ERROR", "CRITICAL"], help="sets the log level and verbosity of the server")
        parser.add_argument('--help', action='help')
        certgr = parser.add_argument_group("advanced certificate options", description="advanced certificate storage and signing options")
        certgr.add_argument('--certdir', dest='certdir', help="Location to store signed domain certificates")
        certgr.add_argument('--ca-certdir', dest='cacertdir', help="Location of root certificates (will be created at ~/.config/womat if empty)")
        certgr.add_argument('--ca-name', dest='ca_name', help="Name of CA Organization")
        certgr.add_argument('--cert-country', dest="cert_country", help="country code of certificate issuer")
        certgr.add_argument('--cert-email', dest="cert_email", help="email for certificates")
        args = parser.parse_args(args)
        load_config(args.config, default_config, vars(args))
    else:
        args = CaseInsensitiveDict(args)
        if 'config' not in args:
            log(LogLevel.CRITICAL, "no config provided for run() function")
            return 1
        load_config(args.config, default_config, args)


    config = get_config()

    log(LogLevel.INFO, f"started webwombat server v{__version__}")

    portthreads = []

    if config.websocket_port > 0:
        websocketThread = Thread(target=logserver, daemon=True, name="logserver")
        websocketThread.start()
        portthreads.append(websocketThread)
    else:
        log(LogLevel.DEBUG, f"not starting log websocket server, port<1")
    if not isinstance(config.ports, list):
        config.ports = [config.ports]
    for port in config.ports:
        thread = Thread(target=server, args=[port], daemon=True, name=f":{port}")
        thread.start()
        portthreads.append(thread)
    try:
        while True:
            sleep(1)
            # log(LogLevel.CRITICAL, threading.active_count())
    except KeyboardInterrupt:
        log(LogLevel.WARNING, f"recieved exit code... shutting down...")
        sleep(0.3)

    return 0

if __name__ == "__main__":
    exit(main())
