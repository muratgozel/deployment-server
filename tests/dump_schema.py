from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from deployment_server import models


def dump_schema_to_text():
    dialect = postgresql.dialect()
    schema_sql = []

    for table in models.ModelBase.metadata.sorted_tables:
        create_sql = str(CreateTable(table).compile(dialect=dialect))
        schema_sql.append(create_sql)

    return "\n\n".join(schema_sql)


text = dump_schema_to_text()
print(text)
