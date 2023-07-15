from .config import get_config
from queue import Queue
import ssl
import json
from . import certs
from blessed import Terminal
from datetime import datetime
from time import time
from enum import IntEnum

messages = Queue()

class LogLevel(IntEnum):
    CONFIG = 0
    SSL = 10
    SOCKET = 20
    DEBUG = 30
    INFO = 40
    WARNING = 50
    ERROR = 60
    CRITICAL = 70

loglevel = LogLevel.CONFIG
term = Terminal()

def log(level, data, http_message=None):
    now = datetime.now()

    line = f"[{now}] {level.name} {str(hash(http_message)) + ': ' if http_message is not None else ''}" + str(data)

    if   level <= LogLevel.SOCKET: line = term.grey(line)
    elif level == LogLevel.DEBUG: ...
    elif level == LogLevel.INFO: line = term.green(line)
    elif level == LogLevel.WARNING: line = term.orange(line)
    elif level == LogLevel.ERROR: line = term.red(line)
    elif level == LogLevel.CRITICAL: line = term.magenta(line)

    if level.value < loglevel.value: return

    print(line)


def handler(websocket):
    try:
        while True:
            data = str(messages.get())
            websocket.send(data)
    except:
        pass
