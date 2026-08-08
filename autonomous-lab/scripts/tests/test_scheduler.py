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

from lab import Lab  # noqa: E402
from scheduler import (  # noqa: E402
    ExecutionLease,
    LeaseHeldError,
    UnsafeWorktreeError,
    load_config,
    persist_transition_commit,
    preflight_worktree,
)


SOURCE_LAB = Path(__file__).resolve().parents[2]
SOURCE_REPO = SOURCE_LAB.parent
RECOVERY_ID = "repository-state-recovery-01"
EXTERNAL_ID = "external-action-escalation-01"
VERIFIED_HASH = hashlib.sha256((SOURCE_REPO / "experiences" / "verified.json").read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SchedulerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.root = self.repo / "autonomous-lab"
        shutil.copytree(SOURCE_LAB, self.root)
        for batch in ("self-consumption-batch-01", "self-consumption-batch-02"):
            path = self.repo / "dogfood" / batch
            path.mkdir(parents=True)
            decision = "batch-01-decision.md" if batch.endswith("01") else "batch-02-decision.md"
            (path / decision).write_text("historical fixture\n", encoding="utf-8")
        experiences = self.repo / "experiences"
        experiences.mkdir()
        shutil.copy2(SOURCE_REPO / "experiences" / "verified.json", experiences / "verified.json")
        registry_path = self.root / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text())
        registry["current_experiment_id"] = None
        commercial = next(
            item for item in registry["experiments"]
            if item["experiment_id"] == "aeg-assisted-agent-failure-recovery-service-v0"
        )
        commercial.update({"operational_status": "proposed", "scheduler_eligible": False, "state": "proposed"})
        for key in tuple(commercial):
            if key.endswith("_path") or key.endswith("_paths"):
                commercial.pop(key)
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
        Lab(self.root).report()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "scheduler-test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Scheduler Test"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True)
        self.script = self.root / "scripts" / "lab.py"
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPYCACHEPREFIX": str(Path(self.temp.name) / "pycache"),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(self.script), "--root", str(self.root), *args],
            cwd=self.repo,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        if result.stdout.strip().startswith("{"):
            return json.loads(result.stdout)
        return {"stderr": result.stderr, "stdout": result.stdout}

    def commit(self, message: str = "fixture update") -> None:
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=self.repo, check=True)

    def tracked_hash(self) -> str:
        paths = subprocess.run(
            ["git", "ls-files"], cwd=self.repo, text=True, capture_output=True, check=True
        ).stdout.splitlines()
        digest = hashlib.sha256()
        for path in paths:
            digest.update(path.encode())
            digest.update((self.repo / path).read_bytes())
        return digest.hexdigest()

    def reset_fixtures(self) -> None:
        registry_path = self.root / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text())
        registry["current_experiment_id"] = None
        for entry in registry["experiments"]:
            if entry["experiment_id"] in {RECOVERY_ID, EXTERNAL_ID}:
                entry["state"] = "proposed"
                entry["operational_status"] = "archived"
                entry["scheduler_eligible"] = False
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

        ledger_path = self.root / "ledger" / "events.jsonl"
        events = [json.loads(line) for line in ledger_path.read_text().splitlines()][:3]
        ledger_path.write_text(
            "".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events),
            encoding="utf-8",
        )
        approvals = {
            key: "not_required"
            for key in (
                "begin_experiment",
                "model_or_agent_execution",
                "paid_execution",
                "external_project_write",
                "contact_external_user",
                "open_or_merge_pull_request",
                "candidate_promotion",
                "verified_library_change",
                "release_publication",
                "secret_creation_or_use",
            )
        }
        recovery = self.root / "experiments" / "shakedown" / RECOVERY_ID
        write_json(
            recovery / "state.json",
            {
                "schema_version": 1,
                "experiment_id": RECOVERY_ID,
                "state": "proposed",
                "milestone": "fixture created; awaiting deterministic screening",
                "blocker": None,
                "updated_at": "2026-08-08T03:30:00Z",
                "budget_used": {"iterations": 0, "commands": 0, "tests": 0, "model_calls": 0, "wall_minutes": 0, "tokens": 0, "cost_usd": 0},
                "retry_count": 0,
                "approvals": approvals,
                "ledger_event_count": 1,
                "ledger_head_sha256": events[1]["event_sha256"],
                "verified_library_sha256": VERIFIED_HASH,
            },
        )
        write_json(
            recovery / "scorecard.json",
            {
                "schema_version": 1,
                "experiment_id": RECOVERY_ID,
                "status": "not_started",
                "comparison_pairs": 0,
                "acceptance_results": [],
                "metrics": {"precondition_failed_as_expected": None, "postcondition_passed": None, "model_calls": 0, "cost_usd": 0},
                "decision": "pending",
                "limitations": ["Local scheduler test fixture only."],
            },
        )
        recovery_escalation = json.loads((recovery / "escalation.json").read_text())
        recovery_escalation.update({"status": "resolved", "resolved_at": "2026-08-08T03:30:00Z", "resolution": "fixture reset"})
        write_json(recovery / "escalation.json", recovery_escalation)

        external = self.root / "experiments" / "shakedown" / EXTERNAL_ID
        external_approvals = dict(approvals)
        for key in ("external_project_write", "contact_external_user", "open_or_merge_pull_request", "candidate_promotion", "verified_library_change", "release_publication", "secret_creation_or_use"):
            external_approvals[key] = "pending"
        write_json(
            external / "state.json",
            {
                "schema_version": 1,
                "experiment_id": EXTERNAL_ID,
                "state": "proposed",
                "milestone": "inert request fixture created; awaiting local screening",
                "blocker": None,
                "updated_at": "2026-08-08T03:31:00Z",
                "budget_used": {"iterations": 0, "commands": 0, "tests": 0, "model_calls": 0, "wall_minutes": 0, "tokens": 0, "cost_usd": 0},
                "retry_count": 0,
                "approvals": external_approvals,
                "ledger_event_count": 1,
                "ledger_head_sha256": events[2]["event_sha256"],
                "verified_library_sha256": VERIFIED_HASH,
            },
        )
        write_json(
            external / "scorecard.json",
            {
                "schema_version": 1,
                "experiment_id": EXTERNAL_ID,
                "status": "not_started",
                "comparison_pairs": 0,
                "acceptance_results": [],
                "metrics": {"external_requests_detected": 0, "external_writes": 0, "model_calls": 0, "cost_usd": 0},
                "decision": "pending",
                "limitations": ["Local scheduler test fixture only."],
            },
        )
        external_escalation = json.loads((external / "escalation.json").read_text())
        external_escalation.update(
            {
                "status": "resolved",
                "summary": "Fixture reset before local screening.",
                "requested_decision": "No decision required before screening.",
                "resolved_at": "2026-08-08T03:31:00Z",
                "resolution": "fixture reset",
            }
        )
        write_json(external / "escalation.json", external_escalation)

    def make_eligible(self, experiment_id: str = RECOVERY_ID) -> None:
        self.reset_fixtures()
        registry_path = self.root / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text())
        entry = next(item for item in registry["experiments"] if item["experiment_id"] == experiment_id)
        entry["experiment_kind"] = "production"
        entry["operational_status"] = "active"
        entry["scheduler_eligible"] = True
        if experiment_id == RECOVERY_ID:
            entry["runtime_evidence_paths"] = [
                f"autonomous-lab/experiments/shakedown/{RECOVERY_ID}/{name}"
                for name in (
                    "screening-result.json",
                    "preregistration.json",
                    "readiness-result.json",
                    "normalized-artifact.json",
                    "run-record.json",
                    "acceptance-results.json",
                )
            ]
        else:
            entry["runtime_evidence_paths"] = [
                f"autonomous-lab/experiments/shakedown/{EXTERNAL_ID}/screening-result.json"
            ]
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
        self.commit("eligible fixture")

    def test_no_eligible_experiment_is_mutation_free_and_repeatable(self) -> None:
        before = self.tracked_hash()
        legacy = self.run_cli("run-one-step", "--timestamp", "2026-08-08T07:59:00Z")
        first = self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:00:00Z", "--run-id", "no-work-1")
        second = self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:01:00Z", "--run-id", "no-work-2")
        self.assertEqual(legacy["message"], "No scheduler-eligible experiment is currently approved.")
        self.assertEqual(first["message"], "No scheduler-eligible experiment is currently approved.")
        self.assertEqual(second["result"], "no_eligible_experiment")
        self.assertEqual(
            (self.root / "reports" / "next-human-action.md").read_text(),
            "# Next human action\n\nNo human action required\n",
        )
        self.assertEqual(before, self.tracked_hash())

    def test_one_eligible_safe_experiment_executes_one_step_and_reports_deterministically(self) -> None:
        self.make_eligible()
        result = self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:02:00Z", "--run-id", "safe-1")
        self.assertEqual(result["transition"], "proposed->screening")
        status = json.loads((self.root / "reports" / "current-status.json").read_text())
        self.assertEqual(status["run_id"], "safe-1")
        self.assertEqual(status["current_experiment"]["experiment_kind"], "production")
        self.assertRegex(status["current_experiment"]["state_sha256"], "^[a-f0-9]{64}$")
        self.assertIn("No human action required", (self.root / "reports" / "next-human-action.md").read_text())
        before = tuple((self.root / "reports" / name).read_bytes() for name in ("current-status.json", "current-status.md", "next-human-action.md"))
        self.run_cli("report")
        self.run_cli("report", "--check")
        after = tuple((self.root / "reports" / name).read_bytes() for name in ("current-status.json", "current-status.md", "next-human-action.md"))
        self.assertNotEqual(before, after)
        self.run_cli("report")
        stable = tuple((self.root / "reports" / name).read_bytes() for name in ("current-status.json", "current-status.md", "next-human-action.md"))
        self.assertEqual(after, stable)

    def test_multiple_eligible_experiments_return_configuration_error(self) -> None:
        self.make_eligible()
        registry_path = self.root / "experiments" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text())
        external = next(item for item in registry["experiments"] if item["experiment_id"] == EXTERNAL_ID)
        external.update({"experiment_kind": "production", "operational_status": "active", "scheduler_eligible": True})
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:03:00Z", "--run-id", "multiple", expected=15)

    def test_archived_and_unapproved_commercial_entries_are_not_selected(self) -> None:
        result = self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:04:00Z", "--run-id", "archive")
        self.assertEqual(result["experiment_id"], None)
        registry = yaml.safe_load((self.root / "experiments" / "registry.yaml").read_text())
        commercial = next(item for item in registry["experiments"] if item["experiment_kind"] == "commercial")
        self.assertEqual(commercial["operational_status"], "proposed")
        self.assertFalse(commercial["scheduler_eligible"])

    def test_concurrent_runner_is_rejected_and_stale_lease_requires_explicit_recovery(self) -> None:
        config = load_config(self.root)
        lease = ExecutionLease(self.repo, config)
        lease.acquire("holder", "2026-08-08T08:05:00Z", None, None, None, "test")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:06:00Z", "--run-id", "contender", expected=13)
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T09:00:00Z", "--run-id", "stale-detect", expected=13)
        recovered = self.run_cli("recover-stale-lease", "--timestamp", "2026-08-08T09:00:00Z", "--run-id", "recovery")
        self.assertEqual(recovered["recovered_run_id"], "holder")
        audit_path = self.repo / ".git" / "aeg-autonomous-lab" / "lease-audit.jsonl"
        events = [json.loads(line) for line in audit_path.read_text().splitlines()]
        self.assertEqual(
            [event["event_type"] for event in events],
            ["lease_acquired", "lease_rejected", "lease_stale_detected", "lease_recovered"],
        )
        previous = None
        for sequence, event in enumerate(events, 1):
            self.assertEqual(event["sequence"], sequence)
            self.assertEqual(event["previous_event_sha256"], previous)
            previous = event["event_sha256"]

    def test_execution_lease_is_shared_across_git_worktrees(self) -> None:
        other = Path(self.temp.name) / "other-worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(other), "HEAD"], cwd=self.repo, check=True, capture_output=True)
        config = load_config(self.root)
        holder = ExecutionLease(self.repo, config)
        contender = ExecutionLease(other, config)
        self.assertEqual(holder.path, contender.path)
        holder.acquire("shared-holder", "2026-08-08T08:05:00Z", None, None, None, "test")
        with self.assertRaisesRegex(LeaseHeldError, "held by run shared-holder"):
            contender.acquire("shared-contender", "2026-08-08T08:06:00Z", None, None, None, "test")
        holder.release("2026-08-08T08:07:00Z", "test_complete")

    def test_nonexpired_lease_cannot_be_recovered(self) -> None:
        config = load_config(self.root)
        ExecutionLease(self.repo, config).acquire("holder", "2026-08-08T08:07:00Z", None, None, None, "test")
        self.run_cli("recover-stale-lease", "--timestamp", "2026-08-08T08:08:00Z", "--run-id", "early", expected=13)

    def test_unrelated_dirty_file_fails_without_cleanup_and_writes_recovery_request(self) -> None:
        (self.repo / "README-user-work.md").write_text("untracked outside lab\n", encoding="utf-8")
        subprocess.run(["git", "add", "README-user-work.md"], cwd=self.repo, check=True)
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:09:00Z", "--run-id", "dirty", expected=14)
        self.assertTrue((self.repo / "README-user-work.md").is_file())
        self.assertTrue((self.repo / ".git" / "aeg-autonomous-lab" / "next-human-action.json").is_file())

    def test_untracked_autonomous_lab_artifact_is_rejected(self) -> None:
        artifact = self.root / "unexpected-secret.txt"
        artifact.write_text("conflicting runtime artifact\n", encoding="utf-8")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:09:30Z", "--run-id", "untracked", expected=14)
        self.assertTrue(artifact.is_file())

    def test_git_operation_in_progress_is_rejected(self) -> None:
        marker = self.repo / ".git" / "MERGE_HEAD"
        marker.write_text("0" * 40 + "\n", encoding="utf-8")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:09:45Z", "--run-id", "merge", expected=14)
        self.assertTrue(marker.is_file())

    def test_verified_library_mutation_returns_unsafe_worktree(self) -> None:
        verified = self.repo / "experiences" / "verified.json"
        verified.write_text(verified.read_text() + " ", encoding="utf-8")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:10:00Z", "--run-id", "verified", expected=14)

    def test_prior_uncommitted_scheduler_output_is_rejected(self) -> None:
        self.make_eligible()
        entry = Lab(self.root).scheduler_entry()
        state_path = self.root / "experiments" / "shakedown" / RECOVERY_ID / "state.json"
        state_path.write_text(state_path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(UnsafeWorktreeError, "uncommitted scheduler output"):
            preflight_worktree(self.repo, self.root, load_config(self.root), entry)

    def test_persistence_rejects_any_path_outside_transition_allowlist(self) -> None:
        self.make_eligible()
        entry = Lab(self.root).scheduler_entry()
        readme = self.root / "README.md"
        readme.write_text(readme.read_text() + "\nunrelated\n", encoding="utf-8")
        with self.assertRaisesRegex(UnsafeWorktreeError, "outside the scheduler allowlist"):
            persist_transition_commit(self.repo, entry, "proposed->screening")
        self.assertIn("unrelated", readme.read_text())

    def test_invalid_ledger_returns_validation_failure(self) -> None:
        self.make_eligible()
        ledger = self.root / "ledger" / "events.jsonl"
        lines = ledger.read_text().splitlines()
        event = json.loads(lines[0])
        event["action"] = "corrupt"
        lines[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.commit("corrupt ledger fixture")
        self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:11:00Z", "--run-id", "invalid", expected=11)

    def test_budget_exhaustion_and_external_approval_exit_codes(self) -> None:
        self.make_eligible()
        state_path = self.root / "experiments" / "shakedown" / RECOVERY_ID / "state.json"
        state = json.loads(state_path.read_text())
        state["budget_used"]["commands"] = 10
        write_json(state_path, state)
        self.commit("exhausted fixture")
        exhausted = self.run_cli("scheduled-step", "--timestamp", "2026-08-08T08:12:00Z", "--run-id", "budget", expected=12)
        self.assertEqual(exhausted["state"], "budget_exhausted")

        self.tearDown()
        self.setUp()
        self.make_eligible(EXTERNAL_ID)
        self.run_cli("scheduled-step", "--persist-commit", "--timestamp", "2026-08-08T08:13:00Z", "--run-id", "external-screen")
        approval = self.run_cli("scheduled-step", "--persist-commit", "--timestamp", "2026-08-08T08:14:00Z", "--run-id", "external-gate", expected=10)
        self.assertEqual(approval["state"], "escalated")


if __name__ == "__main__":
    unittest.main()
