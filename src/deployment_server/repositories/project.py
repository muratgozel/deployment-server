from datetime import datetime, timezone
from typing import Callable, AsyncContextManager
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from deployment_server.models import Project


class ProjectRepository:
    def __init__(
        self, session_factory: Callable[[], AsyncContextManager[AsyncSession]]
    ):
        self.session_factory = session_factory

    async def get_all(self) -> list[Project]:
        async with self.session_factory() as session:
            statement = select(Project).where(Project.removed_at.is_(None))
            result = await session.scalars(statement)
            return list(result.all())

    async def get_by_code(self, code: str) -> Project | None:
        async with self.session_factory() as session:
            statement = select(Project).where(
                Project.code == code, Project.removed_at.is_(None)
            )
            result = await session.scalars(statement)
            recs = result.all()
            if len(recs) == 0:
                return None
            if len(recs) == 1:
                return recs[0]
            raise ValueError("multiple projects found with the same project code.")

    async def get_by_rid(self, rid: str) -> Project | None:
        async with self.session_factory() as session:
            statement = select(Project).where(
                Project.rid == rid, Project.removed_at.is_(None)
            )
            result = await session.scalars(statement)
            recs = result.all()
            if len(recs) == 0:
                return None
            if len(recs) == 1:
                return recs[0]
            raise ValueError("multiple projects found with the same project rid.")

    async def add(self, project: Project) -> Project:
        async with self.session_factory() as session:
            session.add(project)
            await session.commit()
            return project

    async def remove_by_rid(self, rid: str) -> bool:
        async with self.session_factory() as session:
            statement = (
                update(Project)
                .where(Project.rid == rid)
                .values(removed_at=datetime.now(timezone.utc))
            )
            result = await session.execute(statement)
            if result.rowcount == 1:
                await session.commit()
                return True
            return False
