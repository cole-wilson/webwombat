import re
import fnmatch
from .config import get_rules, star_replace, ExternalObject
# from constants import PROXY_SUFFIX

class NoMatch(Exception): pass

def ismatch(patterns, string):
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns:
        if fnmatch.fnmatch(string, pattern):
            return pattern
    raise NoMatch

def filter(message):
    # type, method, status, domain, locator, headers
    rules = get_rules()
    for rule in rules:
        try:
            match = rule['match']
            print(match)
            action= rule['action']

            ismatch(match.type, message.messagetype)
            if message.messagetype == "request":
                domain = ismatch(match.domain, message['host'])
                method = ismatch(match.method, message.method)
                locator = ismatch(match.path, message.locator)
            elif message.messagetype == "response":
                status = ismatch(match.status, message.status)
            headers = {}
            for key, values in match.headers.items():
                key = key.lower()
                matched_key = ismatch(message.headers.keys(), key)
                matched_val = ismatch(values, message.headers[key])
                headers[matched_key] = matched_val
            if isinstance(action, ExternalObject):
                message = action.get()(message)
            else:
                if message.messagetype == "request":
                    if 'method' in action: message.method = star_replace(method, action.method, message.method)
                    if 'domain' in action: message['host'] = star_replace(domain, action.domain, message['host'])
                    if 'path' in action:   message.locator = star_replace(locator, action.path, message.locator)
                elif message.messagetype == "response":
                    if 'status' in action: message.status = star_replace(status, action.status, message.status)
                for k, v in action.headers.items():
                    k = k.lower()
                    if k in headers:
                        message[k] = star_replace(headers[k], v, message[k])
                    elif v == ['']:
                        del message[k]
                    else:
                        message[k] = v
                def get_func(substitutions):
                    def sub(content):
                        for substitution in substitutions:
                            content = substitution.sub(content)
                        return content
                    return sub
                message.function = get_func(action.substitutions)
            # print(message, match, action)
        except NoMatch:
            pass
    return message

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
    return re.sub(re.escape(".proxy".encode('utf-8')), b"", message)
