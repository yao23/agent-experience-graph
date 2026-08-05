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
TRANSFER_RESULTS_PATH = VALIDATOR_PATH.with_name("results") / "tr-04-protocol-transfer-pair.json"


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

    def test_validates_transfer_pair_and_detailed_token_reconciliation(self):
        transfer = json.loads(TRANSFER_RESULTS_PATH.read_text(encoding="utf-8"))
        aggregate = VALIDATOR.validate_results(transfer)
        self.assertEqual(aggregate["verifiedCounts"], {"baseline": 1, "assisted": 1})
        transfer["trials"][0]["arms"]["assisted"]["tokenUsage"]["totalNonCachedTokens"] += 1
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "total non-cached tokens do not reconcile"):
            VALIDATOR.validate_results(transfer)

    def test_allows_pre_registered_semantically_equivalent_patches(self):
        transfer = json.loads(TRANSFER_RESULTS_PATH.read_text(encoding="utf-8"))
        transfer["allowSemanticallyEquivalentPatches"] = True
        transfer["trials"][0]["arms"]["assisted"]["patchSha256"] = "0" * 64
        VALIDATOR.validate_results(transfer)

    def test_rejects_incorrect_pre_registered_positive_classification(self):
        result = json.loads((VALIDATOR_PATH.with_name("results") / "tr-04-failed-path-prevention-pair.json").read_text(encoding="utf-8"))
        result["interpretation"]["preRegisteredPositive"] = True
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "positive classification"):
            VALIDATOR.validate_results(result)


if __name__ == "__main__":
    unittest.main()
