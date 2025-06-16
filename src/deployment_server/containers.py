import os
import logging
from typing import AsyncGenerator
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dependency_injector import containers, providers
from postmarker.core import PostmarkClient
from deployment_server.repositories.project import ProjectRepository
from deployment_server.services.project import ProjectService


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


class Core(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    logger = providers.Resource(init_logging, name=config.name, debug=config.debug)


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


class ServerGateways(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    postmark = PostmarkClient(server_token=config.postmark_server_token)
    session_factory = providers.Resource(create_session_factory, conn_str=config.pg_conn_str)


class Server(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    gateways = providers.DependenciesContainer()
    project_repo = providers.Factory(ProjectRepository, session_factory=gateways.session_factory)
    project_service = providers.Factory(ProjectService, project_repo=project_repo)


def find_yaml_files() -> list[str | Path]:
    config_dir = Path(os.environ.get("APPLICATION_CONFIG_DIR"))
    os.makedirs(config_dir.as_posix(), exist_ok=True)
    config_file_names_to_load = ("config.yaml", f"config_{os.environ.get('APPLICATION_MODE')}.yaml")
    yaml_files = [config_dir / name for name in config_file_names_to_load if (config_dir / name).exists()]
    if len(yaml_files) == 0:
        raise FileNotFoundError(f"no configuration files found in {config_dir.as_posix()}")
    return yaml_files


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["deployment_server.routers.project"])
    config = providers.Configuration(yaml_files=find_yaml_files(), strict=True)
    core = providers.Container(Core, config=config.core)
    gateways = providers.Container(ServerGateways, config=config.server_gateways)
    server = providers.Container(Server, config=config.server, gateways=gateways)
