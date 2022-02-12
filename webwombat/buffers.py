import socket
import ssl
import blessed

TERM = blessed.Terminal()

class SocketBuffer:
    def __init__(self, rfile, wfile,
                read_mark=' < ', write_mark=' > ',
                fstring='{m}',
                rcolor='blue', wcolor='green',
                rmethods=['read', 'readline'],
                wmethods=['write']
        ):
        self.rfile, self.wfile = rfile, wfile
        self.read_mark, self.write_mark = read_mark, write_mark
        self.fstring = fstring
        self.rcolor, self.wcolor = rcolor, wcolor
        self.rmethods, self.wmethods = rmethods, wmethods

    def _show(self, prefix, content, color, width=70, maxlen=140):
        print(getattr(TERM, color), end='')
        for line in content.split(b"\n"):
            if not line: continue
            line += b"\n"
            line = repr(line)[2:-1]
            for part in [line[i:i+width] for i in range(0, len(line), width)]:
                print(hash(self), prefix, part, sep='')
        print(TERM.normal, end='')

    def flush(self, *args): return self.wfile.flush(*args)

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
    def from_address(cls, host: str, port: int, usessl: bool, **kwargs):
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((host, port))
        if usessl:
            context = ssl.create_default_context()
            context.verify_mode = ssl.CERT_REQUIRED
            remote_conn = context.wrap_socket(remote_conn, server_hostname=host)
        resp = cls(
            remote_conn.makefile('rb'),
            remote_conn.makefile('wb', buffering=0),
            **kwargs
        )
        resp.close = lambda: remote_conn.close()
        return resp

