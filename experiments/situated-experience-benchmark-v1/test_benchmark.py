#!/usr/bin/env python3
"""Adversarial tests for Situated Experience Benchmark v1."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("situated_runner", HERE / "run_benchmark.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class SituatedBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = runner.load_json(runner.MANIFEST)

    def package(self, root, pair_id="s1-01-scrapy-cookiejar", replicate=1, mode="control"):
        pair = runner.find_pair(self.manifest, pair_id)
        output = root / runner.arm_id(pair_id, replicate, mode)
        runner.package_arm(self.manifest, pair, replicate, mode, output)
        return pair, output

    def test_frozen_manifest_and_preflight_validate(self):
        validated = runner.validate()
        self.assertEqual(validated["accepted_pairs"], 2)
        self.assertEqual(validated["planned_arms"], 12)
        ready = runner.preflight()
        self.assertEqual(ready["human_patches_verified"], 4)
        self.assertEqual(ready["arm_bundles_audited"], 12)

    def test_source_transfer_pairs_are_natural_and_non_identical(self):
        for pair in self.manifest["pairs"]:
            self.assertLess(runner.parse_time(pair["source"]["fixed_at"]), runner.parse_time(pair["transfer"]["fixed_at"]))
            self.assertNotEqual(pair["source"]["fixed_commit"], pair["transfer"]["fixed_commit"])
            self.assertNotEqual(pair["source_human_patch_sha256"], pair["human_patch_sha256"])

    def test_control_and_assisted_bundle_separation(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-bundles-") as raw:
            root = Path(raw)
            pair, control = self.package(root, mode="control")
            _, assisted = self.package(root, mode="aeg-assisted")
            control_envelope = runner.load_json(control / "arm.json")
            assisted_envelope = runner.load_json(assisted / "arm.json")
            self.assertNotIn("experience", control_envelope)
            self.assertEqual(set(assisted_envelope["experience"]), set(runner.EXPERIENCE_FIELDS))
            serialized = json.dumps(assisted_envelope)
            self.assertNotIn(pair["transfer"]["fixed_commit"], serialized)
            self.assertNotIn(pair["human_patch_sha256"], serialized)

    def test_evaluator_and_cross_arm_artifacts_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-adversarial-") as raw:
            root = Path(raw)
            pair, bundle = self.package(root)
            hidden = bundle / "workspace" / "test_hidden.py"
            hidden.write_text("raise AssertionError('leaked evaluator')\n", encoding="utf-8")
            with self.assertRaises(runner.ProtocolError):
                runner.audit_bundle(self.manifest, pair, bundle)
        with tempfile.TemporaryDirectory(prefix="seb-test-cross-arm-") as raw:
            root = Path(raw)
            pair, bundle = self.package(root)
            (bundle / "workspace" / "prior-arm.patch").write_text("sentinel\n", encoding="utf-8")
            with self.assertRaises(runner.ProtocolError):
                runner.audit_bundle(self.manifest, pair, bundle)

    def test_treatment_payload_cannot_add_patch_fields(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-experience-") as raw:
            root = Path(raw)
            pair, bundle = self.package(root, mode="aeg-assisted")
            envelope_path = bundle / "arm.json"
            envelope = runner.load_json(envelope_path)
            envelope["experience"]["final_patch"] = "return the transfer fix"
            runner.write_json(envelope_path, envelope)
            with self.assertRaises(runner.ProtocolError):
                runner.audit_bundle(self.manifest, pair, bundle)

    def test_worker_probe_rejects_credential_environment(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-worker-") as raw:
            root = Path(raw)
            _, bundle = self.package(root)
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(root / "home"),
                "TMPDIR": str(root / "tmp"),
                "MODEL_API_KEY": "sentinel",
            }
            result = subprocess.run(
                ["python3", str(bundle / "arm_worker.py"), "probe", "--bundle", str(bundle)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("credential-shaped", result.stderr)

    def test_worker_probe_rejects_readable_sibling_arm(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-sibling-") as raw:
            root = Path(raw)
            _, bundle = self.package(root)
            (root / "other-arm").mkdir()
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(root / "home"),
                "TMPDIR": str(root / "tmp"),
                "SEB_RUNNER_ROOT": str(root),
            }
            result = subprocess.run(
                ["python3", str(bundle / "arm_worker.py"), "probe", "--bundle", str(bundle)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("other-arm", result.stderr)

    def test_mode_selector_rejects_unknown_mode(self):
        result = subprocess.run(
            ["python3", str(HERE / "run_benchmark.py"), "package-arm", "--pair", "s1-01-scrapy-cookiejar", "--replicate", "1", "--mode", "unknown", "--output", "/tmp/never-created-seb-mode"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_hidden_evaluator_marks_human_transfer_patch_regression_free(self):
        pair = runner.find_pair(self.manifest, "s1-02-fastapi-pydantic")
        with tempfile.TemporaryDirectory(prefix="seb-test-evaluator-") as raw:
            root = Path(raw)
            arm_output = root / "arm-output"
            arm_output.mkdir()
            patch = runner.fixture_root(pair) / "transfer" / "evaluator" / "human.patch"
            (arm_output / "patch.diff").write_bytes(patch.read_bytes())
            (arm_output / "events.jsonl").write_text("", encoding="utf-8")
            digest = "0" * 64
            runner.write_json(
                arm_output / "arm-result.json",
                {
                    "schema_version": "1.0.0",
                    "benchmark_id": "situated-experience-benchmark-v1",
                    "family": "S1",
                    "pair_id": pair["pair_id"],
                    "replicate": 1,
                    "mode": "control",
                    "evaluation_status": "captured",
                    "input_hashes": {"manifest": digest, "agent_fixture": digest, "task_prompt": digest},
                    "budget": self.manifest["protocol"]["budget"],
                    "regression_free_success": None,
                    "attempts": 1,
                    "completed_commands": 2,
                    "tests_run": [],
                    "files_inspected": ["form_extractor.py"],
                    "files_changed": ["form_extractor.py"],
                    "patch_size": {"added_lines": 4, "deleted_lines": 1, "files": 1},
                    "wall_time_ms": 1,
                    "tokens": {"input": None, "output": None, "unavailable_reason": "fixture"},
                    "failed_historical_paths_repeated": [],
                    "environment_assumptions_checked": [],
                    "experiences": [{"experience_id": None, "disposition": "abstained", "reason": "control"}],
                    "negative_transfer": None,
                    "evaluator_findings": ["hidden evaluation pending"],
                    "limitations": [],
                },
            )
            evaluated = runner.evaluate_arm(pair, 1, "control", arm_output, root / "evaluated.json")
            self.assertTrue(evaluated["regression_free_success"])
            self.assertEqual(evaluated["evaluation_status"], "evaluated")

    def test_schedule_contains_frozen_order_and_twelve_single_arm_bundles(self):
        with tempfile.TemporaryDirectory(prefix="seb-test-schedule-") as raw:
            output = Path(raw) / "schedule"
            plan = runner.schedule_s1(output)
            self.assertEqual(plan["arm_count"], 12)
            expected = []
            for pair in self.manifest["pairs"]:
                for replicate, order in enumerate(self.manifest["protocol"]["arm_orders"][pair["pair_id"]], 1):
                    expected.extend(runner.arm_id(pair["pair_id"], replicate, mode) for mode in order)
            self.assertEqual([arm["arm_id"] for arm in plan["arms"]], expected)


if __name__ == "__main__":
    unittest.main()
