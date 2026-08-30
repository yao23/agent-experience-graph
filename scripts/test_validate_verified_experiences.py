#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("validate_verified_experiences.py")
SPEC = importlib.util.spec_from_file_location("aeg_experience_validator", SCRIPT_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
LIBRARY_PATH = SCRIPT_PATH.parents[1] / "experiences" / "registry.json"


class VerifiedExperienceSemanticTest(unittest.TestCase):
    def setUp(self):
        self.library = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))

    def test_verified_library_passes(self):
        schema_result = VALIDATOR.validate_json_schema(self.library)
        self.assertEqual(schema_result["status"], "passed")
        result = VALIDATOR.validate_library(self.library)
        self.assertEqual(result, {"status": "passed", "experienceCount": 2, "uniqueIds": 2})
        VALIDATOR.validate_evidence_files(self.library)

    def test_missing_evidence_file_fails(self):
        missing = "experiences/missing-result.json"
        self.library[1]["provenance"]["experimentEvidence"]["artifact"] = missing
        self.library[1]["verification"]["evidence"]["experimentArtifact"] = missing
        VALIDATOR.validate_library(self.library)
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "does not resolve to a file"):
            VALIDATOR.validate_evidence_files(self.library)

    def test_duplicate_ids_fail(self):
        self.library.append(dict(self.library[0]))
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate experience ID"):
            VALIDATOR.validate_library(self.library)

    def test_duplicate_slugs_fail(self):
        duplicate = json.loads(json.dumps(self.library[1]))
        duplicate["id"] = "trace-2026-08-03-another-record"
        self.library.append(duplicate)
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate experience slug"):
            VALIDATOR.validate_library(self.library)

    def test_invalid_registry_state_fails(self):
        self.library[0]["verification_status"] = "VERIFIED"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "verification_status"):
            VALIDATOR.validate_library(self.library)

    def test_unknown_metric_must_be_null(self):
        self.library[1]["registry_metrics"]["tokens"]["value"] = 0
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "must be null"):
            VALIDATOR.validate_library(self.library)

    def test_registry_url_must_be_safe_https(self):
        self.library[0]["context"]["repository"] = "javascript:alert(1)"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "absolute HTTPS URL"):
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
