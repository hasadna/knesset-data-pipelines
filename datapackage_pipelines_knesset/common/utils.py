import importlib, logging, os
from contextlib import contextmanager
from tempfile import mkdtemp


@contextmanager
def temp_loglevel(level=logging.INFO):
    root_logging_handler = logging.root.handlers[0]
    old_level = root_logging_handler.level
    root_logging_handler.setLevel(level)
    yield
    root_logging_handler.setLevel(old_level)


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


@contextmanager
def temp_dir(*args, **kwargs):
    dir = mkdtemp(*args, **kwargs)
    try:
        yield dir
    except Exception:
        if os.path.exists(dir):
            os.rmdir(dir)
        raise

@contextmanager
def temp_file(*args, **kwargs):
    with temp_dir(*args, **kwargs) as dir:
        file = os.path.join(dir, "temp")
        try:
            yield file
        except Exception:
            if os.path.exists(file):
                os.unlink(file)
            raise
