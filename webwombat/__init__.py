__version__ = "0.0.0"

WOMBAT = r""" ^=---=^-="'````'"=_
/       \           ""\
| .  .  |              \
 \_Q___/        /      /
  \ \/   _==_   \     /
  |_/cwi;"   \___\___;
"""

global_config = [None, None]

def get_config():
    return global_config[0]
def get_rules():
    return global_config[1]


class BrokenWombat(Exception):
    pass
class DottedDict(dict):
    __getattr__ = lambda self, *args: self.__getitem__(*args)
    __setattr__ = lambda self, *args: self.__setitem__(*args)
    __delattr__ = lambda self, *args: self.__delitem__(*args)
