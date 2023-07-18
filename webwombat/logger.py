from queue import Queue
import ssl
import json
from threading import current_thread
from . import certs, get_config
from blessed import Terminal
from datetime import datetime
from time import time
from enum import IntEnum
from websockets.sync.server import serve
import traceback


messages = Queue()
WIDTH = 100

class LogLevel(IntEnum):
    WEBPAGE_INFO = -99
    CONFIG = 0
    SSL = 10
    SOCKET = 20
    DEBUG = 30
    REQUEST = 35
    INFO = 40
    WARNING = 50
    ERROR = 60
    CRITICAL = 70

term = Terminal()

def sharemessage(uuid, id, message):
    log(LogLevel.WEBPAGE_INFO, {
        "type": message.messagetype,
        "method": message.method,
        "path": message.locator,
        "version": message.version,
        "status": message.status,
        "reason": message.reason,
        "headers": message.headers,
        "port": message.port,
        "time": time()
    }, requestid=uuid, socketid=id, optype="?")

def log(level, data, requestid=None, socketid=None, optype=None):
    config = get_config()
    threadname = current_thread().name
    if config is None:
        loglevel = LogLevel.INFO
    else:
        loglevel = LogLevel[config.loglevel.upper()]

    now = datetime.now()

    if isinstance(data, int):
        data = str(data)
    if not isinstance(data, str) and not isinstance(data, dict):
        data = repr(bytes(data))[2:-1]


    messages.put(json.dumps({
        "time": time(),
        "data": data,
        "level": level.name,
        "requestid": requestid,
        "socketid": socketid,
        "optype": optype
    }))

    if level.value < loglevel.value: return

    hsh = ""
    if requestid is not None:
        hsh = f"{requestid or ''}.{socketid or ''} {optype or ''}: "

    if "\n" in data:
        datalines = data.split("\n")
    else:
        datalines = [data[i:i+WIDTH] for i in range(0, len(data), WIDTH)]

    if (len(datalines) < 1): return

    line = f"[{now}] {level.name.ljust(8)} {hsh}" + datalines[0] + "\n"
    for wrap in datalines[1:]:
        line += f" {' '*len(str(now))}  {' '*(8)} {' '*len(hsh)}" + wrap + "\n"
    line = line.rstrip("\n")

    if   level <= LogLevel.SOCKET: line = term.dimgrey(line)
    elif level == LogLevel.DEBUG: ...
    elif level == LogLevel.REQUEST: line = term.cyan(line)
    elif level == LogLevel.INFO: line = term.green(line)
    elif level == LogLevel.WARNING: line = term.orange(line)
    elif level == LogLevel.ERROR: line = term.red(line)
    elif level == LogLevel.CRITICAL: line = term.purple(line)

    print(line)


def handler(websocket):
    try:
        while True:
            data = str(messages.get())
            websocket.send(data)
    except:
        pass

def logserver():
    try:
        config = get_config()
        log(LogLevel.DEBUG, f"logging websocket server has started on {config.host}:{config.websocket_port}")
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.set_servername_callback(certs.handle_ssl)
        with serve(handler, host=config.host, port=config.websocket_port, ssl_context=ssl_context) as server:
            server.serve_forever()
    except Exception:
        log(LogLevel.CRITICAL, "exception in websocket logserver():\n" + traceback.format_exc())
