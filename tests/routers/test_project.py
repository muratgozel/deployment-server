import pytest
import os
from httpx import ASGITransport, AsyncClient, BasicAuth
from sqlalchemy import text, create_engine
from deployment_server.app import app


@pytest.fixture(scope="module", autouse=True)
def configure():
    # setup
    yield
    # teardown
    engine = create_engine(os.environ.get("DATABASE_URL"))
    with engine.connect() as conn:
        conn.execute(text("delete from project where removed_at is not null"))
        conn.commit()


@pytest.mark.asyncio
async def test_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        body_invalid = {"yo":True}
        headers = {"Content-Type":"application/json"}
        response1 = await client.post('/project', json=body_invalid, headers=headers)
        assert response1.status_code == 401

        body_valid = {
            "name": "Some Server",
            "git_url": "git://github.com/some/server.git",
            "pip_package_name": "some-server",
            "pip_index_url": "https://pypi.gozel.com.tr/",
            "pip_index_user": "user",
            "pip_index_auth": "pass"
        }
        auth = BasicAuth(username=os.environ.get('API_USER'), password=os.environ.get('API_SECRET'))
        response2 = await client.post('/project', json=body_valid, headers=headers, auth=auth)
        assert response2.status_code == 200
        response2_dict = response2.json()
        assert "rid" in response2_dict

        response3 = await client.get(f"/project/{response2_dict['rid']}", auth=auth)
        assert response3.status_code == 200
        response3_dict = response3.json()
        assert response3_dict["project"]["rid"] == response2_dict["rid"]

        response_list = await client.get("/project/list", auth=auth)
        assert response_list.status_code == 200
        response_list_dict = response_list.json()
        assert "projects" in response_list_dict
        assert response_list_dict["projects"][0]["rid"] == response2_dict["rid"]

        response_remove = await client.delete(f"/project/{response2_dict['rid']}", auth=auth)
        assert response_remove.status_code == 200
        response_remove_dict = response_remove.json()
        assert response_remove_dict["rid"] == response2_dict["rid"]
