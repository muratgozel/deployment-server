from dependency_injector import containers, providers
from deployment_server.repositories.project import ProjectRepository
from deployment_server.services.project import ProjectService
from deployment_server.repositories.deployment import DeploymentRepository
from deployment_server.services.deployment import DeploymentService
from deployment_server.containers.common import (
    find_yaml_files,
    init_logging,
    create_session_factory,
)


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "deployment_server.routers.project",
            "deployment_server.routers.deployment",
        ],
        packages=["deployment_server.packages.utils"],
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
