import enum
import nanoid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Enum, TIMESTAMP, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    Mapped,
    mapped_column,
    declared_attr,
)
from sqlalchemy.sql import func


class ModelBase(AsyncAttrs, DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        default=datetime.now(timezone.utc),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), onupdate=func.current_timestamp()
    )
    removed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    rid: Mapped[str]

    @declared_attr
    def rid(cls) -> Mapped[str]:
        return mapped_column(String, primary_key=True)

    @staticmethod
    def generate_rid():
        return nanoid.generate("0123456789abcdefghijklmnopqrstuvwxyz", 16)


class Project(ModelBase):
    __tablename__ = "project"
    rid: Mapped[str]

    name: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(String)
    git_url: Mapped[Optional[str]] = mapped_column(String)
    pip_package_name: Mapped[Optional[str]] = mapped_column(String)
    pip_index_url: Mapped[Optional[str]] = mapped_column(String)
    pip_index_user: Mapped[Optional[str]] = mapped_column(String)
    pip_index_auth: Mapped[Optional[str]] = mapped_column(String)

    deployments: Mapped[list["Deployment"]] = relationship(
        back_populates="project", lazy="selectin"
    )


class Deployment(ModelBase):
    __tablename__ = "deployment"
    rid: Mapped[str]

    version: Mapped[str] = mapped_column(String)
    is_fresh: Mapped[bool] = mapped_column(Boolean, default=True)
    git_branch: Mapped[str] = mapped_column(String)
    project_rid: Mapped[str] = mapped_column(
        String, ForeignKey("project.rid", ondelete="CASCADE")
    )

    project: Mapped["Project"] = relationship(
        back_populates="deployments", lazy="selectin"
    )
    status_updates: Mapped[list["DeploymentStatusUpdate"]] = relationship(
        back_populates="deployment", lazy="selectin"
    )


class DeploymentStatus(enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"


class DeploymentStatusUpdate(ModelBase):
    __tablename__ = "deployment_status_update"
    rid: Mapped[str]

    status: Mapped[DeploymentStatus] = mapped_column(Enum(DeploymentStatus))
    description: Mapped[Optional[str]] = mapped_column(String)
    deployment_rid: Mapped[str] = mapped_column(
        String, ForeignKey("deployment.rid", ondelete="CASCADE")
    )

    deployment: Mapped["Deployment"] = relationship(
        back_populates="status_updates", lazy="selectin"
    )
