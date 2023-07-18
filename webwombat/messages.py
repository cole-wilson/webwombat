import io
from . import filters
from . import BrokenWombat
import brotli
import gzip
import zlib
import sys
from threading import Thread
from .buffers import SocketBuffer

CRLF = b"\r\n"

def read_chunk(r):
    lengthline = r.readline().strip(CRLF)
    if not lengthline: return None
    length = int(lengthline, 16)
    if length == 0:
        r.read(2)
        return None
    chunk = r.read(length)
    r.read(2)
    return chunk

def stream_chunks(r, w, function):
    while True:
        chunk = function(read_chunk(r))
        if chunk:
            length = hex(len(chunk))[2:].encode('utf-8')
            w.write(length + CRLF + chunk + CRLF)
        else:
            w.write(b"0" + CRLF + CRLF)
            break

class CaseInsensitiveDict(dict):
    def __init__(self, initial_values = {}, **_):
        for k, v in initial_values.items():
            self[k.lower()] = v
    def __getitem__(self, k): return super().__getitem__(k.lower())
    def __delitem__(self, k): return super().__delitem__(k.lower())
    def __setitem__(self, k, v): return super().__setitem__(k.lower(), v)
    def __contains__(self,o):return super().__contains__(o.lower())

class Message:
    messagetype = None
    sourcefile = io.BytesIO(b"")
    skiprest = False

    port = None

    method = None
    locator = None
    version = None
    status = None
    reason = None
    headers: dict[str, str] = CaseInsensitiveDict({})


    def __init__(self, file: SocketBuffer, messagetype: str):
        self.function = lambda i: i
        self.messagetype = messagetype
        self.sourcefile = file

    def read_statusline(self):
        statusline = self.sourcefile.readline().strip(CRLF).decode().split()
        if self.messagetype == "request":
            self.method, self.locator, self.version = statusline
            if self.method == "CONNECT":
                self.port = int(self.locator.split(':')[-1])
        elif self.messagetype == "response":
            self.version, self.status, *reason = statusline
            self.reason = " ".join(reason)

    def read_headers(self):
        self.headers = CaseInsensitiveDict({})
        while True:
            headerline = self.sourcefile.readline().strip(CRLF)
            if not headerline: break
            k, v = headerline.split(b": ", 1)
            self.headers[k.decode()] = v.decode()
        if 'host' in self.headers:
            self['host'] = self['host'].split(":")[0]

    def send_to(self, destination) -> Thread:
        if self.method == "TUNNEL":
            self.sourcefile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            if isinstance(self.sourcefile, SocketBuffer):
                self.sourcefile.disablelogging()
            destination.disablelogging()
            def _sendbody():
                while True:
                    data = self.sourcefile.read(1)
                    # print(data, end="")
                    if data == b'': break
                    sys.stdout.flush()
                    try:
                        destination.write(data)
                    except BrokenPipeError:
                        break
                if isinstance(self.sourcefile, SocketBuffer):
                    self.sourcefile.enablelogging()
                destination.enablelogging()
            return Thread(target=_sendbody)

        elif self.body_type == "empty":
            return Thread(target=destination.write, args=[self.encode()])

        elif self.body_type == "normal":
            def _sendbody():
                content_length = int(self['content-length'])
                body = self.sourcefile.read(content_length)

                decoders, encoders = self.get_dencoders()
                for decoder in decoders:
                    body = decoder(body)
                body = self.function(body)
                for encoder in encoders:
                    body = encoder(body)

                self['content-length'] = len(body)
                destination.write(self.encode())
                destination.write(body)
            return Thread(target=_sendbody)

        elif self.body_type == "chunked":
            destination.write(self.encode())
            if self.messagetype == "request":
                early_response = Message(destination, "response")
                early_response.read_statusline()
                early_response.read_headers()
                self.sourcefile.write(early_response.encode())
            return Thread(target=stream_chunks, args=[self.sourcefile, destination, self.function])

        elif self.body_type == "encoded_chunks":
            destination.write(self.encode())
            if self.messagetype == "request":
                early_response = Message(destination, "response")
                early_response.read_statusline()
                early_response.read_headers()
                self.sourcefile.write(early_response.encode())

            decoders, encoders = self.get_dencoders()
            body = b""
            while True:
                chunk = read_chunk(self.sourcefile)
                if chunk is None:
                    break
                body += chunk
            for decoder in decoders:
                body = decoder(body)
            body = self.function(body)
            for encoder in encoders:
                body = encoder(body)
            def _sendchunk():
                length = hex(len(body))[2:].encode()
                destination.write(length + CRLF + body + CRLF)
                destination.write(b"0" + CRLF + CRLF)
            return Thread(target=_sendchunk)
        return Thread(target=lambda: None)

    @property
    def statusline(self) -> bytes:
        if self.messagetype == "request":
            return " ".join([self.method, self.locator, self.version]).encode()
        elif self.messagetype == "response":
            return " ".join([self.version, self.status, self.reason]).encode()
        else:
            return b""

    @property
    def body_type(self) -> str:
        if 'content-length' in self.headers:
            return 'normal'
        elif 'transfer-encoding' in self.headers and self.headers['transfer-encoding'].startswith('chunked'):
            if 'content-encoding' in self.headers:
                return 'encoded_chunks'
            else:
                return 'chunked'
        else:
            return 'empty'

    def get_dencoders(self) -> tuple[list, list]:
        if 'content-encoding' not in self.headers:
            return [], []
        else:
            decoders = []
            encoders = []
            for encoding in self.headers['content-encoding'].replace(" ","").split(','):
                try:
                    decoder, encoder = {
                        "br": (brotli.decompress,brotli.compress),
                        "deflate": (zlib.decompress,zlib.compress),
                        "gzip": (gzip.decompress,gzip.compress),
                    }[encoding]
                    decoders.insert(0, decoder)
                    encoders.append(encoder)
                except KeyError:
                    raise BrokenWombat(f"the `{encoding}` encoding is not supported")
            return decoders, encoders

    def __getitem__(self, name):
        return self.headers[name]
    def __contains__(self, name):
        return name in self.headers
    def __setitem__(self, name, value):
        self.headers[name] = value
    def __delitem__(self, name):
        del self.headers[name]

    def __repr__(self):
        return f"<{type(self).__name__} {self.headers['host'] if 'host' in self.headers else ''} {self.statusline.decode()[:45]}>"

    def __bytes__(self, *_):
        output = b""
        output += self.statusline + CRLF
        for k, v in self.headers.items():
            output += str(k).title().encode('utf-8') + b": " + str(v).encode('utf-8') + CRLF
        output += CRLF
        return output
        # return self.function(output)

    encode = __bytes__
