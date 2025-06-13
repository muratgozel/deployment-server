import json
from typing import Annotated
from fastapi import APIRouter, HTTPException, Response, Request, Header, BackgroundTasks
from fastapi.responses import PlainTextResponse
from deployment_server.core import github, git
from deployment_server.worker import create_deployment_task


router = APIRouter(prefix="/on/release", tags=["on", "release"])


@router.post(
    "/", response_class=PlainTextResponse, status_code=202, operation_id="on_release"
)
async def on_release(
    request: Request,
    response: Response,
    x_github_event: Annotated[str | None, Header()],
    x_hub_signature_256: Annotated[str | None, Header()],
):
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Vary"] = "Origin,Accept-Language"

    # we only support github releases
    if not x_github_event or not x_hub_signature_256:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_headers"}}
        )

    try:
        body_bytes = await request.body()
    except:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_request_body"}}
        )

    # verify request coming from github
    request_verified = github.verify_signature(body_bytes, x_hub_signature_256)
    if request_verified is False:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_signature"}}
        )

    body = json.loads(body_bytes)
    if body["ref_type"] != "tag":
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_ref_type"}}
        )

    try:
        vendor, owner, name = git.parse_repo_url(body["repository"]["git_url"])
    except:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "invalid_repo_url"}}
        )

    try:
        version = git.extract_version_from_ref(body["ref"])
    except:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_ref"}})

    create_deployment_task.delay(version, (vendor, owner, name))

    return "Accepted"
