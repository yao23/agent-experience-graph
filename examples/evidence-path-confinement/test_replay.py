#!/usr/bin/env python3
"""Tests for the public evidence-path confinement replay driver."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True
DIRECTORY = Path(__file__).resolve().parent
REPO_ROOT = DIRECTORY.parents[1]
REPLAY_PATH = DIRECTORY / "replay.py"
CASE_PATH = DIRECTORY / "case.json"
SPEC = importlib.util.spec_from_file_location("evidence_path_confinement_replay", REPLAY_PATH)
REPLAY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REPLAY)


def expected_observations():
    return [
        {
            "id": item["id"],
            "kind": item["kind"],
            "display_path": item["display_path"],
            "baseline": {"decision": item["baseline"], "result_type": "synthetic-test-value"},
            "fixed": {"decision": item["fixed"], "result_type": "synthetic-test-value"},
        }
        for item in REPLAY.EXPECTED_CASES
    ]


class ReplayDriverTest(unittest.TestCase):
    def test_normal_successful_replay(self):
        report = REPLAY.build_report(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["reason_codes"], [])
        self.assertTrue(report["prerequisites"]["source_hashes_verified"])
        self.assertTrue(report["prerequisites"]["symlinks_supported"])
        self.assertTrue(report["summary"]["all_essential_checks_executed"])
        self.assertTrue(report["summary"]["baseline_escape_defect_observed"])
        self.assertTrue(report["summary"]["fixed_escape_rejection_observed"])
        self.assertTrue(report["summary"]["legitimate_cases_preserved"])
        self.assertEqual(report["summary"]["matching_case_count"], len(REPLAY.EXPECTED_CASES))
        self.assertTrue(report["temporary_artifacts_cleaned"])

    def test_absent_pinned_source_history_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = REPLAY.build_report(Path(temporary))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("PINNED_HISTORY_UNAVAILABLE", report["reason_codes"])
        self.assertFalse(report["summary"]["all_essential_checks_executed"])
        self.assertEqual(report["summary"]["executed_case_count"], 0)

    def test_unsupported_symlink_prerequisite_is_blocked(self):
        with mock.patch.object(
            REPLAY,
            "probe_symlink_support",
            return_value=(False, "symlink creation is unavailable on this platform"),
        ):
            report = REPLAY.build_report(REPO_ROOT)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("UNSUPPORTED_PREREQUISITE", report["reason_codes"])
        self.assertFalse(report["summary"]["all_essential_checks_executed"])
        self.assertTrue(report["temporary_artifacts_cleaned"])

    def test_unexpected_baseline_or_fixed_behavior_fails(self):
        for side, case_id, decision in (
            ("baseline", "direct_outside_symlink", "REJECTED"),
            ("fixed", "direct_outside_symlink", "ACCEPTED"),
        ):
            with self.subTest(side=side):
                observations = expected_observations()
                selected = next(item for item in observations if item["id"] == case_id)
                selected[side]["decision"] = decision
                with mock.patch.object(REPLAY, "run_case_matrix", return_value=observations):
                    report = REPLAY.build_report(REPO_ROOT)
                self.assertEqual(report["status"], "FAIL")
                self.assertIn("UNEXPECTED_BEHAVIOR", report["reason_codes"])
                self.assertLess(report["summary"]["matching_case_count"], len(REPLAY.EXPECTED_CASES))

    def test_missing_essential_observation_cannot_pass(self):
        observations = expected_observations()[:-1]
        with mock.patch.object(REPLAY, "run_case_matrix", return_value=observations):
            report = REPLAY.build_report(REPO_ROOT)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["summary"]["all_essential_checks_executed"])
        self.assertIn("UNEXPECTED_BEHAVIOR", report["reason_codes"])

    def test_case_description_matches_driver_expectations(self):
        case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
        described = case["replay"]["committed_expectations"]
        projected = [
            {"id": item["id"], "baseline": item["baseline"], "fixed": item["fixed"]}
            for item in REPLAY.EXPECTED_CASES
        ]
        self.assertEqual(described, projected)
        self.assertEqual(case["source"]["baseline"]["commit"], REPLAY.BASELINE["commit"])
        self.assertEqual(case["source"]["published_fix"]["commit"], REPLAY.FIXED["commit"])

    def test_machine_readable_cli_output_is_consistent_and_public_safe(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(REPLAY_PATH), "--json"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["case_id"], REPLAY.CASE_ID)
        self.assertEqual(report["case_version"], REPLAY.CASE_VERSION)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            report["summary"]["executed_case_count"],
            report["summary"]["essential_case_count"],
        )
        self.assertEqual(
            report["summary"]["matching_case_count"],
            report["summary"]["essential_case_count"],
        )
        self.assertNotIn(str(REPO_ROOT.parent), completed.stdout)
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
