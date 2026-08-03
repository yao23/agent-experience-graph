#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("validate_verified_experiences.py")
SPEC = importlib.util.spec_from_file_location("aeg_experience_validator", SCRIPT_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
LIBRARY_PATH = SCRIPT_PATH.parents[1] / "experiences" / "verified.json"


class VerifiedExperienceSemanticTest(unittest.TestCase):
    def setUp(self):
        self.library = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))

    def test_verified_library_passes(self):
        result = VALIDATOR.validate_library(self.library)
        self.assertEqual(result, {"status": "passed", "experienceCount": 1, "uniqueIds": 1})

    def test_duplicate_ids_fail(self):
        self.library.append(dict(self.library[0]))
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate experience ID"):
            VALIDATOR.validate_library(self.library)

    def test_regression_requires_limitation(self):
        self.library[0]["limitations"] = ["One task family only."]
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duration regression"):
            VALIDATOR.validate_library(self.library)

    def test_raw_prompt_field_fails(self):
        self.library[0]["rawPrompt"] = "not publishable"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "forbidden public field"):
            VALIDATOR.validate_library(self.library)

    def test_private_workspace_path_fails(self):
        self.library[0]["lessons"].append("Read /Users/example/private/report.json")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "private workspace path"):
            VALIDATOR.validate_library(self.library)


if __name__ == "__main__":
    unittest.main()
