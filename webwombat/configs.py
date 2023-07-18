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
# from .logger import log, LogLevel
from . import logger, DottedDict
import webwombat

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

    logger.log(logger.LogLevel.CONFIG, f"star_replace({pattern!r}, {replace!r}, {text!r}) -> {output}")

    return output

class ExternalObject:
    def __init__(self, modulestr=None, attrstr=None, *args):
        if modulestr == None:
            modulestr = "webwombat.transformers"
        self.modulestr = modulestr
        self.attrstr = attrstr
        self.args = args

    def get(self):
        module = importlib.import_module(self.modulestr)
        return operator.attrgetter(self.attrstr)(module)

class ComiledSubstitution:
    args = []
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
    def get(self):
        return self.sub

class Transformer(lark.Transformer):
    # rules
    def start(self, items): return items
    def main(self, items): return items
    def keyvalue_group(self, items): return DottedDict(items)
    def headers(self, items): return dict(items)
    def funcref(self, items):
        return ExternalObject(*items)
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
        head, headers, *stuffs = items
        if head is None: head = DottedDict(defaultdict(None))

        subs, funcs = [], []

        for thing in stuffs:
            if isinstance(thing, ExternalObject):
                funcs.append(thing)
            else:
                subs.append(thing)

        head['headers'] = headers
        head['funcs'] = funcs
        head['subs'] = subs
        return head

    # TERMINALS
    def ENV(self, text): return os.environ.get(text[1:], "")
    def BOOL(self, text): return text.lower() not in ['false', 'no', 'nah']
    def NUMBER(self, text): return int(text)
    def STATUS(self, text): return "status", str(text).replace('x', '?')
    def TYPE(self, text): return "type", str(text)
    def SUB_REGEX(self, text):
        _, pattern, sub, flags = re.split(r"(?<!\\)/", text)
        ordflags = re.MULTILINE
        bodyonly = True
        for flag in flags:
            if hasattr(re, flag.upper()):
                ordflags |= getattr(re, flag.upper())
        compiled = re.compile(pattern.encode(), flags=ordflags)
        return ComiledSubstitution(compiled, sub.encode()).sub

    DOMAIN = lambda _, i: ("domain", str(i))
    PATH = lambda _, i: ("path", str(i))
    METHOD = lambda _, i: ("method", str(i))
    NAME = HEADER_KEY = HEADER_VALUE = lambda _, i: str(i).strip()
    STRING = lambda _, i: str(i)[1:-1]
    arg = lambda _, i: i[0]
    keyvalue = list = lambda _, i: i


def load(path, defaults = {}, overrides={}):
    grammar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/g.lark"
    grammar = open(grammar_path).read()

    parser = lark.Lark(grammar)
    with open(Path(path).expanduser(), 'r') as configuration_file:
        tree = parser.parse(configuration_file.read())
    webwombat.global_config = Transformer().transform(tree)

    for k, v in defaults.items():
        if k not in webwombat.global_config[0]:
            webwombat.global_config[0][k] = v


    for k, v in overrides.items():
        webwombat.global_config[0][k] = v

    logger.log(logger.LogLevel.CONFIG, f"loaded configuration grammar from {grammar_path}")
    logger.log(logger.LogLevel.CONFIG, f"read config tree: {tree}")
    logger.log(logger.LogLevel.CONFIG, f"config: {webwombat.global_config[0]}")
    logger.log(logger.LogLevel.CONFIG, f"rules: {webwombat.global_config[1]}")

# def get_config():
#     assert global_config is not None
#     return global_config[0]
def get_rules():
    logger.log(logger.LogLevel.CONFIG, "got rules")
    assert webwombat.global_config is not None
    return webwombat.global_config[1]

if __name__ == "__main__":
    load(sys.argv[1])
    print(webwombat.global_config)
    # print()
    print(get_rules())
