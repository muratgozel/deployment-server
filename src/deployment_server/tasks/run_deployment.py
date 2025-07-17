from logging import Logger
from typing import Annotated
from celery import shared_task
from dependency_injector.wiring import inject, Provide
from deployment_server.containers.worker import WorkerContainer
from deployment_server.models import DeploymentStatus
from deployment_server.services.deployment import DeploymentService
from deployment_server.services.project import ProjectService
from deployment_server.packages.deployer import deployer


ProjectServiceType = Annotated[ProjectService, Provide[WorkerContainer.project_service]]
DeploymentServiceType = Annotated[
    DeploymentService, Provide[WorkerContainer.deployment_service]
]
LoggerType = Annotated[Logger, Provide[WorkerContainer.logger]]


@shared_task()
@inject
def run_deployment(
    project_service: ProjectServiceType,
    deployment_service: DeploymentServiceType,
    logger: LoggerType,
):
    logger.debug("checking deployment tasks.")
    rec = deployment_service.pick_deployment_sync()
    if rec is None:
        logger.debug("no deployment tasks found.")
        return

    deployment_service.send_status_update_sync(rec.rid, DeploymentStatus.RUNNING)

    project = project_service.get_by_code_sync(rec.project_code)

    logger.debug(f"deploying project {project.name or project.git_url}.")

    mode = rec.mode or "default"
    success, message = deployer.deploy(
        project_code=rec.project_code,
        mode=mode,
        pip_package_name=project.pip_package_name,
        pip_index_url=project.pip_index_url,
        pip_index_user=project.pip_index_user,
        pip_index_auth=project.pip_index_auth,
        daemons=project.daemons,
        secrets_provider=project.secrets_provider,
    )
    if not success:
        deployer.logger.error(message)
        deployment_service.send_status_update_sync(rec.rid, DeploymentStatus.FAILED)
        return False

    deployment_service.send_status_update_sync(rec.rid, DeploymentStatus.SUCCESS)

    return True
