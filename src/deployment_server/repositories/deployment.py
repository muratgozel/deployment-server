from datetime import datetime, timezone
from typing import Callable, AsyncContextManager, ContextManager
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from deployment_server.models import (
    Deployment,
    DeploymentStatusUpdate,
    DeploymentStatus,
    Project,
)


class LatestStatusType:
    rid: str
    deployment_rid: str
    version: str
    mode: str | None
    status: str
    project_code: str


class DeploymentRepository:
    def __init__(
        self,
        session_factory: (
            Callable[[], AsyncContextManager[AsyncSession]]
            | Callable[[], ContextManager[Session]]
        ),
    ):
        self.session_factory = session_factory

    def get_statement_latest_statuses(
        self, project_rid: str = None, version: str = None
    ):
        conditions = []
        if project_rid:
            conditions.append(Project.rid == project_rid)
        if version:
            conditions.append(Deployment.version == version)
        conditions.extend(
            (
                Deployment.removed_at.is_(None),
                Project.removed_at.is_(None),
                DeploymentStatusUpdate.removed_at.is_(None),
            )
        )
        return (
            select(
                Deployment.rid.label("deployment_rid"),
                Deployment.version,
                Deployment.mode,
                DeploymentStatusUpdate.rid,
                DeploymentStatusUpdate.status,
                Project.code.label("project_code"),
            )
            .join(Project, Deployment.project_rid == Project.rid)
            .outerjoin(
                DeploymentStatusUpdate,
                Deployment.rid == DeploymentStatusUpdate.deployment_rid,
            )
            .where(and_(*conditions))
            .distinct(Deployment.rid)
            .order_by(Deployment.rid, DeploymentStatusUpdate.created_at.desc())
        )

    async def get_latest_statuses(
        self, project_rid: str, version: str
    ) -> list[LatestStatusType]:
        async with self.session_factory() as session:
            statement = self.get_statement_latest_statuses(project_rid, version)
            result = await session.scalars(statement)
            return list(result.all())

    async def pick_deployment(self) -> LatestStatusType | None:
        async with self.session_factory() as session:
            inner_statement = self.get_statement_latest_statuses()
            subquery = inner_statement.subquery()
            statement = (
                select(subquery)
                .where(subquery.c.status == DeploymentStatus.READY)
                .limit(1)
            )
            result = await session.scalars(statement)
            return result.first()

    def pick_deployment_sync(self) -> LatestStatusType | None:
        with self.session_factory() as session:
            inner_statement = self.get_statement_latest_statuses()
            subquery = inner_statement.subquery()
            statement = (
                select(subquery)
                .where(subquery.c.status == DeploymentStatus.READY)
                .limit(1)
            )
            result = session.scalars(statement)
            return result.first()

    async def status_update(
        self, status_rid: str, value: DeploymentStatus, description: str = None
    ):
        async with self.session_factory() as session:
            statement = (
                update(DeploymentStatusUpdate)
                .where(DeploymentStatusUpdate.rid == status_rid)
                .values(status=value, description=description)
            )
            result = await session.execute(statement)
            if result.rowcount == 1:
                await session.commit()
                return True
            return False

    def status_update_sync(
        self, status_rid: str, value: DeploymentStatus, description: str = None
    ):
        with self.session_factory() as session:
            statement = (
                update(DeploymentStatusUpdate)
                .where(DeploymentStatusUpdate.rid == status_rid)
                .values(status=value, description=description)
            )
            result = session.execute(statement)
            if result.rowcount == 1:
                session.commit()
                return True
            return False

    async def get_all(self) -> list[Deployment]:
        async with self.session_factory() as session:
            statement = select(Deployment).where(Deployment.removed_at.is_(None))
            result = await session.scalars(statement)
            return list(result.all())

    async def get_one_by(self, column_name: str, value: str) -> Deployment | None:
        async with self.session_factory() as session:
            statement = select(Deployment).where(
                getattr(Deployment, column_name) == value,
                Deployment.removed_at.is_(None),
            )
            result = await session.scalars(statement)
            recs = result.all()
            if len(recs) == 0:
                return None
            if len(recs) == 1:
                return recs[0]
            raise ValueError(f"multiple deployments found with the same {column_name}.")

    async def add(
        self, deployment: Deployment, status_update: DeploymentStatusUpdate
    ) -> Deployment:
        async with self.session_factory() as session:
            session.add(deployment)
            session.add(status_update)
            await session.commit()
            return deployment

    async def remove_by_rid(self, rid: str) -> bool:
        async with self.session_factory() as session:
            statement = (
                update(Deployment)
                .where(Deployment.rid == rid)
                .values(removed_at=datetime.now(timezone.utc))
            )
            result = await session.execute(statement)
            if result.rowcount == 1:
                await session.commit()
                return True
            return False
