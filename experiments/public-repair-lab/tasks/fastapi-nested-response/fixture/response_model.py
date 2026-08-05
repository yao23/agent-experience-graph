"""Dependency-free reproduction of FastAPI issue #889.

FastAPI and this adapted fixture are MIT licensed. See ../SOURCE.md.
"""


class ModelSchema:
    def __init__(self, name, fields=None, parent=None):
        self.name = name
        self.fields = fields or {}
        self.parent = parent

    def is_subclass_of(self, other):
        current = self
        while current is not None:
            if current is other:
                return True
            current = current.parent
        return False


class ModelValue:
    def __init__(self, schema, **values):
        self.schema = schema
        self.values = values


class ModelField:
    def __init__(self, name, model_schema=None):
        self.name = name
        self.model_schema = model_schema


def create_cloned_field(field):
    """Clone a response field so input model inheritance cannot bypass filtering."""
    original_schema = field.model_schema
    cloned_schema = original_schema
    if original_schema is not None:
        cloned_schema = ModelSchema(original_schema.name)
        for name, nested_field in original_schema.fields.items():
            cloned_schema.fields[name] = nested_field
    return ModelField(field.name, cloned_schema)


def _validate_model(expected_schema, value):
    # Matching model instances are already validated. This optimization is safe
    # for request data, but a response field clone must not retain inheritance
    # relationships that allow a more-specific object to keep extra fields.
    if value.schema.is_subclass_of(expected_schema):
        return dict(value.values)

    filtered = {}
    for name, field in expected_schema.fields.items():
        if name not in value.values:
            continue
        field_value = value.values[name]
        if field.model_schema is None:
            filtered[name] = field_value
        else:
            filtered[name] = _validate_model(field.model_schema, field_value)
    return filtered


def serialize_response(response_field, value):
    safe_field = create_cloned_field(response_field)
    return _validate_model(safe_field.model_schema, value)
