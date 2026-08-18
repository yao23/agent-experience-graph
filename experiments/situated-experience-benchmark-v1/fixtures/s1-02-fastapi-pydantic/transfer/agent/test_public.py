import unittest

from form_extractor import Field, FormData, request_body_to_args


class ConcreteSequenceFormTest(unittest.TestCase):
    def test_builtin_list_receives_all_submitted_values(self):
        form = FormData([("items", "first"), ("items", "second"), ("items", "third")])
        field = Field(alias="items", shape="singleton", type_=list)
        self.assertEqual(
            request_body_to_args([field], form)["items"],
            ["first", "second", "third"],
        )


if __name__ == "__main__":
    unittest.main()
