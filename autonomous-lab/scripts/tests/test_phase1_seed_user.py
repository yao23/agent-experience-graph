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
    validate_recruitment_records,
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

    def test_recruitment_requires_human_reviewed_merge(self) -> None:
        self.mutate("approval-record.json", lambda value: value.update({"effective_condition": "effective immediately on this draft branch"}))
        with self.assertRaisesRegex(Phase1ValidationError, "human-reviewed merge"):
            validate_phase1_package(self.repo, self.entry)

    def test_participant_execution_remains_unapproved(self) -> None:
        self.mutate("approval-record.json", lambda value: value["actions"].update({"participant_task_execution": "approved"}))
        with self.assertRaisesRegex(Phase1ValidationError, "participant_task_execution must remain pending"):
            validate_phase1_package(self.repo, self.entry)

    def test_stage_b_and_evidence_decisions_remain_separate(self) -> None:
        self.mutate("approval-record.json", lambda value: value["actions"].update({"stage_b": "approved"}))
        with self.assertRaisesRegex(Phase1ValidationError, "stage_b must remain pending"):
            validate_phase1_package(self.repo, self.entry)

    def test_recruitment_budget_is_bounded_and_unused(self) -> None:
        self.mutate(
            "stage-a-recruitment/budget.json",
            lambda value: value["initial_invitations"].update({"maximum": 11}),
        )
        with self.assertRaisesRegex(Phase1ValidationError, "initial_invitations maximum is unsafe"):
            validate_phase1_package(self.repo, self.entry)

    def test_recruitment_templates_are_empty(self) -> None:
        for name in ("candidate-shortlist-template.json", "outreach-ledger-template.json"):
            value = json.loads((SOURCE_REPO / PACKAGE_RELATIVE / "stage-a-recruitment" / name).read_text(encoding="utf-8"))
            self.assertTrue(value["template_only"])
            self.assertEqual(value["records"], [])

    def recruitment_fixture(self) -> tuple[dict, dict]:
        candidate = {
            "candidate_id": "C001",
            "discovery_source": "relevant_public_work",
            "review_status": "enrolled",
            "eligibility": {
                "active_coding_agent_user": "confirmed",
                "current_real_task": "confirmed",
                "repository_authorization": "public",
                "objective_reproducible_oracle": "confirmed",
                "correct_public_repair_known": "no",
                "sensitive_data_boundary_agreed": "confirmed",
            },
            "consent_status": {
                "participation": "consented",
                "eligibility_record_retention": "consented",
                "anonymized_experimental_evidence_retention": "not_requested",
                "public_result_publication": "not_requested",
            },
            "participant_id": "P01",
        }
        event = {
            "outreach_id": "O001",
            "candidate_id": "C001",
            "event_type": "initial_invitation",
            "review_id": "R001",
            "review_completed": True,
            "personalized": True,
            "channel": "direct_message",
            "sent_at": "2026-08-09T05:00:00Z",
            "response": "interested",
        }
        shortlist = {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "authorization_id": "aeg-phase1-stage-a-recruitment-v1",
            "template_only": False,
            "records": [candidate],
        }
        outreach = {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "authorization_id": "aeg-phase1-stage-a-recruitment-v1",
            "template_only": False,
            "records": [event],
        }
        return shortlist, outreach

    def test_recruitment_record_semantics_accept_one_consented_enrollment(self) -> None:
        shortlist, outreach = self.recruitment_fixture()
        result = validate_recruitment_records(SOURCE_REPO, shortlist, outreach)
        self.assertEqual(result["enrolled_participants"], 1)
        self.assertEqual(result["initial_invitations"], 1)

    def test_nonresponse_is_not_consent(self) -> None:
        shortlist, outreach = self.recruitment_fixture()
        outreach["records"][0]["response"] = "no_response"
        with self.assertRaisesRegex(Phase1ValidationError, "nonresponse is not consent"):
            validate_recruitment_records(SOURCE_REPO, shortlist, outreach)

    def test_only_one_initial_invitation_and_follow_up_per_candidate(self) -> None:
        shortlist, outreach = self.recruitment_fixture()
        duplicate = copy.deepcopy(outreach["records"][0])
        duplicate.update({"outreach_id": "O002", "review_id": "R002", "sent_at": "2026-08-09T05:01:00Z"})
        outreach["records"].append(duplicate)
        with self.assertRaisesRegex(Phase1ValidationError, "more than one initial invitation"):
            validate_recruitment_records(SOURCE_REPO, shortlist, outreach)

    def test_stage_a_enrollment_is_capped_at_three(self) -> None:
        shortlist, outreach = self.recruitment_fixture()
        for index in range(2, 5):
            candidate = copy.deepcopy(shortlist["records"][0])
            candidate.update({"candidate_id": f"C{index:03d}", "participant_id": f"P{index:02d}"})
            shortlist["records"].append(candidate)
            event = copy.deepcopy(outreach["records"][0])
            event.update({"outreach_id": f"O{index:03d}", "candidate_id": f"C{index:03d}", "review_id": f"R{index:03d}"})
            outreach["records"].append(event)
        with self.assertRaisesRegex(Phase1ValidationError, "enrollment exceeds 3"):
            validate_recruitment_records(SOURCE_REPO, shortlist, outreach)

    def test_candidate_schema_rejects_identity_and_source_fields(self) -> None:
        shortlist, outreach = self.recruitment_fixture()
        shortlist["records"][0]["email"] = "not-allowed@example.invalid"
        with self.assertRaisesRegex(Phase1ValidationError, "Additional properties are not allowed"):
            validate_recruitment_records(SOURCE_REPO, shortlist, outreach)

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
