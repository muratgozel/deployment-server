import os
import pytest
from deployment_server.server import create_app
from deployment_server.modules import env


@pytest.fixture(scope="session")
def get_app():
    return create_app()


@pytest.fixture(scope="session", autouse=True)
def configure():
    # setup

    os.environ["APPLICATION_MODE"] = (
        os.environ.get("APPLICATION_MODE") or env.get_mode_fallback()
    )
    os.environ["APPLICATION_CONFIG_DIR"] = os.path.expanduser(
        os.environ.get("APPLICATION_CONFIG_DIR") or env.get_config_dir_fallback()
    )
    os.environ["APPLICATION_SERVER_PORT"] = (
        os.environ.get("APPLICATION_SERVER_PORT") or env.get_port_fallback()
    )

    yield

    # teardown

    pass
