from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from deployment_server.utils.converters import sqlalchemy_to_pydantic
from deployment_server.models import ModelBase


class SampleDatabaseObject(ModelBase):
    __tablename__ = "sample_database_object"
    # rid: Mapped[str] NOTE: should inherit rid from ModelBase

    name: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(String)
    git_url: Mapped[Optional[str]] = mapped_column(String)
    pip_package_name: Mapped[Optional[str]] = mapped_column(String)
    pip_index_url: Mapped[Optional[str]] = mapped_column(String)
    pip_index_user: Mapped[Optional[str]] = mapped_column(String)
    pip_index_auth: Mapped[Optional[str]] = mapped_column(String)


def test_sqlalchemy_to_pydantic():
    result = sqlalchemy_to_pydantic(SampleDatabaseObject, "Sample")
    assert result.__name__ == "Sample"
    assert list(result.model_fields.keys()) == [
        "created_at",
        "updated_at",
        "removed_at",
        "rid",
        "name",
        "code",
        "git_url",
        "pip_package_name",
        "pip_index_url",
        "pip_index_user",
        "pip_index_auth",
    ]
