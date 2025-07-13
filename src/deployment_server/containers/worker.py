from dependency_injector import containers, providers
from postmarker.core import PostmarkClient
from deployment_server.repositories.project import ProjectRepository
from deployment_server.services.project import ProjectService
from deployment_server.repositories.deployment import DeploymentRepository
from deployment_server.services.deployment import DeploymentService
from deployment_server.containers.common import (
    init_logging,
    create_session_factory_sync,
    find_yaml_files,
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
