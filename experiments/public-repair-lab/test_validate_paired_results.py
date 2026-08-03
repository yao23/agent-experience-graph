#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path


VALIDATOR_PATH = Path(__file__).with_name("validate_paired_results.py")
SPEC = importlib.util.spec_from_file_location("aeg_paired_validator", VALIDATOR_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
RESULTS_PATH = VALIDATOR_PATH.with_name("results") / "v0.1.3-paired-results.json"


class PairedResultsValidationTest(unittest.TestCase):
    def setUp(self):
        self.results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    def assert_invalid(self, fragment):
        with self.assertRaisesRegex(VALIDATOR.ValidationError, fragment):
            VALIDATOR.validate_results(self.results)

    def test_recomputes_published_aggregate(self):
        aggregate = VALIDATOR.validate_results(self.results)
        self.assertEqual(
            aggregate["pairedMedianAssistedMinusBaseline"],
            {"completedCommands": -1, "actualTestExecutions": 0, "nonCachedTokens": -732, "durationMs": 18235},
        )
        self.assertEqual(aggregate["verifiedCounts"], {"baseline": 5, "assisted": 5})

    def test_rejects_missing_arm(self):
        del self.results["trials"][0]["arms"]["assisted"]
        self.assert_invalid("exactly baseline and assisted")

    def test_rejects_invalid_metric_type(self):
        self.results["trials"][0]["arms"]["baseline"]["completedCommands"] = "6"
        self.assert_invalid("completedCommands must be a non-negative integer")

    def test_rejects_duplicate_trial_id(self):
        self.results["trials"][1]["trialId"] = self.results["trials"][0]["trialId"]
        self.assert_invalid("duplicate trial ID")

    def test_rejects_inconsistent_patch_hash(self):
        self.results["trials"][2]["arms"]["assisted"]["patchSha256"] = "0" * 64
        self.assert_invalid("inconsistent with expectedPatchSha256")

    def test_rejects_mismatched_aggregate(self):
        self.results["aggregate"]["pairedMedianAssistedMinusBaseline"]["durationMs"] = 0
        self.assert_invalid("published aggregate does not match recomputation")

    def test_rejects_forbidden_raw_artifact_field(self):
        self.results["trials"][0]["rawPrompt"] = "not publishable"
        self.assert_invalid("forbidden public field")


if __name__ == "__main__":
    unittest.main()
