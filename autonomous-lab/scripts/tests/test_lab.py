from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from lab import Lab, LabValidationError, canonical_hash  # noqa: E402


SOURCE_LAB = Path(__file__).resolve().parents[2]
SOURCE_REPO = SOURCE_LAB.parent


class LabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.root = self.repo / "autonomous-lab"
        shutil.copytree(SOURCE_LAB, self.root)
        for batch in ("self-consumption-batch-01", "self-consumption-batch-02"):
            path = self.repo / "dogfood" / batch
            path.mkdir(parents=True)
            (path / ("batch-01-decision.md" if batch.endswith("01") else "batch-02-decision.md")).write_text(
                "historical fixture\n", encoding="utf-8"
            )
        experiences = self.repo / "experiences"
        experiences.mkdir()
        shutil.copy2(SOURCE_REPO / "experiences" / "verified.json", experiences / "verified.json")
        self.lab = Lab(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def current_paths(self) -> tuple[Path, Path, Path, Path]:
        entry = self.lab.current_entry()
        return (
            self.lab.resolve(entry["goal_path"]),
            self.lab.resolve(entry["state_path"]),
            self.lab.resolve(entry["scorecard_path"]),
            self.lab.resolve(entry["escalation_path"]),
        )

    def write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def write_yaml(self, path: Path, value: object) -> None:
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    def read_events(self) -> list[dict]:
        return [json.loads(line) for line in (self.root / "ledger" / "events.jsonl").read_text().splitlines()]

    def write_events(self, events: list[dict]) -> None:
        (self.root / "ledger" / "events.jsonl").write_text(
            "".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events),
            encoding="utf-8",
        )

    def test_complete_control_plane_validates(self) -> None:
        result = self.lab.validate()
        self.assertEqual(result["result"], "valid")
        self.assertEqual(result["registry_experiments"], 3)

    def test_valid_state_transition_is_constructed(self) -> None:
        _, goal, state, _, _ = self.lab.records()
        state["approvals"]["begin_experiment"] = "approved"
        event = self.lab._event_for_transition(
            goal, state, "screening", ["screening-evidence.json"], "2026-08-08T01:00:00Z", "test", "test"
        )
        self.assertEqual(event["previous_state"], "proposed")
        self.assertEqual(event["new_state"], "screening")
        self.assertEqual(event["event_sha256"], canonical_hash(event))

    def test_skipped_transition_is_rejected(self) -> None:
        events = self.read_events()
        events[0]["new_state"] = "ready"
        events[0]["event_sha256"] = canonical_hash(events[0])
        self.write_events(events)
        _, state_path, _, _ = self.current_paths()
        state = json.loads(state_path.read_text())
        state["state"] = "ready"
        state["approvals"]["begin_experiment"] = "approved"
        state["ledger_head_sha256"] = events[0]["event_sha256"]
        self.write_json(state_path, state)
        registry = yaml.safe_load((self.root / "experiments" / "registry.yaml").read_text())
        registry["experiments"][-1]["state"] = "ready"
        self.write_yaml(self.root / "experiments" / "registry.yaml", registry)
        with self.assertRaisesRegex(LabValidationError, "invalid or skipped transition"):
            Lab(self.root).validate()

    def test_execution_without_preregistration_is_rejected(self) -> None:
        _, goal, state, _, _ = self.lab.records()
        with self.assertRaisesRegex(LabValidationError, "not allowed"):
            self.lab._event_for_transition(
                goal, state, "running", ["attempt.json"], "2026-08-08T01:00:00Z", "test", "test"
            )

    def test_missing_evidence_is_rejected(self) -> None:
        _, goal, state, _, _ = self.lab.records()
        with self.assertRaisesRegex(LabValidationError, "requires evidence"):
            self.lab._event_for_transition(goal, state, "screening", [], "2026-08-08T01:00:00Z", "test", "test")

    def test_missing_oracle_is_rejected(self) -> None:
        _, goal, state, _, _ = self.lab.records()
        goal.pop("objective_oracle")
        state["state"] = "running"
        with self.assertRaisesRegex(LabValidationError, "objective oracle"):
            self.lab._event_for_transition(
                goal, state, "evaluating", ["result.json"], "2026-08-08T01:00:00Z", "test", "test"
            )

    def test_evaluate_requires_results(self) -> None:
        goal_path, state_path, _, _ = self.current_paths()
        self.assertTrue(goal_path.is_file())
        state = json.loads(state_path.read_text())
        state["state"] = "evaluating"
        self.write_json(state_path, state)
        results = self.root / "empty-results.json"
        self.write_json(results, [])
        with self.assertRaisesRegex(LabValidationError, "non-empty"):
            Lab(self.root).evaluate(results, "2026-08-08T01:00:00Z")

    def test_budget_exhaustion_escalates(self) -> None:
        _, state_path, _, _ = self.current_paths()
        state = json.loads(state_path.read_text())
        state["budget_used"]["commands"] = 120
        self.write_json(state_path, state)
        action = Lab(self.root).next_action()
        self.assertEqual(action["kind"], "escalate")
        self.assertEqual(action["transition"], "budget_exhausted")

    def test_repeated_failure_escalates_at_three(self) -> None:
        _, state_path, _, _ = self.current_paths()
        state = json.loads(state_path.read_text())
        state["retry_count"] = 3
        self.write_json(state_path, state)
        action = Lab(self.root).next_action()
        self.assertEqual(action["kind"], "escalate")
        self.assertIn("retries", action["reason"])

    def test_external_write_and_promotion_require_approval(self) -> None:
        self.assertEqual(self.lab.approval_decision("external_write")["kind"], "escalate")
        self.assertEqual(self.lab.approval_decision("promotion")["kind"], "escalate")

    def test_verified_library_mutation_is_detected(self) -> None:
        path = self.repo / "experiences" / "verified.json"
        path.write_text(path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(LabValidationError, "immutable baseline"):
            self.lab.validate()

    def test_overwritten_ledger_event_is_detected(self) -> None:
        events = self.read_events()
        events[0]["action"] = "silently overwritten"
        self.write_events(events)
        with self.assertRaisesRegex(LabValidationError, "content hash mismatch"):
            self.lab.validate()

    def test_rehashed_historical_event_still_violates_append_only_rule(self) -> None:
        original = (self.root / "ledger" / "events.jsonl").read_text()
        events = self.read_events()
        events[0]["action"] = "rewritten and rehashed"
        events[0]["event_sha256"] = canonical_hash(events[0])
        self.write_events(events)
        with self.assertRaisesRegex(LabValidationError, "removed or overwritten"):
            self.lab.validate_append_only(original)

    def test_terminal_state_cannot_continue(self) -> None:
        _, goal, state, _, _ = self.lab.records()
        state["state"] = "completed"
        with self.assertRaisesRegex(LabValidationError, "not allowed|terminal"):
            self.lab._event_for_transition(
                goal, state, "running", ["evidence"], "2026-08-08T01:00:00Z", "test", "test"
            )

    def test_report_generation_is_idempotent(self) -> None:
        first = self.lab.render_reports()
        second = self.lab.render_reports()
        self.assertEqual(first, second)
        self.lab.report(check=True)

    def test_one_step_makes_at_most_one_transition(self) -> None:
        _, state_path, _, escalation_path = self.current_paths()
        state = json.loads(state_path.read_text())
        state["approvals"]["begin_experiment"] = "approved"
        self.write_json(state_path, state)
        escalation = json.loads(escalation_path.read_text())
        escalation["status"] = "resolved"
        escalation["resolved_at"] = "2026-08-08T00:59:00Z"
        escalation["resolution"] = "approve screening only"
        self.write_json(escalation_path, escalation)
        lab = Lab(self.root)
        before = lab.status()["ledger_event_count"]
        lab.perform_transition("screening", ["freshness-search.json"], "2026-08-08T01:00:00Z")
        after = Lab(self.root).status()["ledger_event_count"]
        self.assertEqual(after - before, 1)
        self.assertEqual(Lab(self.root).status()["state"], "screening")

    def test_batch_registry_records_honest_historical_limits(self) -> None:
        self.lab.validate_registry()
        entries = {item["experiment_id"]: item for item in self.lab.registry["experiments"]}
        batch_01 = entries["aeg-self-consumption-batch-01"]["conclusion"]
        batch_02 = entries["aeg-self-consumption-batch-02"]["conclusion"]
        self.assertIn("zero promotion-ready", batch_01)
        self.assertIn("zero qualified", batch_02)
        self.assertIn("no affirmative AEG retrieval benefit", batch_02)


if __name__ == "__main__":
    unittest.main()
