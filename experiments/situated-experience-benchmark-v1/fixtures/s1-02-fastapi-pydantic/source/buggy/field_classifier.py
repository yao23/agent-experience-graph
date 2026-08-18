"""Dependency-free extract of FastAPI's Pydantic field classifier."""

from dataclasses import dataclass, field as dataclass_field


SINGLETON = "singleton"
SEQUENCE_TYPES = (list, set, tuple, dict)


class BaseModel:
    pass


class Body:
    pass


@dataclass
class Field:
    shape: str = SINGLETON
    type_: type = str
    schema: object = None
    sub_fields: list = dataclass_field(default_factory=list)


def is_scalar_field(field):
    return (
        field.shape == SINGLETON
        and not issubclass(field.type_, BaseModel)
        and not issubclass(field.type_, SEQUENCE_TYPES)
        and not isinstance(field.schema, Body)
    )
