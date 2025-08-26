import os


def get_mode_fallback():
    return "default"


def get_config_dir_fallback():
    return "./"


def get_port_fallback():
    return "8000"


def is_dev():
    mode = os.environ.get("APPLICATION_MODE")
    if mode is None:
        return False
    if "dev" in mode or "local" in mode or "development" in mode or "default" in mode:
        return True
    return False


def is_testing():
    mode = os.environ.get("APPLICATION_MODE")
    if mode is None:
        return False
    return True if "test" in mode else False


def is_staging():
    mode = os.environ.get("APPLICATION_MODE")
    if mode is None:
        return False
    return True if "staging" in mode else False


def is_prod():
    mode = os.environ.get("APPLICATION_MODE")
    if mode is None:
        return False
    return True if "production" in mode or "prod" in mode else False


def get_mode():
    return os.environ.get("APPLICATION_MODE") or get_mode_fallback()


def is_debugging():
    value = os.environ.get("DEBUG")
    if isinstance(value, str) and value == "0":
        return False
    return bool(value)
