import re
import os
from bs4 import BeautifulSoup as BS
from webwombat.transformers import returntext

TLD_REGEX = "|".join(open(os.path.abspath(os.path.join(os.path.dirname(__file__), "tlds.txt"))).read().split("\n")[1:])
DOMAIN = "fbi.com"
REGEX_URL_MATCH = r"(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6})(\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*))"
REGEX_URL_REPLACE = r"\1."+DOMAIN+r"\2"


def replaceURLs(text):
    if isinstance(text, bytes):
        return re.sub(REGEX_URL_MATCH.encode(), REGEX_URL_REPLACE.encode(), text)
    else:
        return re.sub(REGEX_URL_MATCH, REGEX_URL_REPLACE, text)


def replaceTLDs(text):
    # print(text)
    if isinstance(text, bytes):
        text = re.sub((r"(\.(?:"+TLD_REGEX+r"))([^\.\w])").encode(), REGEX_URL_REPLACE.encode(), text, flags=re.IGNORECASE)
        return text#re.sub(REGEX_URL_MATCH.encode(), REGEX_URL_REPLACE.encode(), text)
    else:
        text = re.sub((r"(\.(?:"+TLD_REGEX+r"))([^\.\w])"), REGEX_URL_REPLACE, text, flags=re.IGNORECASE)
        return text#re.sub(REGEX_URL_MATCH, REGEX_URL_REPLACE, text)


def html_replacement(data):
    soup = BS(data, features="html.parser")

    for tag in soup.findAll(True):
        for k, v in tag.attrs.items():
            if isinstance(v, list):
                v = " ".join(v)
            tag.attrs[k] = replaceURLs(v)
    return str(soup).encode()


def main(message):
    if message.messagetype == "request":
        # message.function = lambda i: i.replace(".fbi.com", "")
        return message

    else:

        for k, v in message.headers.items():
            message.headers[k] = replaceTLDs(v)

        if 'content-type' in message and message['content-type'].startswith('text/html'):
            message.function = html_replacement
        else:
            message.function = replaceURLs

        return message
