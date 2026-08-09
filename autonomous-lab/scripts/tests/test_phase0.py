from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab import EXIT_APPROVAL_REQUIRED, EXIT_BUDGET_EXHAUSTED, Lab, LabValidationError  # noqa: E402
from phase0_fixture import prepare_preregistered_phase0  # noqa: E402


SOURCE_LAB = Path(__file__).resolve().parents[2]
SOURCE_REPO = SOURCE_LAB.parent
EXPERIMENT = "aeg-assisted-agent-failure-recovery-service-v0"


class Phase0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.root = self.repo / "autonomous-lab"
        shutil.copytree(SOURCE_LAB, self.root)
        for batch in ("self-consumption-batch-01", "self-consumption-batch-02"):
            decision = "batch-01-decision.md" if batch.endswith("01") else "batch-02-decision.md"
            path = self.repo / "dogfood" / batch
            path.mkdir(parents=True)
            (path / decision).write_text("historical evidence fixture\n", encoding="utf-8")
        (self.repo / "experiences").mkdir()
        shutil.copy2(SOURCE_REPO / "experiences" / "verified.json", self.repo / "experiences" / "verified.json")
        prepare_preregistered_phase0(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def lab(self) -> Lab:
        return Lab(self.root)

    def test_activation_is_phase0_only_and_zero_budget(self) -> None:
        result = self.lab().validate()
        entry, _, state, _, _ = self.lab().records(EXPERIMENT)
        self.assertEqual(result["state"], "preregistered")
        self.assertEqual(entry["approved_phase"], "phase0_preparation")
        self.assertEqual(state["phase_run_count"], 0)
        self.assertTrue(all(value == 0 for value in state["budget_used"].values()))
        for action in ("external_write", "promotion", "verified_library_change", "release", "paid_execution"):
            self.assertNotEqual(self.lab().approval_decision(action, EXPERIMENT)["kind"], "permitted")

    def test_approval_hash_tampering_fails_closed(self) -> None:
        entry = self.lab().current_entry(EXPERIMENT)
        path = self.lab().resolve(entry["approval_record_path"])
        record = json.loads(path.read_text())
        record["limits"]["external_writes"] = 1
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(LabValidationError, "approval event hash"):
            self.lab().validate()

    def test_four_runs_make_one_transition_each_then_require_phase1_approval(self) -> None:
        expected = ("ready", "running", "evaluating", "completed")
        before_events = self.lab().status(EXPERIMENT)["ledger_event_count"]
        for index, state_name in enumerate(expected, 1):
            code, result = self.lab().run_one_step(EXPERIMENT, f"2026-08-08T05:0{index}:00Z")
            self.assertEqual(result["state"], state_name)
            self.assertEqual(result["transition"].split("->")[1], state_name)
            self.assertEqual(code, EXIT_APPROVAL_REQUIRED if state_name == "completed" else 0)
            self.assertEqual(self.lab().status(EXPERIMENT)["ledger_event_count"], before_events + index)
            self.lab().validate()
        entry, _, state, _, escalation = self.lab().records(EXPERIMENT)
        self.assertFalse(entry["scheduler_eligible"])
        self.assertEqual(entry["operational_status"], "disabled")
        self.assertEqual(state["phase_run_count"], 4)
        self.assertEqual(state["budget_used"]["model_calls"], 4)
        self.assertEqual(escalation["status"], "open")
        self.assertEqual(escalation["requested_decision"], "whether to begin Phase 1 seed-user recruitment")
        self.assertEqual(self.lab().next_action(EXPERIMENT)["kind"], "human_approval")
        self.lab().report()
        next_human = (self.root / "reports" / "next-human-action.md").read_text()
        self.assertIn("whether to begin Phase 1 seed-user recruitment", next_human)
        self.assertNotIn("AEG improves repairs", next_human)

    def test_eight_run_limit_stops_before_another_phase0_transition(self) -> None:
        entry = self.lab().current_entry(EXPERIMENT)
        state_path = self.lab().resolve(entry["state_path"])
        state = json.loads(state_path.read_text())
        state["phase_run_count"] = 8
        state["budget_used"]["iterations"] = 8
        state["budget_used"]["model_calls"] = 8
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        code, result = self.lab().run_one_step(EXPERIMENT, "2026-08-08T06:00:00Z")
        self.assertEqual(code, EXIT_BUDGET_EXHAUSTED)
        self.assertEqual(result["state"], "budget_exhausted")


class Phase0ScheduledPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.root = self.repo / "autonomous-lab"
        shutil.copytree(SOURCE_LAB, self.root)
        for batch in ("self-consumption-batch-01", "self-consumption-batch-02"):
            decision = "batch-01-decision.md" if batch.endswith("01") else "batch-02-decision.md"
            path = self.repo / "dogfood" / batch
            path.mkdir(parents=True)
            (path / decision).write_text("historical evidence fixture\n", encoding="utf-8")
        (self.repo / "experiences").mkdir()
        shutil.copy2(
            SOURCE_REPO / "experiences" / "verified.json",
            self.repo / "experiences" / "verified.json",
        )
        prepare_preregistered_phase0(self.root)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "scheduler-test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Scheduler Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "phase0 fixture"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "--unset", "user.email"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "--unset", "user.name"], cwd=self.repo, check=True)
        self.script = self.root / "scripts" / "lab.py"
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPYCACHEPREFIX": str(Path(self.temp.name) / "pycache"),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_four_independent_scheduled_runs_commit_only_transition_outputs(self) -> None:
        verified_path = self.repo / "experiences" / "verified.json"
        verified_before = verified_path.read_bytes()
        entry = Lab(self.root).current_entry(EXPERIMENT)
        business_hashes = {
            path: hashlib.sha256((self.repo / path).read_bytes()).hexdigest()
            for path in entry["phase0_artifact_paths"]
            if not path.endswith("phase0-scorecard.json")
        }
        ledger_path = self.root / "ledger" / "events.jsonl"
        prior_lines = ledger_path.read_text().splitlines()
        initial_commit_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"], cwd=self.repo,
                text=True, capture_output=True, check=True,
            ).stdout
        )
        expected_states = ("ready", "running", "evaluating", "completed")
        expected_codes = (0, 0, 0, EXIT_APPROVAL_REQUIRED)
        experiment_dir = "autonomous-lab/experiments/proposed/aeg-assisted-agent-failure-recovery-service"
        common_paths = {
            "autonomous-lab/experiments/registry.yaml",
            "autonomous-lab/ledger/events.jsonl",
            "autonomous-lab/reports/current-status.json",
            "autonomous-lab/reports/current-status.md",
            "autonomous-lab/reports/next-human-action.md",
            f"{experiment_dir}/state.json",
            f"{experiment_dir}/phase0-validation.json",
        }
        expected_paths = {
            "ready": common_paths,
            "running": common_paths,
            "evaluating": common_paths | {f"{experiment_dir}/scorecard.json"},
            "completed": common_paths | {
                f"{experiment_dir}/scorecard.json",
                f"{experiment_dir}/phase0-scorecard.json",
                f"{experiment_dir}/escalation.json",
            },
        }
        for index, (state_name, expected_code) in enumerate(zip(expected_states, expected_codes), 1):
            result = subprocess.run(
                [
                    sys.executable, str(self.script), "--root", str(self.root),
                    "scheduled-step", "--persist-commit",
                    "--timestamp", f"2026-08-08T09:0{index}:00Z",
                    "--run-id", f"phase0-persist-{index}",
                ],
                cwd=self.repo, env=self.env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, expected_code, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], state_name)
            self.assertEqual(payload["transition"].split("->")[1], state_name)
            self.assertFalse(payload["persistence"]["pushed"])
            self.assertEqual(set(payload["persistence"]["paths"]), expected_paths[state_name])
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
                    cwd=self.repo, text=True, capture_output=True, check=True,
                ).stdout,
                "",
            )
            current_lines = ledger_path.read_text().splitlines()
            self.assertEqual(current_lines[:len(prior_lines)], prior_lines)
            self.assertEqual(len(current_lines), len(prior_lines) + 1)
            prior_lines = current_lines
            self.assertEqual(verified_path.read_bytes(), verified_before)

        commit_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"], cwd=self.repo,
                text=True, capture_output=True, check=True,
            ).stdout
        )
        self.assertEqual(commit_count, initial_commit_count + 4)
        self.assertEqual(
            subprocess.run(
                ["git", "show", "-s", "--format=%an <%ae>", "HEAD"], cwd=self.repo,
                text=True, capture_output=True, check=True,
            ).stdout.strip(),
            "AEG Autonomous Lab <aeg-autonomous-lab@localhost.invalid>",
        )
        for path, digest in business_hashes.items():
            self.assertEqual(hashlib.sha256((self.repo / path).read_bytes()).hexdigest(), digest)
        entry, _, state, phase0_scorecard, escalation = Lab(self.root).records(EXPERIMENT)
        self.assertEqual(state["state"], "completed")
        self.assertFalse(entry["scheduler_eligible"])
        self.assertIsNone(Lab(self.root).scheduler_entry())
        self.assertEqual(escalation["status"], "open")
        self.assertEqual(phase0_scorecard["metrics"]["external_actions"], 0)
        self.assertEqual(state["verified_library_sha256"], hashlib.sha256(verified_before).hexdigest())

        committed_reports = tuple(
            (self.root / "reports" / name).read_bytes()
            for name in ("current-status.json", "current-status.md", "next-human-action.md")
        )
        Lab(self.root).report(check=True)
        ledger_after_completion = ledger_path.read_bytes()
        for index in (5, 6):
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--root",
                    str(self.root),
                    "scheduled-step",
                    "--persist-commit",
                    "--timestamp",
                    f"2026-08-08T10:0{index}:00Z",
                    "--run-id",
                    f"phase0-no-work-{index}",
                ],
                cwd=self.repo,
                env=self.env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(json.loads(result.stdout)["result"], "no_eligible_experiment")
        self.assertEqual(ledger_path.read_bytes(), ledger_after_completion)
        self.assertEqual(verified_path.read_bytes(), verified_before)
        self.assertEqual(
            committed_reports,
            tuple(
                (self.root / "reports" / name).read_bytes()
                for name in ("current-status.json", "current-status.md", "next-human-action.md")
            ),
        )


if __name__ == "__main__":
    unittest.main()
