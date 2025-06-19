from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from sqlalchemy import select, and_
from deployment_server import models


def dump_schema_to_text():
    dialect = postgresql.dialect()
    schema_sql = []

    for table in models.ModelBase.metadata.sorted_tables:
        create_sql = str(CreateTable(table).compile(dialect=dialect))
        schema_sql.append(create_sql)

    return "\n\n".join(schema_sql)


text = dump_schema_to_text()
# print(text)


def sample():
    Deployment = models.Deployment
    DeploymentStatusUpdate = models.DeploymentStatusUpdate
    Project = models.Project

    query = (
        select(
            Deployment.rid.label("deployment_rid"),
            Deployment.version,
            DeploymentStatusUpdate.status,
        )
        .join(Project, Deployment.project_rid == Project.rid)
        .outerjoin(
            DeploymentStatusUpdate,
            Deployment.rid == DeploymentStatusUpdate.deployment_rid,
        )
        .where(
            and_(
                Deployment.removed_at.is_(None),
                Project.removed_at.is_(None),
                Project.rid == "p1",
                DeploymentStatusUpdate.removed_at.is_(None),
            )
        )
        .distinct(Deployment.rid)
        .order_by(Deployment.rid, DeploymentStatusUpdate.created_at.desc())
    )
    print(query)


sample()
