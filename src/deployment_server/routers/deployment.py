import secrets
from typing import Annotated
from dependency_injector import providers
from dependency_injector.wiring import inject, Provide
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, AfterValidator, Field
from deployment_server.packages.utils import converters, validators
from deployment_server.containers.server import ServerContainer
from deployment_server.services.project import ProjectService
from deployment_server.services.deployment import DeploymentService
from deployment_server.models import Deployment


security = HTTPBasic()
AuthCredentials = Annotated[HTTPBasicCredentials, Depends(security)]
AuthConfig = Annotated[
    providers.Configuration, Depends(Provide[ServerContainer.config])
]


@inject
async def authenticate(credentials: AuthCredentials, config: AuthConfig):
    is_correct_user = secrets.compare_digest(
        credentials.username.encode(), config["api_user"].encode()
    )
    is_correct_secret = secrets.compare_digest(
        credentials.password.encode(), config["api_secret"].encode()
    )
    if not (is_correct_user and is_correct_secret):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "Unauthorized"}},
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


router = APIRouter(
    prefix="/deployment", tags=["deployment"], dependencies=[Depends(authenticate)]
)


ProjectServiceType = Annotated[
    ProjectService, Depends(Provide[ServerContainer.project_service])
]
DeploymentServiceType = Annotated[
    DeploymentService, Depends(Provide[ServerContainer.deployment_service])
]
DeploymentModel = converters.sqlalchemy_to_pydantic(Deployment, "Deployment")


class DeploymentCreateRequest(BaseModel):
    git_url: Annotated[str, AfterValidator(validators.url_pydantic)]
    version: Annotated[str, Field(max_length=64, min_length=1)]
    mode: Annotated[str, AfterValidator(validators.deployment_mode_pydantic)] = (
        "default"
    )


@router.post("/", response_model=DeploymentModel, operation_id="deployment_create")
@inject
async def deployment_create(
    body: DeploymentCreateRequest,
    project_service: ProjectServiceType,
    deployment_service: DeploymentServiceType,
):
    project = await project_service.get_by_git_url(body.git_url)
    if project is None:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "project_not_found"}}
        )

    good = await deployment_service.verify_version_is_good_to_go(
        project_rid=project.rid, version=body.version
    )
    if not good:
        raise HTTPException(
            status_code=400, detail={"error": {"code": "deployment_already_exists"}}
        )

    deployment = await deployment_service.create(
        project_rid=project.rid,
        version=body.version,
        mode=body.mode,
        scheduled_to_run_at=None,
    )

    return deployment
