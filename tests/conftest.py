import os
import pytest
from sqlalchemy import text, create_engine
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

    engine = create_engine(os.environ.get("DATABASE_URL"))
    with engine.connect() as conn:
        conn.execute(text("delete from project where removed_at is not null"))
        conn.commit()
