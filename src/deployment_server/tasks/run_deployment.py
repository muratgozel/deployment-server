from typing import Annotated
from celery import shared_task
from dependency_injector.wiring import inject, Provide
from deployment_server.containers import WorkerContainer
from deployment_server.models import DeploymentStatus
from deployment_server.services.deployment import DeploymentService
from deployment_server.services.project import ProjectService
from deployment_server.packages.deployer import deployer


ProjectServiceType = Annotated[ProjectService, Provide[WorkerContainer.project_service]]
DeploymentServiceType = Annotated[
    DeploymentService, Provide[WorkerContainer.deployment_service]
]


@shared_task
@inject
async def run_deployment(
    project_service: ProjectServiceType, deployment_service: DeploymentServiceType
):
    rec = await deployment_service.pick_deployment()
    if rec is None:
        return

    await deployment_service.send_status_update(rec.rid, DeploymentStatus.RUNNING)

    project = await project_service.get_by_code(rec.project_code)

    mode = rec.mode or "default"
    success, message = deployer.deploy(
        project_code=rec.project_code,
        mode=mode,
        systemd_units=project.systemd_units,
        pip_package_name=project.pip_package_name,
        pip_index_url=project.pip_index_url,
        pip_index_user=project.pip_index_user,
        pip_index_auth=project.pip_index_auth,
    )
    if not success:
        deployer.logger.error(message)
        await deployment_service.send_status_update(rec.rid, DeploymentStatus.FAILED)
        return False

    await deployment_service.send_status_update(rec.rid, DeploymentStatus.SUCCESS)

    return True
