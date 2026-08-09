from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from lab import Lab  # noqa: E402
from validate_phase1_seed_user import (  # noqa: E402
    EXPERIMENT_ID,
    PACKAGE_RELATIVE,
    Phase1ValidationError,
    validate_phase1_package,
)


SOURCE_LAB = Path(__file__).resolve().parents[2]
SOURCE_REPO = SOURCE_LAB.parent


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class Phase1SeedUserTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = yaml.safe_load((SOURCE_LAB / "experiments" / "registry.yaml").read_text(encoding="utf-8"))
        self.entry = copy.deepcopy(
            next(item for item in registry["experiments"] if item["experiment_id"] == EXPERIMENT_ID)
        )
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        destination = self.repo / PACKAGE_RELATIVE
        destination.parent.mkdir(parents=True)
        shutil.copytree(SOURCE_REPO / PACKAGE_RELATIVE, destination)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def mutate(self, relative: str, callback) -> None:
        path = self.repo / PACKAGE_RELATIVE / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        callback(value)
        write_json(path, value)

    def test_canonical_proposal_is_valid_and_scheduler_ineligible(self) -> None:
        result = validate_phase1_package(SOURCE_REPO, self.entry)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["lifecycle_state"], "proposed")
        self.assertFalse(result["scheduler_eligible"])
        lab = Lab(SOURCE_LAB)
        self.assertEqual(lab.scheduler_entries(), [])
        self.assertEqual(lab.status()["state"], "completed")
        self.assertEqual(lab.validate()["protocol_experiments"], 1)

    def test_recruitment_and_execution_must_remain_unapproved(self) -> None:
        self.mutate("approval-record.json", lambda value: value["actions"].update({"recruitment": "approved"}))
        with self.assertRaisesRegex(Phase1ValidationError, "recruitment must remain pending"):
            validate_phase1_package(self.repo, self.entry)

    def test_stage_b_and_evidence_decisions_remain_separate(self) -> None:
        self.mutate("approval-record.json", lambda value: value["actions"].update({"stage_b": "approved"}))
        with self.assertRaisesRegex(Phase1ValidationError, "stage_b must remain pending"):
            validate_phase1_package(self.repo, self.entry)

    def test_scheduler_eligibility_cannot_be_enabled(self) -> None:
        entry = copy.deepcopy(self.entry)
        entry["scheduler_eligible"] = True
        with self.assertRaisesRegex(Phase1ValidationError, "scheduler-ineligible"):
            validate_phase1_package(self.repo, entry)

    def test_frozen_oracle_and_pre_diagnosis_query_gates_are_required(self) -> None:
        def remove_freeze(value: dict) -> None:
            value["eligibility_gates"] = [gate for gate in value["eligibility_gates"] if gate["id"] != "freeze"]

        self.mutate("protocol.json", remove_freeze)
        with self.assertRaisesRegex(Phase1ValidationError, "eligibility gates"):
            validate_phase1_package(self.repo, self.entry)

    def test_promotion_boundary_requires_independent_external_reuse(self) -> None:
        def weaken(value: dict) -> None:
            value["promotion_requirements"] = ["objective verification and human review"]

        self.mutate("protocol.json", weaken)
        with self.assertRaisesRegex(Phase1ValidationError, "promotion boundary"):
            validate_phase1_package(self.repo, self.entry)

    def test_budget_is_hard_capped_and_unused(self) -> None:
        self.mutate("budget.json", lambda value: value["model_calls"].update({"maximum": 41}))
        with self.assertRaisesRegex(Phase1ValidationError, "model_calls maximum"):
            validate_phase1_package(self.repo, self.entry)

    def test_per_task_soft_limits_cannot_raise_absolute_budget(self) -> None:
        self.mutate("budget.json", lambda value: value["soft_limits_per_task"].update({"commands": 31}))
        with self.assertRaisesRegex(Phase1ValidationError, "soft_limits_per_task.commands"):
            validate_phase1_package(self.repo, self.entry)

    def test_absolute_budget_stops_before_overrun(self) -> None:
        self.mutate(
            "stopping-policy.json",
            lambda value: value["immediate_stop"].__setitem__(-1, "stop only after an absolute budget is exceeded"),
        )
        with self.assertRaisesRegex(Phase1ValidationError, "absolute budgets must stop before overrun"):
            validate_phase1_package(self.repo, self.entry)

    def test_abstention_cannot_count_as_affirmative_aeg_value(self) -> None:
        def credit_abstention(value: dict) -> None:
            value["definitions"]["observable_user_value"] = "A correct abstention is affirmative AEG usefulness."

        self.mutate("protocol.json", credit_abstention)
        with self.assertRaisesRegex(Phase1ValidationError, "abstention must not count"):
            validate_phase1_package(self.repo, self.entry)

    def test_zero_denominators_remain_not_applicable(self) -> None:
        self.mutate(
            "templates/anonymized-result-template.json",
            lambda value: value.update({"recommendation_correctness_rate": 1}),
        )
        with self.assertRaisesRegex(Phase1ValidationError, "empty recommendation denominator"):
            validate_phase1_package(self.repo, self.entry)

    def test_each_invitation_contains_required_disclosures(self) -> None:
        invitation = self.repo / PACKAGE_RELATIVE / "templates" / "social-post.md"
        invitation.write_text("# DRAFT — DO NOT SEND\n\nVerified Experience Challenge\n", encoding="utf-8")
        with self.assertRaisesRegex(Phase1ValidationError, "participant disclosure"):
            validate_phase1_package(self.repo, self.entry)

    def test_planning_package_contains_no_participant_records(self) -> None:
        result = json.loads(
            (SOURCE_REPO / PACKAGE_RELATIVE / "templates" / "participant-task-ledger-template.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["records"], [])
        self.assertTrue(result["template_only"])

    def test_verified_library_remains_at_phase0_baseline(self) -> None:
        phase0 = json.loads(
            (SOURCE_LAB / "experiments" / "proposed" / "aeg-assisted-agent-failure-recovery-service" / "state.json").read_text(encoding="utf-8")
        )
        actual = hashlib.sha256((SOURCE_REPO / "experiences" / "verified.json").read_bytes()).hexdigest()
        self.assertEqual(actual, phase0["verified_library_sha256"])


if __name__ == "__main__":
    unittest.main()
