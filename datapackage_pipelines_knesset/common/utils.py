import importlib


def parse_import_func_parameter(value, *args):
    if value and isinstance(value, str) and value.startswith("(") and value.endswith(")"):
        cmdparts = value[1:-1].split(":")
        cmdmodule = cmdparts[0]
        cmdfunc = cmdparts[1]
        cmdargs = cmdparts[2] if len(cmdparts) > 2 else None
        func = importlib.import_module(cmdmodule)
        for part in cmdfunc.split("."):
            func = getattr(func, part)
        if cmdargs == "args":
            value = func(*args)
        else:
            value = func()
    return value
