#!/usr/bin/env python3
import unittest

from response_model import ModelField, ModelSchema, ModelValue, serialize_response


class NestedResponseFilteringTest(unittest.TestCase):
    def test_nested_subclass_does_not_leak_extra_fields(self):
        public_user = ModelSchema("PublicUser", {"username": ModelField("username")})
        private_user = ModelSchema(
            "PrivateUser",
            {
                "username": ModelField("username"),
                "password": ModelField("password"),
            },
            parent=public_user,
        )
        envelope = ModelSchema(
            "Envelope",
            {
                "name": ModelField("name"),
                "user": ModelField("user", public_user),
            },
        )
        response_field = ModelField("response", envelope)
        value = ModelValue(
            envelope,
            name="example",
            internal_request_id="req-secret",
            user=ModelValue(
                private_user,
                username="alice",
                password="correct horse battery staple",
            ),
        )

        self.assertEqual(
            serialize_response(response_field, value),
            {"name": "example", "user": {"username": "alice"}},
        )


if __name__ == "__main__":
    unittest.main()
