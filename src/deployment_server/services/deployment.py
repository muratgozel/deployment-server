import datetime
from deployment_server.repositories.deployment import DeploymentRepository
from deployment_server.models import (
    Deployment,
    DeploymentStatus,
    DeploymentStatusUpdate,
)


class DeploymentService:
    def __init__(self, deployment_repo: DeploymentRepository):
        self.deployment_repo: DeploymentRepository = deployment_repo

    async def verify_version_is_good_to_go(
        self, project_rid: str, version: str
    ) -> bool:
        statuses_acceptable = [DeploymentStatus.FAILED]
        recs = await self.deployment_repo.get_latest_statuses(project_rid, version)
        if len(recs) == 0:
            return True
        if len(recs) > 0:
            recs_filtered = [x.status for x in recs if x.status in statuses_acceptable]
            if len(recs_filtered) == len(recs):
                return True
        return False

    async def pick_deployment(self):
        return await self.deployment_repo.pick_deployment()

    def pick_deployment_sync(self):
        return self.deployment_repo.pick_deployment_sync()

    async def send_status_update(
        self, status_rid: str, value: DeploymentStatus, description: str = None
    ):
        return await self.deployment_repo.status_update(status_rid, value, description)

    def send_status_update_sync(
        self, status_rid: str, value: DeploymentStatus, description: str = None
    ):
        return self.deployment_repo.status_update_sync(status_rid, value, description)

    async def get_all(self):
        return await self.deployment_repo.get_all()

    async def get_by_rid(self, rid: str):
        return await self.deployment_repo.get_one_by("rid", rid)

    async def create(
        self,
        project_rid: str,
        version: str,
        scheduled_to_run_at: datetime.datetime = None,
    ):
        deployment = Deployment(
            rid=Deployment.generate_rid(),
            project_rid=project_rid,
            version=version,
            scheduled_to_run_at=scheduled_to_run_at,
        )
        status_update = DeploymentStatusUpdate(
            rid=DeploymentStatusUpdate.generate_rid(),
            status=DeploymentStatus.READY,
            deployment_rid=deployment.rid,
        )
        return await self.deployment_repo.add(
            deployment=deployment, status_update=status_update
        )

    async def remove_by_rid(self, rid: str):
        return await self.deployment_repo.remove_by_rid(rid=rid)
