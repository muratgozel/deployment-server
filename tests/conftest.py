import os
import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def configure():
    # setup

    if os.path.isfile(".env.test"):
        load_dotenv(".env.test")
    elif os.path.isfile(".env"):
        load_dotenv(".env")
    else:
        pass

    yield

    # teardown

    pass
