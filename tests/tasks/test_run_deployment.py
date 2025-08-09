from time import sleep

import pytest
import pytest_asyncio
from sqlalchemy import text

from deployment_server.repositories.deployment import LatestStatusType


@pytest_asyncio.fixture(autouse=True, scope="module", loop_scope="session")
async def setup_run_deployment(get_app):
    app = get_app
    session_factory = await app.container.session_factory()
    async with session_factory() as session:
        await session.execute(
            text(
                "insert into project (rid, name, code, secrets_provider) values ('randone', 'one', 'one', 'LOCAL'), ('randtwo', 'two', 'two', 'LOCAL'), ('randthree', 'three', 'three', 'LOCAL');"
            )
        )
        await session.execute(
            text(
                "insert into deployment (rid, project_rid, version, mode) values ('randone', 'randone', '0.1.2', 'LOCAL');"
            )
        )
        await session.execute(
            text(
                "insert into deployment_status_update (rid, deployment_rid, status) values ('randone', 'randone', 'READY');"
            )
        )
        await session.commit()
        sleep(1)
        await session.execute(
            text(
                "insert into deployment (rid, project_rid, version, mode) values ('randtwo', 'randone', '0.1.3', 'LOCAL'), ('randthree', 'randtwo', '1.0.0', 'LOCAL');"
            )
        )
        await session.execute(
            text(
                "insert into deployment_status_update (rid, deployment_rid, status) values ('randtwo', 'randtwo', 'READY'), ('randthree', 'randthree', 'FAILED');"
            )
        )
        await session.commit()

    yield

    async with session_factory() as session:
        await session.execute(
            text(
                "delete from project where rid = 'randone' or rid = 'randtwo' or rid = 'randthree';"
            )
        )
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_run_deployment():
    from deployment_server.containers.worker import WorkerContainer

    container = WorkerContainer()
    container.init_resources()
    rec = container.deployment_service().pick_deployment_sync()
    assert isinstance(rec, LatestStatusType)
    assert rec.version == "0.1.3"
