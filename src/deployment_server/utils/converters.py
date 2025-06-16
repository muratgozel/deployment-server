from pydantic import BaseModel, ConfigDict, create_model
from typing import get_type_hints, Type, Set, Optional, get_origin, get_args
from sqlalchemy.orm import Mapped


def sqlalchemy_to_pydantic(
    sqlalchemy_model: Type,
    model_name: str,
    exclude_fields: Optional[Set[str]] = None,
    include_relationships: bool = False,
) -> Type[BaseModel]:
    """
    Create a Pydantic model from SQLAlchemy model with minimal boilerplate
    """

    def extract_sqlalchemy_type(field_type):
        """
        Extract the actual type from SQLAlchemy Mapped annotations
        """
        # Check if it's a Mapped type
        if get_origin(field_type) is Mapped:
            # Get the inner type from Mapped[SomeType]
            args = get_args(field_type)
            if args:
                return args[0]

        return field_type

    exclude_fields = exclude_fields or {"registry", "metadata"}

    if not include_relationships:
        # Auto-detect relationship fields and exclude them
        relationship_fields = set()
        for attr_name in dir(sqlalchemy_model):
            attr = getattr(sqlalchemy_model, attr_name)
            if hasattr(attr, "property") and hasattr(attr.property, "mapper"):
                relationship_fields.add(attr_name)
        exclude_fields.update(relationship_fields)

    type_hints = get_type_hints(sqlalchemy_model, include_extras=False)

    fields = {}
    for field_name, field_type in type_hints.items():
        if not field_name.startswith("_") and field_name not in exclude_fields:
            actual_type = extract_sqlalchemy_type(field_type)
            fields[field_name] = (actual_type, None)

    return create_model(
        model_name, __config__=ConfigDict(from_attributes=True), **fields
    )
