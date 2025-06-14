import secrets
from datetime import datetime, timezone
from typing import Annotated
from pydantic import BaseModel, Field, AfterValidator
from fastapi import APIRouter, HTTPException, Response, Request, Header, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, or_, and_, update
from slugify import slugify
from deployment_server.config import config
from deployment_server.dependencies import SessionDep
from deployment_server.models import Project
from deployment_server.core import py, urlextra


security = HTTPBasic()


async def authenticate(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    is_correct_user = secrets.compare_digest(credentials.username.encode(), config.api_user.encode())
    is_correct_secret = secrets.compare_digest(credentials.password.encode(), config.api_secret.encode())
    if not (is_correct_user and is_correct_secret):
        raise HTTPException(status_code=401,
                            detail={"error":{"code":"Unauthorized"}},
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


router = APIRouter(prefix="/project", tags=["project"], dependencies=[Depends(authenticate)])


class ProjectCreateRequestBody(BaseModel):
    name: Annotated[str, Field(max_length=64, min_length=1)]
    code: Annotated[str | None, Field(max_length=64, min_length=1, default=None)] = None
    git_url: Annotated[str | None, AfterValidator(urlextra.validate_pydantic)] = None
    pip_package_name: Annotated[str | None, AfterValidator(py.validate_pip_package_name_pydantic)] = None
    pip_index_url: Annotated[str | None, AfterValidator(urlextra.validate_pydantic)] = None
    pip_index_user: Annotated[str | None, Field(max_length=64, min_length=1)] = None
    pip_index_auth: Annotated[str | None, Field(max_length=64, min_length=1)] = None


class ProjectCreateResponse(BaseModel):
    rid: str


@router.post("/", response_model=ProjectCreateResponse, operation_id="project_create")
async def project_create(body: ProjectCreateRequestBody, session: SessionDep):
    code = slugify(body.code or body.name)
    if len(code) == 0:
        raise HTTPException(status_code=400, detail={"error":{"code":"invalid_code"}})

    statement = select(Project).where(Project.code == code, Project.removed_at.is_(None))
    existing_project: Project | None = await session.scalar(statement)
    if existing_project is not None:
        raise HTTPException(status_code=409, detail={"error":{"code":"project_already_exists"}})

    new_project = Project(rid=Project.generate_rid(),
                          name=body.name,
                          code=code,
                          git_url=body.git_url,
                          pip_package_name=body.pip_package_name,
                          pip_index_url=body.pip_index_url,
                          pip_index_user=body.pip_index_user,
                          pip_index_auth=body.pip_index_auth)
    session.add(new_project)
    await session.commit()
    return ProjectCreateResponse(rid=new_project.rid)


class ProjectOut(BaseModel):
    rid: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectOut] = []


@router.get("/list", response_model=ProjectListResponse, operation_id="project_list")
async def project_list(session: SessionDep):
    statement = select(Project).where(Project.removed_at.is_(None))
    projects: list[Project] | [] = await session.scalars(statement)
    return ProjectListResponse(projects=[x.__dict__ for x in projects])


class ProjectGetResponse(BaseModel):
    project: ProjectOut


@router.get("/{rid_or_code}", response_model=ProjectGetResponse, operation_id="project_get")
async def project_get(rid_or_code: Annotated[str, Field(max_length=64, min_length=1, default=None)], session: SessionDep):
    statement = select(Project).where(and_(or_(Project.rid == rid_or_code, Project.code == rid_or_code), Project.removed_at.is_(None)))
    project: Project | None = await session.scalar(statement)
    if project is None:
        raise HTTPException(status_code=409, detail={"error":{"code":"project_not_found"}})
    return ProjectGetResponse(project=project.__dict__)


class ProjectRemoveResponse(BaseModel):
    rid: str


@router.delete("/{rid_or_code}", response_model=ProjectRemoveResponse, operation_id="project_remove")
async def project_remove(rid_or_code: Annotated[str, Field(max_length=64, min_length=1, default=None)], session: SessionDep):
    statement = select(Project).where(and_(or_(Project.rid == rid_or_code, Project.code == rid_or_code), Project.removed_at.is_(None)))
    project: Project | None = await session.scalar(statement)
    if project is None:
        raise HTTPException(status_code=409, detail={"error":{"code":"project_not_found"}})

    statement = update(Project).where(Project.rid == project.rid).values(removed_at=datetime.now(timezone.utc))
    result = await session.execute(statement)
    if result.rowcount != 1:
        raise HTTPException(status_code=500, detail={"error":{"code":"internal_server_error"}})
    await session.commit()
    return ProjectRemoveResponse(rid=project.rid)
