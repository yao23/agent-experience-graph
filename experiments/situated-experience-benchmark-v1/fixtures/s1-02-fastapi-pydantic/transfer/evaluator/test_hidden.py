import unittest

from form_extractor import Field, FormData, request_body_to_args


class ConcreteSequenceFormHiddenTest(unittest.TestCase):
    def setUp(self):
        self.form = FormData(
            [("items", "first"), ("items", "second"), ("name", "Ada")]
        )

    def test_other_concrete_sequence_types_receive_all_values(self):
        for concrete in (set, tuple):
            with self.subTest(concrete=concrete.__name__):
                field = Field(alias="items", shape="singleton", type_=concrete)
                self.assertEqual(
                    request_body_to_args([field], self.form)["items"],
                    ["first", "second"],
                )

    def test_typing_shape_and_scalar_paths_remain_valid(self):
        shaped = Field(alias="items", shape="list-shape", type_=str)
        scalar = Field(alias="name", shape="singleton", type_=str)
        self.assertEqual(
            request_body_to_args([shaped, scalar], self.form),
            {"items": ["first", "second"], "name": "Ada"},
        )


if __name__ == "__main__":
    unittest.main()
