import unittest

from field_classifier import BaseModel, Field, is_scalar_field


class Item(BaseModel):
    pass


class SourcePydanticRepresentationTest(unittest.TestCase):
    def test_union_with_model_subfield_is_not_scalar(self):
        union = Field(type_=object, sub_fields=[Field(type_=str), Field(type_=Item)])
        self.assertFalse(is_scalar_field(union))


if __name__ == "__main__":
    unittest.main()
