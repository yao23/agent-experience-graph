#!/usr/bin/env python3
"""Tests for the frozen natural-transfer benchmark controller."""

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("natural_transfer_runner", HERE / "run_benchmark.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def git(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = runner.load_manifest()

    def test_frozen_manifest_and_orders_validate(self):
        result = runner.validate_manifest(self.manifest)
        self.assertEqual(result["tasks"], 5)
        self.assertEqual(result["injected"], 4)
        self.assertEqual(result["abstained"], 1)

    def test_randomized_orders_are_reproducible(self):
        stored = [order for task in self.manifest["tasks"] for order in task["orders"]]
        self.assertEqual(stored, runner.expected_orders(self.manifest))
        self.assertIn(["control", "treatment"], stored)
        self.assertIn(["treatment", "control"], stored)

    def test_gate_is_mechanical_and_abstention_has_no_capsule(self):
        abstention = next(task for task in self.manifest["tasks"] if task["gate"]["decision"] == "abstain")
        self.assertEqual(runner.gate_decision(self.manifest, abstention), "abstain")
        self.assertEqual(
            runner.arm_prompt(self.manifest, abstention, "control"),
            runner.arm_prompt(self.manifest, abstention, "treatment"),
        )
        injected = next(task for task in self.manifest["tasks"] if task["gate"]["decision"] == "inject")
        self.assertNotIn(runner.render_capsule(injected), runner.arm_prompt(self.manifest, injected, "control"))
        self.assertIn(runner.render_capsule(injected), runner.arm_prompt(self.manifest, injected, "treatment"))

    def test_chronology_mutation_is_rejected(self):
        changed = copy.deepcopy(self.manifest)
        changed["tasks"][0]["source"]["fixedAt"] = changed["tasks"][0]["transfer"]["fixedAt"]
        with self.assertRaises(runner.ProtocolError):
            runner.validate_manifest(changed)

    def test_semantic_similarity_is_deterministic(self):
        human = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@ def value\n-return 1\n+return 2\n"
        exact = runner.semantic_similarity(human, human)
        empty = runner.semantic_similarity("", human)
        self.assertEqual(exact["weightedScore"], 1.0)
        self.assertLess(empty["weightedScore"], exact["weightedScore"])

    def test_seed_contains_buggy_code_fixed_test_and_one_commit(self):
        with tempfile.TemporaryDirectory(prefix="aeg-seed-test-") as raw:
            root = Path(raw)
            mirror = root / "mirror"
            mirror.mkdir()
            git(mirror, "init", "-q")
            (mirror / "bug.py").write_text("def value():\n    return 1\n", encoding="utf-8")
            (mirror / "test_bug.py").write_text("assert True\n", encoding="utf-8")
            git(mirror, "add", ".")
            git(mirror, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "buggy")
            buggy = git(mirror, "rev-parse", "HEAD")
            (mirror / "bug.py").write_text("def value():\n    return 2\n", encoding="utf-8")
            (mirror / "test_bug.py").write_text("from bug import value\nassert value() == 2\n", encoding="utf-8")
            git(mirror, "add", ".")
            git(mirror, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "fixed")
            fixed = git(mirror, "rev-parse", "HEAD")

            task = copy.deepcopy(self.manifest["tasks"][0])
            task["transfer"]["buggyCommit"] = buggy
            task["transfer"]["fixedCommit"] = fixed
            task["transfer"]["testFiles"] = ["test_bug.py"]
            task["transfer"].pop("expectedSeedTreeSha256", None)
            seeds = root / "seeds"
            seeds.mkdir()
            prepared = runner.prepare_seed(self.manifest, task, mirror, seeds, check_oracle=False)
            seed = Path(prepared["path"])
            self.assertIn("return 1", (seed / "bug.py").read_text())
            self.assertIn("value() == 2", (seed / "test_bug.py").read_text())
            self.assertEqual(git(seed, "rev-list", "--all", "--count"), "1")
            self.assertEqual(git(seed, "remote"), "")

    def test_self_test_passes(self):
        self.assertEqual(runner.self_test(self.manifest)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
