import socket
import ssl
import blessed
from .logger import log

TERM = blessed.Terminal()

class SocketBuffer:
    def __init__(self, rfile, wfile, rmethods=['read', 'readline'], wmethods=['write']):
        self.rfile, self.wfile = rfile, wfile
        self.rmethods, self.wmethods = rmethods, wmethods

    def flush(self, *args):
        return self.wfile.flush(*args)

    def __getattr__(self, name):
        if name in self.rmethods:
            def _r_wrapper(*args):
                rvalue = getattr(self.rfile, name)(*args)
                self._show(self.fstring.format(m=self.read_mark), rvalue, self.rcolor)
                return rvalue
            return _r_wrapper
        elif name in self.wmethods:
            def _w_wrapper(*args):
                if not args[0]: return
                self._show(self.fstring.format(m=self.write_mark), args[0], self.wcolor)
                return getattr(self.wfile, name)(*args)
            return _w_wrapper
        else:
            raise Exception(name + ' not supported')

    @classmethod
    def from_address(cls, host: str, port: int, usessl: bool):
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((host, port))
        if usessl:
            context = ssl.create_default_context()
            context.verify_mode = ssl.CERT_REQUIRED
            remote_conn = context.wrap_socket(remote_conn, server_hostname=host)
        resp = cls(
            remote_conn.makefile('rb'),
            remote_conn.makefile('wb', buffering=0),
        )
        resp.close = lambda: remote_conn.close()
        return resp
