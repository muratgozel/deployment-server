import os
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, update
from deployment_server.config import config
from deployment_server.dependencies import logger, AsyncSessionLocal
from deployment_server.models import (
    Project,
    Deployment,
    DeploymentStatusUpdate,
    DeploymentStatus,
)
from deployer import py


worker = Celery("tasks", broker=config.rabbitmq_conn_str)


@worker.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(
        crontab(minute="*"), run_deployment_task.s(), name="check deployments queue"
    )


@worker.task
async def run_deployment_task():
    logger.debug("checking deployments queue")
    async with AsyncSessionLocal() as session:
        statement = (
            select(Deployment)
            .where(Deployment.is_fresh is True, Deployment.removed_at is None)
            .limit(1)
        )
        deployment: Deployment | None = await session.scalar(statement)
        if deployment is None:
            return None

        # remove deployment's freshness
        statement = (
            update(Deployment)
            .where(Deployment.rid == deployment.rid)
            .values(is_fresh=False)
        )
        result = await session.execute(statement)
        if result.rowcount != 1:
            logger.error(
                f"failed to remove the deployment's ({deployment.rid}) freshness"
            )
            return None
        await session.commit()

        # verify project
        statement = select(Project).where(
            Project.rid == deployment.project_rid, Project.removed_at is None
        )
        project: Project | None = await session.scalar(statement)
        if project is None:
            return None

        # send deployment status update
        update1 = DeploymentStatusUpdate(
            rid=DeploymentStatusUpdate.generate_rid(),
            status=DeploymentStatus.RUNNING,
            deployment_rid=deployment.rid,
        )
        session.add(update1)
        await session.commit()

        # deploy
        logger.info(f"deploying project {project.name}...")
        logger.debug(f"verifying project installation directory...")
        env = "prod"
        dir_name = f"{env}-{project.name}"
        install_dir = os.path.join("/opt", dir_name)
        os.makedirs(install_dir, exist_ok=True)
        logger.debug(f"verifying project installation directory... done.")

        # TODO fetch secrets

        try:
            if project.pip_package_name:
                success, message = py.deploy(project, install_dir)
                if success:
                    logger.info(f"deploying project {project.name}... done.")
                    update2 = DeploymentStatusUpdate(
                        rid=DeploymentStatusUpdate.generate_rid(),
                        status=DeploymentStatus.SUCCESS,
                        deployment_rid=deployment.rid,
                    )
                    session.add(update2)
                    await session.commit()
                    return True
        except Exception as e:
            logger.info(f"deploying project {project.name}... failed. {e}")

        update2 = DeploymentStatusUpdate(
            rid=DeploymentStatusUpdate.generate_rid(),
            status=DeploymentStatus.FAILED,
            deployment_rid=deployment.rid,
        )
        session.add(update2)
        await session.commit()

        return None


@worker.task
async def create_deployment_task(version: str, repo_parts: tuple[str, str, str]):
    logger.info(f"creating deployment task for {repo_parts}:{version}")
    async with AsyncSessionLocal() as session:
        vendor, owner, name = repo_parts
        project_name = f"{owner}/{name}"

        # verify project exists
        statement = select(Project).where(
            Project.name == project_name, Project.removed_at is None
        )
        project: Project | None = await session.scalar(statement)
        if project is None:
            logger.info(f"project {project_name} not found.")
            return None

        deployment = Deployment(
            rid=Deployment.generate_rid(), project_rid=project.rid, version=version
        )
        status_update = DeploymentStatusUpdate(
            rid=DeploymentStatusUpdate.generate_rid(),
            deployment_rid=deployment.rid,
            status=DeploymentStatus.CREATED,
        )
        session.add(deployment)
        session.add(status_update)
        await session.commit()

        logger.info(
            f"creating deployment task for {repo_parts}:{version} is successful"
        )
        return deployment
