import socket
import ssl
import blessed
from .logger import log, LogLevel

TERM = blessed.Terminal()

class SocketBuffer:
    logging = True
    def __init__(self, rfile, wfile, rawsock=None, rmethods=['read', 'readline'], wmethods=['write'], requestid=None, socketid=None):
        log(LogLevel.SOCKET, f"created new {socketid} SocketBuffer for message {requestid} with methods {rmethods} and {wmethods}", requestid=requestid, socketid=socketid)
        self.rfile, self.wfile = rfile, wfile
        self.requestid = requestid
        self.socketid = socketid
        self.rawsock = rawsock
        self.rmethods, self.wmethods = rmethods, wmethods

    def disablelogging(self):
        self.logging = False
        log(LogLevel.SOCKET, f"disabling socket logging for {self.socketid} {self.requestid}", requestid=self.requestid, socketid=self.socketid)
    def enablelogging(self):
        self.logging = True
        log(LogLevel.SOCKET, f"re-enabling socket logging for {self.socketid} {self.requestid}", requestid=self.requestid, socketid=self.socketid)

    def flush(self, *args):
        return self.wfile.flush(*args)

    def __getattr__(self, name):
        if name in self.rmethods:
            def _r_wrapper(*args):
                rvalue = getattr(self.rfile, name)(*args)
                if self.logging:
                    log(LogLevel.SOCKET, rvalue, requestid=self.requestid, socketid=self.socketid, optype="r")
                return rvalue
            return _r_wrapper
        elif name in self.wmethods:
            def _w_wrapper(*args):
                if not args[0]: return
                if self.logging:
                    log(LogLevel.SOCKET, args[0], requestid=self.requestid, socketid=self.socketid, optype="w")
                return getattr(self.wfile, name)(*args)
            return _w_wrapper
        else:
            raise Exception(name + ' not supported by SocketBuffer')

    @classmethod
    def from_address(cls, host: str, port: int, usessl: bool, requestid=None, socketid=None):
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((host, port))
        if usessl:
            context = ssl.create_default_context()
            context.verify_mode = ssl.CERT_REQUIRED
            s_remote_conn = context.wrap_socket(remote_conn, server_hostname=host)
        else:
            s_remote_conn = remote_conn
        resp = cls(
            s_remote_conn.makefile('rb'),
            s_remote_conn.makefile('wb', buffering=0),
            remote_conn,
            requestid=requestid,
            socketid=socketid
        )
        resp.close = lambda: remote_conn.close()
        return resp
