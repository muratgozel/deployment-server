import os
import logging
from typing import AsyncGenerator, Generator
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dependency_injector import containers, providers
from postmarker.core import PostmarkClient
from deployment_server.repositories.project import ProjectRepository
from deployment_server.services.project import ProjectService
from deployment_server.repositories.deployment import DeploymentRepository
from deployment_server.services.deployment import DeploymentService


def init_logging(name: str, debug: bool = False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(stream_handler)

    yield logger

    # cleanup


async def create_session_factory(conn_str: str):
    engine = create_async_engine(conn_str)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()

    yield get_session

    await engine.dispose()


def create_session_factory_sync(conn_str: str):
    engine = create_engine(conn_str)
    SessionLocal = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def get_session() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    yield get_session

    engine.dispose()


def find_yaml_files(service_name: str) -> list[str | Path]:
    config_dir = Path(os.environ.get("APPLICATION_CONFIG_DIR"))
    os.makedirs(config_dir.as_posix(), exist_ok=True)
    config_file_names_to_load = (
        "config.yaml",
        f"config_{os.environ.get('APPLICATION_MODE')}.yaml",
        f"config_{service_name}.yaml",
        f"config_{os.environ.get('APPLICATION_MODE')}_{service_name}.yaml",
    )
    yaml_files = [
        config_dir / name
        for name in config_file_names_to_load
        if (config_dir / name).exists()
    ]
    if len(yaml_files) == 0:
        raise FileNotFoundError(
            f"no configuration files found in {config_dir.as_posix()}"
        )
    return yaml_files


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "deployment_server.routers.project",
            "deployment_server.routers.deployment",
        ]
    )
    config = providers.Configuration(yaml_files=find_yaml_files("server"), strict=True)
    logger = providers.Resource(init_logging, name=config.codename, debug=config.debug)
    session_factory = providers.Resource(
        create_session_factory, conn_str=config.pg_conn_str
    )
    project_repo = providers.Factory(ProjectRepository, session_factory=session_factory)
    project_service = providers.Factory(ProjectService, project_repo=project_repo)
    deployment_repo = providers.Factory(
        DeploymentRepository, session_factory=session_factory
    )
    deployment_service = providers.Factory(
        DeploymentService, deployment_repo=deployment_repo
    )


class WorkerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["deployment_server.packages.deployer"],
        modules=["deployment_server.tasks.run_deployment"],
    )
    config = providers.Configuration(yaml_files=find_yaml_files("worker"), strict=True)
    logger = providers.Resource(init_logging, name=config.codename, debug=config.debug)
    session_factory = providers.Resource(
        create_session_factory_sync, conn_str=config.pg_conn_str
    )
    postmark = PostmarkClient(server_token=config.postmark_server_token)
    project_repo = providers.Factory(ProjectRepository, session_factory=session_factory)
    project_service = providers.Factory(ProjectService, project_repo=project_repo)
    deployment_repo = providers.Factory(
        DeploymentRepository, session_factory=session_factory
    )
    deployment_service = providers.Factory(
        DeploymentService, deployment_repo=deployment_repo
    )
