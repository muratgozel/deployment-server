from logging import Logger
from celery import shared_task, current_app
from deployment_server.models import DeploymentStatus
from deployment_server.services.deployment import DeploymentService
from deployment_server.services.project import ProjectService
from deployment_server.packages.deployer import deployer


@shared_task()
def run_deployment():
    logger: Logger = current_app.container.logger()
    project_service: ProjectService = current_app.container.project_service()
    deployment_service: DeploymentService = current_app.container.deployment_service()
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
