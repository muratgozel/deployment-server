import enum
import nanoid
from typing import Optional, Annotated
from datetime import datetime, timezone
from pydantic import BaseModel, Field, AfterValidator
from sqlalchemy import String, ForeignKey, Enum, TIMESTAMP, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    Mapped,
    mapped_column,
    declared_attr,
)
from sqlalchemy.sql import func
from deployment_server.packages.utils import validators


class SystemdUnit(BaseModel):
    name: Annotated[
        str,
        Field(max_length=64, min_length=1),
        AfterValidator(validators.pip_package_name_pydantic),
    ]
    port: Annotated[int | None, Field(ge=1000, le=9999)] = None
    py_module_name: Annotated[
        str | None, AfterValidator(validators.pip_package_name_pydantic)
    ] = None


class SecretsProvider(enum.Enum):
    LOCAL = "LOCAL"
    COLDRUNE = "COLDRUNE"


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
    secrets_provider: Mapped[SecretsProvider] = mapped_column(
        Enum(SecretsProvider, name="secrets_provider")
    )

    deployments: Mapped[list["Deployment"]] = relationship(
        back_populates="project", lazy="selectin"
    )
    daemons: Mapped[list["Daemon"]] = relationship(
        back_populates="project", lazy="selectin"
    )


class DaemonType(enum.Enum):
    SYSTEMD = "SYSTEMD"
    DOCKER = "DOCKER"


class Daemon(ModelBase):
    __tablename__ = "daemon"
    rid: Mapped[str]

    type: Mapped[DaemonType] = mapped_column(Enum(DaemonType, name="daemon_type"))
    name: Mapped[str] = mapped_column(String)
    port: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    py_module_name: Mapped[Optional[str]] = mapped_column(String)
    project_rid: Mapped[str] = mapped_column(
        String, ForeignKey("project.rid", ondelete="CASCADE")
    )

    project: Mapped["Project"] = relationship(back_populates="daemons", lazy="selectin")


class Deployment(ModelBase):
    __tablename__ = "deployment"
    rid: Mapped[str]

    version: Mapped[str] = mapped_column(String)
    mode: Mapped[Optional[str]] = mapped_column(String)
    scheduled_to_run_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
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
    SCHEDULED = "SCHEDULED"
    READY = "READY"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"


class DeploymentStatusUpdate(ModelBase):
    __tablename__ = "deployment_status_update"
    rid: Mapped[str]

    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status")
    )
    description: Mapped[Optional[str]] = mapped_column(String)
    deployment_rid: Mapped[str] = mapped_column(
        String, ForeignKey("deployment.rid", ondelete="CASCADE")
    )

    deployment: Mapped["Deployment"] = relationship(
        back_populates="status_updates", lazy="selectin"
    )
