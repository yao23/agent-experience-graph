"""Dependency-free extract of FastAPI's form request-body extraction path."""

from dataclasses import dataclass


SEQUENCE_SHAPES = {"list-shape", "set-shape", "tuple-shape"}
SEQUENCE_TYPES = (list, set, tuple)


class FormData:
    def __init__(self, pairs):
        self._pairs = list(pairs)

    def get(self, alias):
        values = [value for key, value in self._pairs if key == alias]
        return values[-1] if values else None

    def getlist(self, alias):
        return [value for key, value in self._pairs if key == alias]


@dataclass
class Field:
    alias: str
    shape: str
    type_: type


def request_body_to_args(required_params, received_body):
    values = {}
    for field in required_params:
        if field.shape in SEQUENCE_SHAPES and isinstance(received_body, FormData):
            value = received_body.getlist(field.alias)
        else:
            value = received_body.get(field.alias)
        values[field.alias] = value
    return values
