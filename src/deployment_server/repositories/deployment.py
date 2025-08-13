from datetime import datetime, timezone
from typing import Callable, AsyncContextManager, ContextManager
from pydantic import BaseModel
from sqlalchemy import select, update, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from deployment_server.models import (
    Deployment,
    DeploymentStatusUpdate,
    DeploymentStatus,
    Project,
)


class LatestStatusType(BaseModel):
    project_rid: str
    project_name: str
    project_code: str
    deployment_rid: str
    version: str
    mode: str
    status: DeploymentStatus
    rid: str
    # rid: str
    # deployment_rid: str
    # version: str
    # mode: str | None
    # status: str
    # project_code: str


def repr_latest_status(
    rid: str,
    status: DeploymentStatus,
    mode: str,
    version: str,
    deployment_rid: str,
    project_rid: str,
    project_name: str,
    project_code: str,
):
    return LatestStatusType(
        rid=rid,
        status=status,
        mode=mode,
        version=version,
        deployment_rid=deployment_rid,
        project_rid=project_rid,
        project_name=project_name,
        project_code=project_code,
    )


class DeploymentRepository:
    def __init__(
        self,
        session_factory: (
            Callable[[], AsyncContextManager[AsyncSession]]
            | Callable[[], ContextManager[Session]]
        ),
    ):
        self.session_factory = session_factory
        self.query_latest_status = """
WITH latest_status AS (
    SELECT
        rid,
        deployment_rid,
        status,
        description,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY deployment_rid ORDER BY created_at DESC) as rn
    FROM deployment_status_update
    WHERE removed_at IS NULL
)
SELECT
    p.rid as project_rid,
    p.name as project_name,
    p.code as project_code,
    d.rid as deployment_rid,
    d.version,
    d.mode,
    ls.status,
    ls.rid
FROM deployment d
JOIN project p ON d.project_rid = p.rid
JOIN latest_status ls ON d.rid = ls.deployment_rid
WHERE d.removed_at IS NULL
    AND p.removed_at IS NULL
    AND ls.status = 'READY'
ORDER BY d.created_at DESC;
"""

    async def get_latest_statuses(
        self, project_rid: str, version: str
    ) -> list[LatestStatusType]:
        async with self.session_factory() as session:
            query = """
SELECT
    DISTINCT ON (d.rid) d.rid as deployment_rid,
    d.version,
    d.mode,
    ds.rid,
    ds.status,
    p.rid as project_rid,
    p.code as project_code,
    p.name as project_name
FROM deployment d
JOIN project p ON p.rid = d.project_rid
LEFT OUTER JOIN deployment_status_update ds ON ds.deployment_rid = d.rid
WHERE
    p.rid = :project_rid AND
    d.version = :version AND
    d.removed_at IS NULL AND
    p.removed_at IS NULL AND
    ds.removed_at IS NULL
ORDER BY d.rid, ds.created_at DESC;
"""
            result = await session.execute(
                text(query), {"project_rid": project_rid, "version": version}
            )
            rows = result.all()
            if len(rows) == 0:
                return []
            results = [
                repr_latest_status(
                    project_rid=arr[5],
                    project_name=arr[7],
                    project_code=arr[6],
                    deployment_rid=arr[0],
                    version=arr[1],
                    mode=arr[2] or "default",
                    status=arr[4],
                    rid=arr[3],
                )
                for arr in rows
            ]
            return results

    async def pick_deployment(self) -> LatestStatusType | None:
        async with self.session_factory() as session:
            result = await session.execute(text(self.query_latest_status))
            rows = result.all()
            if len(rows) == 0:
                return None
            results = [
                repr_latest_status(
                    project_rid=arr[0],
                    project_name=arr[1],
                    project_code=arr[2],
                    deployment_rid=arr[3],
                    version=arr[4],
                    mode=arr[5] or "default",
                    status=arr[6],
                    rid=arr[7],
                )
                for arr in rows
            ]
            if len(results) == 1:
                return results[0]
            rest = results[1:]
            ids = [x.rid for x in rest]
            await self.status_update(status_rid=ids, value=DeploymentStatus.SKIPPED)
            return results[0]

    def pick_deployment_sync(self) -> LatestStatusType | None:
        with self.session_factory() as session:
            result = session.execute(text(self.query_latest_status))
            rows = result.all()
            if len(rows) == 0:
                return None
            results = [
                repr_latest_status(
                    project_rid=arr[0],
                    project_name=arr[1],
                    project_code=arr[2],
                    deployment_rid=arr[3],
                    version=arr[4],
                    mode=arr[5] or "default",
                    status=arr[6],
                    rid=arr[7],
                )
                for arr in rows
            ]
            if len(results) == 1:
                return results[0]
            rest = results[1:]
            ids = [x.rid for x in rest]
            self.status_update_sync(status_rid=ids, value=DeploymentStatus.SKIPPED)
            return results[0]

    async def status_update(
        self,
        status_rid: str | list[str],
        value: DeploymentStatus,
        description: str = None,
    ):
        is_bulk = False if isinstance(status_rid, str) else True
        async with self.session_factory() as session:
            statement = (
                update(DeploymentStatusUpdate)
                .where(
                    DeploymentStatusUpdate.rid == status_rid
                    if not is_bulk
                    else DeploymentStatusUpdate.rid.in_(status_rid)
                )
                .values(status=value, description=description)
            )
            result = await session.execute(statement)
            if not is_bulk:
                if result.rowcount == 1:
                    await session.commit()
                    return True
                return False
            else:
                if result.rowcount > 1:
                    await session.commit()
                    return True
                return False

    def status_update_sync(
        self,
        status_rid: str | list[str],
        value: DeploymentStatus,
        description: str = None,
    ):
        is_bulk = False if isinstance(status_rid, str) else True
        with self.session_factory() as session:
            statement = (
                update(DeploymentStatusUpdate)
                .where(
                    DeploymentStatusUpdate.rid == status_rid
                    if not is_bulk
                    else DeploymentStatusUpdate.rid.in_(status_rid)
                )
                .values(status=value, description=description)
            )
            result = session.execute(statement)
            if not is_bulk:
                if result.rowcount == 1:
                    session.commit()
                    return True
                return False
            else:
                if result.rowcount > 1:
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
