#!/usr/bin/env python3
"""Tests for the public evidence-path confinement replay driver."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
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


def invoke_json_main():
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = REPLAY.main(["--json"])
    return exit_code, json.loads(stdout.getvalue())


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
        self.assertEqual(set(report["source_identity"]["runtime_observed"]), {"baseline", "fixed"})
        historical = report["source_identity"]["historical_provenance_only"]["original_target"]
        self.assertFalse(historical["runtime_required"])
        self.assertFalse(historical["verified_this_run"])
        self.assertFalse(historical["loaded_this_run"])
        self.assertFalse(historical["executed_this_run"])

    def test_absent_pinned_source_history_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = REPLAY.build_report(Path(temporary))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("PINNED_HISTORY_UNAVAILABLE", report["reason_codes"])
        self.assertFalse(report["summary"]["all_essential_checks_executed"])
        self.assertEqual(report["summary"]["executed_case_count"], 0)

    def test_each_missing_required_runtime_source_is_non_pass(self):
        real_source_identity = REPLAY._source_identity
        for missing_label in ("baseline", "fixed"):
            with self.subTest(missing_label=missing_label):
                def fail_selected_source(repo_root, label, expected, selected=missing_label):
                    if label == selected:
                        raise REPLAY.ReplayBlocked(
                            "PINNED_HISTORY_UNAVAILABLE",
                            f"injected missing {selected} source",
                        )
                    return real_source_identity(repo_root, label, expected)

                with mock.patch.object(REPLAY, "_source_identity", side_effect=fail_selected_source):
                    exit_code, report = invoke_json_main()
                self.assertEqual(exit_code, 2)
                self.assertEqual(report["status"], "BLOCKED")
                self.assertIn("PINNED_HISTORY_UNAVAILABLE", report["reason_codes"])
                self.assertFalse(report["summary"]["all_essential_checks_executed"])

    def test_required_source_identity_mismatch_is_non_pass(self):
        mismatched_baseline = json.loads(json.dumps(REPLAY.BASELINE))
        mismatched_baseline["sources"][REPLAY.VALIDATOR_PATH]["sha256"] = "0" * 64
        with mock.patch.object(REPLAY, "BASELINE", mismatched_baseline):
            exit_code, report = invoke_json_main()
        self.assertEqual(exit_code, 2)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("PROVENANCE_MISMATCH", report["reason_codes"])
        self.assertFalse(report["summary"]["all_essential_checks_executed"])

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
        self.assertEqual(case["source"]["runtime_required_sources"], ["baseline", "published_fix"])
        self.assertEqual(case["source"]["baseline"]["commit"], REPLAY.BASELINE["commit"])
        self.assertEqual(case["source"]["published_fix"]["commit"], REPLAY.FIXED["commit"])
        historical = case["source"]["original_target"]
        self.assertEqual(historical["role"], "HISTORICAL_PROVENANCE_ONLY")
        self.assertFalse(historical["runtime_required"])
        self.assertFalse(historical["verified_by_replay"])
        self.assertFalse(historical["loaded_by_replay"])
        self.assertFalse(historical["executed_by_replay"])

    def test_single_branch_clone_without_original_target_is_portable(self):
        branch = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "branch", "--show-current"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        self.assertTrue(branch)
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            clone = temporary_path / "repository"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-local",
                    "--no-tags",
                    "--single-branch",
                    "--branch",
                    branch,
                    str(REPO_ROOT),
                    str(clone),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            clone_case = clone / "examples" / "evidence-path-confinement"
            clone_case.mkdir(parents=True, exist_ok=True)
            for name in ("README.md", "case.json", "replay.py", "test_replay.py"):
                shutil.copy2(DIRECTORY / name, clone_case / name)

            for required in (REPLAY.BASELINE["commit"], REPLAY.FIXED["commit"]):
                present = subprocess.run(
                    ["git", "-C", str(clone), "cat-file", "-e", f"{required}^{{commit}}"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(present.returncode, 0)
            historical = subprocess.run(
                ["git", "-C", str(clone), "cat-file", "-e", f"{REPLAY.ORIGINAL_TARGET['commit']}^{{commit}}"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(historical.returncode, 0)

            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [sys.executable, str(clone_case / "replay.py"), "--json"],
                cwd=clone,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["summary"]["executed_case_count"], len(REPLAY.EXPECTED_CASES))
            self.assertEqual(report["summary"]["matching_case_count"], len(REPLAY.EXPECTED_CASES))
            self.assertTrue(report["summary"]["baseline_escape_defect_observed"])
            self.assertTrue(report["summary"]["fixed_escape_rejection_observed"])
            self.assertTrue(report["summary"]["legitimate_cases_preserved"])
            self.assertEqual(set(report["source_identity"]["runtime_observed"]), {"baseline", "fixed"})
            self.assertFalse(
                report["source_identity"]["historical_provenance_only"]["original_target"]["verified_this_run"]
            )
        self.assertFalse(temporary_path.exists())

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
        self.assertEqual(set(report["source_identity"]["runtime_observed"]), {"baseline", "fixed"})
        self.assertFalse(
            report["source_identity"]["historical_provenance_only"]["original_target"]["verified_this_run"]
        )
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
