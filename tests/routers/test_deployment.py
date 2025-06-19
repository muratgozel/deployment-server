import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, BasicAuth
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True, scope="module", loop_scope="session")
async def setup_deployment(get_app):
    app = get_app
    session_factory = await app.container.session_factory()

    async with session_factory() as session:
        await session.execute(
            text(
                "insert into project (rid, name, code, git_url) values (:rid, :name, :code, :git_url)"
            ),
            {
                "rid": "rid1",
                "name": "p1",
                "code": "p1",
                "git_url": "git://github.com/some/server.git",
            },
        )
        await session.commit()

    yield

    async with session_factory() as session:
        await session.execute(
            text("delete from deployment where removed_at is not null")
        )
        await session.execute(
            text("delete from project where rid=:rid"), {"rid": "rid1"}
        )
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_deployment(get_app):
    app = get_app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        body_invalid = {"yo": True}
        headers = {"Content-Type": "application/json"}
        response1 = await client.post("/deployment", json=body_invalid, headers=headers)
        assert response1.status_code == 401

        body_valid = {
            "git_url": "git://github.com/some/server.git",
            "version": "0.1.0",
        }
        auth = BasicAuth(
            username=app.container.config.api_user(),
            password=app.container.config.api_secret(),
        )
        response2 = await client.post(
            "/deployment", json=body_valid, headers=headers, auth=auth
        )
        assert response2.status_code == 200
        response2_dict = response2.json()
        assert "rid" in response2_dict
