import re
from sys import flags
from constants import PROXY_SUFFIX

def wombatize(message: bytes):
    message = re.sub(
        rb"\.(com|org|ws|net)([^\w=()]|$)",
        rb".\1.proxy\2",
        message,
        flags=re.MULTILINE|re.IGNORECASE
    )
    message = message.replace(b"integrity=", b"")
    return message

def normalize(message: bytes):
    return re.sub(re.escape(PROXY_SUFFIX.encode('utf-8')), b"", message)
