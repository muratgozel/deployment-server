import os
import pytest
from deployment_server.constants import CODENAME, SERVER_PORT_FALLBACK


@pytest.fixture(scope="session", autouse=True)
def configure():
    # setup

    ci = True if bool(os.environ.get("CI")) else False

    os.environ["APPLICATION_MODE"] = "testing"
    if os.environ.get("APPLICATION_CONFIG_DIR") is None:
        os.environ["APPLICATION_CONFIG_DIR"] = "./" if ci else os.path.expanduser(f"~/{CODENAME}")
    if os.environ.get("APPLICATION_SERVER_PORT") is None:
        os.environ["APPLICATION_SERVER_PORT"] = SERVER_PORT_FALLBACK

    yield

    # teardown

    pass
