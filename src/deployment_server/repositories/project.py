from datetime import datetime, timezone
from typing import Callable, AsyncContextManager, ContextManager
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from deployment_server.models import Project, SystemdUnit, Daemon, DaemonType


class ProjectRepository:
    def __init__(
        self,
        session_factory: (
            Callable[[], AsyncContextManager[AsyncSession]]
            | Callable[[], ContextManager[Session]]
        ),
    ):
        self.session_factory = session_factory

    async def get_all(self) -> list[Project]:
        async with self.session_factory() as session:
            statement = select(Project).where(Project.removed_at.is_(None))
            result = await session.scalars(statement)
            return list(result.all())

    async def get_one_by(self, column_name: str, value: str) -> Project | None:
        async with self.session_factory() as session:
            statement = select(Project).where(
                getattr(Project, column_name) == value, Project.removed_at.is_(None)
            )
            result = await session.scalars(statement)
            recs = result.all()
            if len(recs) == 0:
                return None
            if len(recs) == 1:
                return recs[0]
            raise ValueError(
                f"multiple projects found with the same project {column_name}."
            )

    def get_one_by_sync(self, column_name: str, value: str) -> Project | None:
        with self.session_factory() as session:
            statement = select(Project).where(
                getattr(Project, column_name) == value, Project.removed_at.is_(None)
            )
            result = session.scalars(statement)
            recs = result.all()
            if len(recs) == 0:
                return None
            if len(recs) == 1:
                return recs[0]
            raise ValueError(
                f"multiple projects found with the same project {column_name}."
            )

    async def add(self, project: Project, daemons: list[SystemdUnit] = None) -> Project:
        async with self.session_factory() as session:
            session.add(project)

            if isinstance(daemons, list) and len(daemons) > 0:
                daemons = [
                    Daemon(
                        rid=Daemon.generate_rid(),
                        type=DaemonType.SYSTEMD,
                        project_rid=project.rid,
                        name=d.name,
                        port=d.port or None,
                        py_module_name=d.py_module_name or None,
                    )
                    for d in daemons
                ]
                session.add_all(daemons)

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
