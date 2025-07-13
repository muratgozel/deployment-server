import secrets
from typing import Annotated
from dependency_injector import providers
from dependency_injector.wiring import Provide, inject
from pydantic import BaseModel, Field, AfterValidator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import PlainTextResponse
from deployment_server.models import Project, SystemdUnit, SecretsProvider
from deployment_server.services.project import ProjectService
from deployment_server.containers.server import ServerContainer
from deployment_server.packages.utils import converters, validators

ProjectRid = Annotated[str, Field(max_length=64, min_length=1)]
ProjectServiceType = Annotated[
    ProjectService, Depends(Provide[ServerContainer.project_service])
]


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
    prefix="/project", tags=["project"], dependencies=[Depends(authenticate)]
)


class ProjectCreateRequestBody(BaseModel):
    name: Annotated[str, Field(max_length=64, min_length=1)]
    code: Annotated[str | None, Field(max_length=64, min_length=1, default=None)] = None
    git_url: Annotated[str | None, AfterValidator(validators.url_pydantic)] = None
    pip_package_name: Annotated[
        str | None, AfterValidator(validators.pip_package_name_pydantic)
    ] = None
    pip_index_url: Annotated[str | None, AfterValidator(validators.url_pydantic)] = None
    pip_index_user: Annotated[str | None, Field(max_length=64, min_length=1)] = None
    pip_index_auth: Annotated[str | None, Field(max_length=64, min_length=1)] = None
    systemd_units: Annotated[list[SystemdUnit] | None, Field(default=None)] = None
    secrets_provider: Annotated[SecretsProvider, Field(default=SecretsProvider.LOCAL)]


ProjectModel = converters.sqlalchemy_to_pydantic(Project, "ProjectModel")


@router.post("/", response_model=ProjectModel, operation_id="project_create")
@inject
async def project_create(
    body: ProjectCreateRequestBody, project_service: ProjectServiceType
):
    code = project_service.validate_code(body.code or body.name)
    if len(code) == 0:
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_code"}})

    existing_project = await project_service.get_by_code(code)
    if existing_project is not None:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "project_already_exists"}}
        )

    new_project = await project_service.create(
        name=body.name,
        code=code,
        git_url=body.git_url,
        pip_package_name=body.pip_package_name,
        pip_index_url=body.pip_index_url,
        pip_index_user=body.pip_index_user,
        pip_index_auth=body.pip_index_auth,
        daemons=body.systemd_units,
        secrets_provider=body.secrets_provider,
    )
    return new_project


@router.get("/list", response_model=list[ProjectModel], operation_id="project_list")
@inject
async def project_list(project_service: ProjectServiceType):
    return await project_service.get_all()


@router.get("/{rid}", response_model=ProjectModel, operation_id="project_get")
@inject
async def project_get(rid: ProjectRid, project_service: ProjectServiceType):
    project = await project_service.get_by_rid(rid)
    if project is None:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "project_not_found"}}
        )
    return project


class ProjectRemoveResponse(BaseModel):
    rid: str


@router.delete(
    "/{rid}", response_class=PlainTextResponse, operation_id="project_remove"
)
@inject
async def project_remove(rid: ProjectRid, project_service: ProjectServiceType):
    project = await project_service.get_by_rid(rid)
    if project is None:
        raise HTTPException(
            status_code=409, detail={"error": {"code": "project_not_found"}}
        )

    result = await project_service.remove_by_rid(project.rid)
    status_code = 204 if result is True else 404

    return PlainTextResponse(status_code=status_code)
