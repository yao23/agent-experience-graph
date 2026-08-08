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

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from lab import Lab, canonical_hash  # noqa: E402


SOURCE_LAB = Path(__file__).resolve().parents[2]
SOURCE_REPO = SOURCE_LAB.parent
RECOVERY_ID = "repository-state-recovery-01"
EXTERNAL_ID = "external-action-escalation-01"
RECOVERY_DIR = "autonomous-lab/experiments/shakedown/repository-state-recovery-01"
EXTERNAL_DIR = "autonomous-lab/experiments/shakedown/external-action-escalation-01"
VERIFIED_HASH = hashlib.sha256((SOURCE_REPO / "experiences" / "verified.json").read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class ShakedownIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.root = self.repo / "autonomous-lab"
        shutil.copytree(SOURCE_LAB, self.root)
        for batch in ("self-consumption-batch-01", "self-consumption-batch-02"):
            path = self.repo / "dogfood" / batch
            path.mkdir(parents=True)
            decision = "batch-01-decision.md" if batch.endswith("01") else "batch-02-decision.md"
            (path / decision).write_text("tracked historical dependency\n", encoding="utf-8")
        experiences = self.repo / "experiences"
        experiences.mkdir()
        shutil.copy2(SOURCE_REPO / "experiences" / "verified.json", experiences / "verified.json")
        self.script = self.root / "scripts" / "lab.py"
        self.clean_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPYCACHEPREFIX": str(Path(self.temp.name) / "pycache")}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(self.script), "--root", str(self.root), *args],
            cwd=self.repo,
            env=self.clean_env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout) if result.stdout.strip().startswith("{") else {"output": result.stdout}

    def reset_fixture(self, current_id: str) -> None:
        registry_path = self.root / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text())
        registry["current_experiment_id"] = current_id
        for entry in registry["experiments"]:
            if entry["experiment_id"] in {RECOVERY_ID, EXTERNAL_ID}:
                entry["state"] = "proposed"
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

        ledger_path = self.root / "ledger" / "events.jsonl"
        events = [json.loads(line) for line in ledger_path.read_text().splitlines()][:3]
        ledger_path.write_text("".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events), encoding="utf-8")

        recovery = self.root / "experiments" / "shakedown" / "repository-state-recovery-01"
        recovery_state = {
            "schema_version": 1,
            "experiment_id": RECOVERY_ID,
            "state": "proposed",
            "milestone": "fixture created; awaiting deterministic screening",
            "blocker": None,
            "updated_at": "2026-08-08T03:30:00Z",
            "budget_used": {"iterations": 0, "commands": 0, "tests": 0, "model_calls": 0, "wall_minutes": 0, "tokens": 0, "cost_usd": 0},
            "retry_count": 0,
            "approvals": {key: "not_required" for key in (
                "begin_experiment", "model_or_agent_execution", "paid_execution", "external_project_write",
                "contact_external_user", "open_or_merge_pull_request", "candidate_promotion",
                "verified_library_change", "release_publication", "secret_creation_or_use"
            )},
            "ledger_event_count": 1,
            "ledger_head_sha256": events[1]["event_sha256"],
            "verified_library_sha256": VERIFIED_HASH,
        }
        write_json(recovery / "state.json", recovery_state)
        write_json(
            recovery / "scorecard.json",
            {"schema_version": 1, "experiment_id": RECOVERY_ID, "status": "not_started", "comparison_pairs": 0,
             "acceptance_results": [], "metrics": {"precondition_failed_as_expected": None, "postcondition_passed": None, "model_calls": 0, "cost_usd": 0},
             "decision": "pending", "limitations": ["Local orchestration fixture only; no AEG effectiveness or commercial inference is permitted."]},
        )

        external = self.root / "experiments" / "shakedown" / "external-action-escalation-01"
        external_state = {
            "schema_version": 1,
            "experiment_id": EXTERNAL_ID,
            "state": "proposed",
            "milestone": "inert request fixture created; awaiting local screening",
            "blocker": None,
            "updated_at": "2026-08-08T03:31:00Z",
            "budget_used": {"iterations": 0, "commands": 0, "tests": 0, "model_calls": 0, "wall_minutes": 0, "tokens": 0, "cost_usd": 0},
            "retry_count": 0,
            "approvals": {
                "begin_experiment": "not_required", "model_or_agent_execution": "not_required", "paid_execution": "not_required",
                "external_project_write": "pending", "contact_external_user": "pending", "open_or_merge_pull_request": "pending",
                "candidate_promotion": "pending", "verified_library_change": "pending", "release_publication": "pending", "secret_creation_or_use": "pending",
            },
            "ledger_event_count": 1,
            "ledger_head_sha256": events[2]["event_sha256"],
            "verified_library_sha256": VERIFIED_HASH,
        }
        write_json(external / "state.json", external_state)
        write_json(
            external / "scorecard.json",
            {"schema_version": 1, "experiment_id": EXTERNAL_ID, "status": "not_started", "comparison_pairs": 0,
             "acceptance_results": [], "metrics": {"external_requests_detected": 0, "external_writes": 0, "model_calls": 0, "cost_usd": 0},
             "decision": "pending", "limitations": ["Safety fixture only; it provides no AEG effectiveness or commercial evidence."]},
        )
        escalation = json.loads((external / "escalation.json").read_text())
        escalation.update({"created_at": "2026-08-08T03:30:00Z", "status": "resolved", "summary": "Escalation fixture has not yet reached its external-action request.",
                           "evidence": ["external-action-request.json is inert and unauthorized."], "requested_decision": "No decision required before screening.",
                           "allowed_resolutions": ["continue to local gate evaluation"], "tradeoffs": ["Continuing evaluates the gate locally and performs no external action."],
                           "recommended_choice": "Continue only to the local gate evaluation.", "resolved_at": "2026-08-08T03:30:00Z", "resolution": "fixture initialized"})
        write_json(external / "escalation.json", escalation)

        generated = [
            "screening-result.json", "preregistration.json", "readiness-result.json", "normalized-artifact.json",
            "run-record.json", "acceptance-results.json",
        ]
        for name in generated:
            (recovery / name).unlink(missing_ok=True)
        (external / "screening-result.json").unlink(missing_ok=True)

    def test_full_lifecycle_uses_fresh_processes_and_is_terminal_idempotent(self) -> None:
        self.reset_fixture(RECOVERY_ID)
        timestamps = [f"2026-08-08T04:0{minute}:00Z" for minute in range(1, 7)]
        expected = ["screening", "preregistered", "ready", "running", "evaluating", "completed"]
        for timestamp, next_state in zip(timestamps, expected):
            self.run_cli("validate")
            self.run_cli("status")
            self.run_cli("next")
            result = self.run_cli("run-one-step", "--timestamp", timestamp)
            self.assertEqual(result["state"], next_state)
        state_path = self.root / "experiments" / "shakedown" / "repository-state-recovery-01" / "state.json"
        ledger_path = self.root / "ledger" / "events.jsonl"
        artifact_path = state_path.parent / "normalized-artifact.json"
        before = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in (state_path, ledger_path, artifact_path))
        stable = self.run_cli("run-one-step", "--timestamp", "2026-08-08T04:07:00Z")
        after = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in (state_path, ledger_path, artifact_path))
        self.assertEqual(stable["result"], "terminal_stable")
        self.assertEqual(before, after)
        self.assertEqual(json.loads(state_path.read_text())["budget_used"], {"iterations": 1, "commands": 6, "tests": 5, "model_calls": 0, "wall_minutes": 0, "tokens": 0, "cost_usd": 0})

    def test_external_action_is_escalated_without_network_or_substitution(self) -> None:
        self.reset_fixture(EXTERNAL_ID)
        first = self.run_cli("run-one-step", "--timestamp", "2026-08-08T05:01:00Z")
        self.assertEqual(first["state"], "screening")
        second = self.run_cli("run-one-step", "--timestamp", "2026-08-08T05:02:00Z", expected=10)
        self.assertEqual(second["state"], "escalated")
        state_path = self.root / "experiments" / "shakedown" / "external-action-escalation-01" / "state.json"
        ledger_path = self.root / "ledger" / "events.jsonl"
        before = (state_path.read_bytes(), ledger_path.read_bytes())
        third = self.run_cli("run-one-step", "--timestamp", "2026-08-08T05:03:00Z", expected=10)
        self.assertEqual(third["result"], "human_approval_required")
        self.assertEqual(before, (state_path.read_bytes(), ledger_path.read_bytes()))
        state = json.loads(state_path.read_text())
        self.assertEqual(state["budget_used"]["model_calls"], 0)
        self.assertEqual(state["budget_used"]["cost_usd"], 0)
        self.assertIn("no external action was performed", state["blocker"])
        self.assertIn("will not silently substitute", (self.root / "reports" / "next-human-action.md").read_text())

    def test_documented_budget_and_validation_exit_codes(self) -> None:
        self.reset_fixture(RECOVERY_ID)
        state_path = self.root / "experiments" / "shakedown" / "repository-state-recovery-01" / "state.json"
        state = json.loads(state_path.read_text())
        state["budget_used"]["commands"] = 10
        write_json(state_path, state)
        stopped = self.run_cli("run-one-step", "--timestamp", "2026-08-08T06:01:00Z", expected=12)
        self.assertEqual(stopped["state"], "budget_exhausted")
        self.assertEqual(json.loads(state_path.read_text())["state"], "budget_exhausted")
        verified = self.repo / "experiences" / "verified.json"
        verified.write_text(verified.read_text() + " ", encoding="utf-8")
        self.run_cli("validate", expected=11)

    def test_tracked_state_reconstructs_in_clean_repository(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "autonomous-lab", "experiences/verified.json", "dogfood/self-consumption-batch-01/batch-01-decision.md", "dogfood/self-consumption-batch-02/batch-02-decision.md"],
            cwd=SOURCE_REPO, text=True, capture_output=True, check=True,
        ).stdout.splitlines()
        self.assertTrue(any(path.endswith("normalized-artifact.json") for path in tracked), "shakedown evidence must be tracked before this test runs")
        clean_repo = Path(self.temp.name) / "tracked-only"
        for relative in tracked:
            destination = clean_repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_REPO / relative, destination)
        subprocess.run(["git", "init", "-q"], cwd=clean_repo, check=True)
        subprocess.run(["git", "add", "."], cwd=clean_repo, check=True)
        clean_root = clean_repo / "autonomous-lab"
        clean_script = clean_root / "scripts" / "lab.py"
        command = [sys.executable, str(clean_script), "--root", str(clean_root)]
        for verb in ("validate", "status", "next"):
            result = subprocess.run([*command, verb], cwd=clean_repo, env=self.clean_env, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        expected_reports = tuple((clean_root / "reports" / name).read_text() for name in ("current-status.json", "current-status.md", "next-human-action.md"))
        result = subprocess.run([*command, "report"], cwd=clean_repo, env=self.clean_env, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual_reports = tuple((clean_root / "reports" / name).read_text() for name in ("current-status.json", "current-status.md", "next-human-action.md"))
        self.assertEqual(expected_reports, actual_reports)
        lab = Lab(clean_root)
        lab.validate()
        state = json.loads((clean_root / "experiments" / "shakedown" / "external-action-escalation-01" / "state.json").read_text())
        events = [json.loads(line) for line in (clean_root / "ledger" / "events.jsonl").read_text().splitlines()]
        current_events = [event for event in events if event["experiment_id"] == EXTERNAL_ID]
        self.assertEqual(state["ledger_head_sha256"], current_events[-1]["event_sha256"])
        report = json.loads((clean_root / "reports" / "current-status.json").read_text())
        self.assertEqual(report["current_experiment"]["artifact_sha256"], current_events[-1]["artifact_sha256"])
        all_text = "\n".join(path.read_text(errors="ignore") for path in clean_root.rglob("*") if path.is_file())
        self.assertNotIn("agent-experience-graph-" + "self-consumption-batch", all_text)
        self.assertNotIn("/" + "Users" + "/", all_text)


if __name__ == "__main__":
    unittest.main()
