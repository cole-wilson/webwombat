from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import operator
import importlib
import lark
import fnmatch
import json
import re
import sys
import os

grammar = open('./g.lark').read()

def star_replace(pattern, replace, text):
    # ?.*.com    *.?.proxy    a.google.com
    # print(pattern , replace, text)
    keys = re.findall(r"\?|\*", pattern)
    pattern = re.escape(pattern).replace(r"\*", "(.*)").replace(r"\?", "(.)")
    matches = re.findall(pattern, text)[0]
    if isinstance(matches, str): matches = (matches,)
    groups = defaultdict(list)
    for k, v in zip(keys, matches):
        groups[k].append(v)
    # print(groups)
    output = ""
    for char in replace:
        if char in ("*", "?"):
            try:
                output += groups[char].pop(0)
            except IndexError:
                pass
        else:
            output += char
    return output

class DottedDict(dict):
    __getattr__ = lambda self, *args: self.__getitem__(*args)
    __setattr__ = lambda self, *args: self.__setitem__(*args)
    __delattr__ = lambda self, *args: self.__delitem__(*args)

class ExternalObject:
    def __init__(self, modulestr, attrstr):
        self.modulestr = modulestr
        self.attrstr = attrstr

    def get(self):
        module = importlib.import_module(self.modulestr)
        return operator.attrgetter(self.attrstr)(module)

class ComiledSubstitution:
    def __init__(self, compiled, replacewith):
        self.compiled = compiled
        self.replacewith = replacewith
    def __repr__(self):
        return f"<CompiledSubstitution {repr(self.compiled)}, {self.replacewith}>"
    def sub(self, text, **variables):
        if text is None:
            return b""
        r = self.replacewith.decode().format(**variables).encode()
        return self.compiled.sub(r, text)

class Transformer(lark.Transformer):
    # rules
    def start(self, items): return items
    def main(self, items): return items
    def keyvalue_group(self, items): return DottedDict(items)
    def headers(self, items): return dict(items)
    def funcref(self, items): return ExternalObject(*items)
    def dotted(self, parts): return ".".join(parts)

    def header(self, items):
        key, *values = items
        return key, values
    def group(self, items):
        match, _, action = items
        return {"match": match, "action": action}
    def matchhead(self, items):
        out = defaultdict(list)
        for k, v in items: out[k].append(v)
        if 'method' not in out: out['method'] = ["*"]
        if 'status' not in out: out['status'] = ["*"]
        if 'path' not in out: out['path'] = ["*"]
        return DottedDict(out)
    def actionhead(self, items):
        return DottedDict(filter(lambda i: i is not None, items))
    def matchgroup(self, items):
        match, headers = items
        match['headers'] = headers
        return match
    def actiongroup(self, items):
        if isinstance(items[0], ExternalObject):
            return items[0]
        head, headers, *subs = items
        if head is None: head = defaultdict(None)
        head['headers'] = headers
        head['headers'] = headers
        head['substitutions'] = subs
        return head

    # TERMINALS
    def ENV(self, text): return os.environ.get(text[1:], "")
    def BOOL(self, text): return text.lower() in ['false', 'no', 'nah']
    def NUMBER(self, text): return int(text)
    def STATUS(self, text): return "status", str(text).replace('x', '?')
    def TYPE(self, text): return "type", str(text)
    def SUB_REGEX(self, text):
        _, pattern, sub, flags = re.split(r"(?<!\\)/", text)
        ordflags = re.MULTILINE
        for flag in flags:
            if hasattr(re, flag.upper()):
                ordflags |= getattr(re, flag.upper())
        compiled = re.compile(pattern.encode(), flags=ordflags)
        return ComiledSubstitution(compiled, sub.encode())

    DOMAIN = lambda _, i: ("domain", str(i))
    PATH = lambda _, i: ("path", str(i))
    METHOD = lambda _, i: ("method", str(i))
    NAME = HEADER_KEY = HEADER_VALUE = lambda _, i: str(i).strip()
    STRING = lambda _, i: str(i)[1:-1]
    arg = lambda _, i: i[0]
    keyvalue = list = lambda _, i: i

global_config = None

def load(path, defaults = {}):
    global global_config

    parser = lark.Lark(grammar)
    with open(Path(path).expanduser(), 'r') as configuration_file:
        tree = parser.parse(configuration_file.read())
    global_config = Transformer().transform(tree)

    for k, v in defaults.items():
        if k not in global_config[0]:
            global_config[0][k] = v

def get_config():
    assert global_config is not None
    return global_config[0]
def get_rules():
    assert global_config is not None
    return global_config[1]

if __name__ == "__main__":
    load(sys.argv[1])
    print(get_config())
    print()
    print(get_rules())
