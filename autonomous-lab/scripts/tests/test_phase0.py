from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from lab import EXIT_APPROVAL_REQUIRED, EXIT_BUDGET_EXHAUSTED, Lab, LabValidationError  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
