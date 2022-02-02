import filters
import exceptions
import brotli
import gzip
import zlib
from constants import PORT
from threading import Thread
from buffers import SocketBuffer
from requests.structures import CaseInsensitiveDict

CRLF = b"\r\n"

def read_chunk(r, func):
    lengthline = r.readline().strip(CRLF)
    if not lengthline: return None
    length = int(lengthline, 16)
    if length == 0:
        r.read(2)
        return None
    chunk = func(r.read(length))
    r.read(2)
    return chunk

def stream_chunks(r, w, func):
    while True:
        chunk = read_chunk(r, func)
        if chunk:
            length = hex(len(chunk))[2:].encode('utf-8')
            w.write(length + CRLF + chunk + CRLF)
        else:
            w.write(b"0" + CRLF + CRLF)
            break

class Message:
    def __init__(self, file: SocketBuffer, function):
        self.function = function
        self.source = file
        self.statusline = self.function(self.source.readline().strip(CRLF))
        self.headers = CaseInsensitiveDict({})
        while True:
            headerline = self.function(self.source.readline().strip(CRLF))
            if not headerline: break
            k, v = headerline.split(b": ", 1)
            self.headers[str(k, 'utf-8')] = str(v, 'utf-8')

    def transfer_body(self, destination) -> Thread:
        func = self.function
        if self.body_type == 'empty':
            return Thread(target=destination.write, args=[bytes(self)])
        elif self.body_type == 'normal':
            if not self.headers['content-length'].isnumeric():
                raise exceptions.BrokenWombat("the Content-Length of the request was non-numeric! what are you trying to do here?")
            request_body = self.source.read(int(self.headers['content-length']))
            decoders, encoders = self.get_dencoders()
            for decoder in decoders:
                request_body = decoder(request_body)
            request_body = func(request_body)
            for encoder in encoders:
                request_body = encoder(request_body)
            self.headers['content-length'] = len(request_body)
            def _send_body():
                destination.write(bytes(self))
                destination.write(request_body)
            return Thread(target=_send_body)
        elif 'chunk' in self.body_type:
            destination.write(bytes(self))
            if self.is_request():
                early_response = Message(destination, filters.wombatize)
                if early_response.code != 100:
                    raise exceptions.BrokenWombat(f"the remote server returned {early_response.code} instead of 100.")
                self.source.write(bytes(early_response))

            if self.body_type == 'chunked':
                return Thread(target=stream_chunks, args=[self.source, destination, self.function])
            else:
                def _waitsendchunks():
                    body = b""
                    while True:
                        chunk = read_chunk(self.source, lambda i: i) # we mustn't mess up encoded data
                        if chunk is None: break
                        body += chunk
                    decoders, encoders = self.get_dencoders()
                    for decoder in decoders:
                        body = decoder(body)
                    body = self.function(body)
                    for encoder in encoders:
                        body = encoder(body)
                    hexlen = hex(len(body))[2:].encode('utf-8')
                    destination.write(hexlen + CRLF + body + CRLF)
                    destination.write(b"0" + CRLF + CRLF)
                return Thread(target=_waitsendchunks)
        else:
            return Thread(target=lambda i: i)


    def is_response(self) -> bool: return self.statusline.startswith(b"HTTP")

    def is_request(self) -> bool: return not self.is_response()

    @property
    def port(self) -> int:
        assert self.is_request(), "tried to get port on a response"
        h: str = self.headers['host']
        if ':' in h:
            p = h.split(':')[1]
            if not p.isnumeric():
                raise exceptions.BrokenWombat("the host port is non-numeric")
            else:
                return int(p)
        else:
            return PORT

    @property
    def host(self) -> str:
        assert self.is_request(), "tried to get host on a response"
        if 'host' not in self.headers:
            raise exceptions.BrokenWombat("the Host header is required for all HTTP verbs other than CONNECT")
        return self.headers['host'].split(':')[0]

    @property
    def verb(self) -> str:
        assert self.is_request(), "tried to get verb on a response"
        return str(self.statusline.split(b" ")[0], 'utf-8')

    @property
    def locator(self) -> str:
        assert self.is_request(), "tried to get locator on a response"
        return str(self.statusline.split(b" ")[1], 'utf-8')

    @property
    def version(self) -> str:
        if self.is_request():
            return str(self.statusline.split(b" ")[2], 'utf-8')
        else:
            return str(self.statusline.split(b" ")[0], 'utf-8')

    @property
    def code(self) -> int:
        assert self.is_response(), "tried to get response code on a request"
        return int(self.statusline.split(b" ")[1])

    @property
    def reason(self) -> str:
        assert self.is_response(), "tried to get response reason on a request"
        return str(self.statusline.split(b" ")[2], 'utf-8')

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
                    raise exceptions.BrokenWombat(f"the `{encoding}` encoding is not supported")
            return decoders, encoders

    def __repr__(self):
       return f"<{type(self).__name__} {str(self.statusline, 'utf-8')}>"

    def __bytes__(self, *args):
        output = b""
        output += self.statusline + CRLF
        for k, v in self.headers.items():
            output += str(k).title().encode('utf-8') + b": " + str(v).encode('utf-8') + CRLF
        output += CRLF
        return output

    encode = __bytes__
