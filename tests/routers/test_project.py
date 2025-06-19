import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, BasicAuth
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True, scope="module", loop_scope="session")
async def setup_project(get_app):
    app = get_app
    session_factory = await app.container.session_factory()

    yield

    async with session_factory() as session:
        await session.execute(text("delete from project where removed_at is not null"))
        await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_project(get_app):
    app = get_app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        body_invalid = {"yo": True}
        headers = {"Content-Type": "application/json"}
        response1 = await client.post("/project", json=body_invalid, headers=headers)
        assert response1.status_code == 401

        body_valid = {
            "name": "Some Server",
            "git_url": "git://github.com/some/server.git",
            "pip_package_name": "some-server",
            "pip_index_url": "https://pypi.gozel.com.tr/",
            "pip_index_user": "user",
            "pip_index_auth": "pass",
        }
        auth = BasicAuth(
            username=app.container.config.api_user(),
            password=app.container.config.api_secret(),
        )
        response2 = await client.post(
            "/project", json=body_valid, headers=headers, auth=auth
        )
        assert response2.status_code == 200
        response2_dict = response2.json()
        assert "rid" in response2_dict

        response3 = await client.get(f"/project/{response2_dict['rid']}", auth=auth)
        assert response3.status_code == 200
        response3_dict = response3.json()
        assert response3_dict["rid"] == response2_dict["rid"]

        response_list = await client.get("/project/list", auth=auth)
        assert response_list.status_code == 200
        response_list_dict = response_list.json()
        assert isinstance(response_list_dict, list)
        filtered = [x for x in response_list_dict if x["rid"] == response2_dict["rid"]]
        assert len(filtered) == 1

        response_remove = await client.delete(
            f"/project/{response2_dict['rid']}", auth=auth
        )
        assert response_remove.status_code == 204
