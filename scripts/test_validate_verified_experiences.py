#!/usr/bin/env python3
import importlib.util
import json
import tempfile
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

    def test_repository_reference_confinement_and_symlink_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            repository_root = temporary_root / "repository"
            repository_root.mkdir()
            regular_file = repository_root / "evidence.json"
            regular_file.write_text("{}\n", encoding="utf-8")
            outside_file = temporary_root / "outside.json"
            outside_file.write_text("{}\n", encoding="utf-8")
            inside_link = repository_root / "inside-link.json"
            outside_link = repository_root / "outside-link.json"
            dangling_link = repository_root / "dangling-link.json"
            try:
                inside_link.symlink_to(regular_file)
                outside_link.symlink_to(outside_file)
                dangling_link.symlink_to(repository_root / "missing-target.json")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            VALIDATOR.validate_repository_reference("evidence.json", "regular", repository_root)
            VALIDATOR.validate_repository_reference("inside-link.json", "inside-link", repository_root)

            for value, label in (
                ("missing.json", "missing"),
                (str(regular_file.resolve()), "absolute"),
                ("../outside.json", "parent traversal"),
                ("outside-link.json", "outside-link"),
                ("dangling-link.json", "dangling-link"),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(VALIDATOR.ValidationError):
                        VALIDATOR.validate_repository_reference(value, label, repository_root)


if __name__ == "__main__":
    unittest.main()
