import unittest

from field_classifier import Field, is_scalar_field


class SourcePydanticHiddenRepresentationTest(unittest.TestCase):
    def test_union_with_sequence_subfield_is_not_scalar(self):
        union = Field(type_=object, sub_fields=[Field(type_=str), Field(type_=list)])
        self.assertFalse(is_scalar_field(union))

    def test_union_of_scalar_subfields_remains_scalar(self):
        union = Field(type_=object, sub_fields=[Field(type_=str), Field(type_=int)])
        self.assertTrue(is_scalar_field(union))


if __name__ == "__main__":
    unittest.main()
