#!/usr/bin/env python3
"""Validate Phase 1 and its bounded recruitment-only activation record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


EXPERIMENT_ID = "aeg-verified-experience-seed-user-v1"
RUNNER_KIND = "phase1-seed-user-protocol"
PACKAGE_RELATIVE = Path(
    "autonomous-lab/experiments/proposed/aeg-verified-experience-seed-user-v1"
)
RECRUITMENT_RELATIVE = PACKAGE_RELATIVE / "stage-a-recruitment"


class Phase1ValidationError(Exception):
    """Raised when the Phase 1 proposal weakens a preregistered boundary."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    if repo_root.resolve() not in path.parents:
        raise Phase1ValidationError(f"path escapes repository: {value}")
    if not path.is_file():
        raise Phase1ValidationError(f"required Phase 1 artifact is missing: {value}")
    return path


def validate_instance(instance: Any, schema_path: Path, label: str) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{label}:{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise Phase1ValidationError(details)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1ValidationError(message)


def validate_recruitment_records(
    repo_root: Path,
    shortlist: dict[str, Any],
    outreach: dict[str, Any],
) -> dict[str, int]:
    """Apply schema and cross-record limits to recruitment-only records."""
    recruitment = repo_root.resolve() / RECRUITMENT_RELATIVE
    validate_instance(shortlist, recruitment / "candidate-shortlist.schema.json", "candidate shortlist")
    validate_instance(outreach, recruitment / "outreach-ledger.schema.json", "outreach ledger")

    candidates = shortlist["records"]
    events = outreach["records"]
    candidate_ids = [record["candidate_id"] for record in candidates]
    require(len(candidate_ids) == len(set(candidate_ids)), "candidate IDs must be unique")
    outreach_ids = [record["outreach_id"] for record in events]
    require(len(outreach_ids) == len(set(outreach_ids)), "outreach IDs must be unique")
    require(len(candidates) <= 10, "candidate shortlist exceeds 10")

    enrolled = [record for record in candidates if record["review_status"] == "enrolled"]
    require(len(enrolled) <= 3, "Stage A enrollment exceeds 3")
    participant_ids = [record["participant_id"] for record in enrolled]
    require(all(participant_ids), "enrolled candidates require pseudonymous participant IDs")
    require(len(participant_ids) == len(set(participant_ids)), "participant IDs must be unique")

    by_candidate = {record["candidate_id"]: record for record in candidates}
    events_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        require(event["candidate_id"] in by_candidate, "outreach references an unknown candidate")
        events_by_candidate.setdefault(event["candidate_id"], []).append(event)

    initial_count = 0
    follow_up_count = 0
    for candidate_id, candidate_events in events_by_candidate.items():
        initials = [event for event in candidate_events if event["event_type"] == "initial_invitation"]
        follow_ups = [event for event in candidate_events if event["event_type"] == "follow_up"]
        require(len(initials) <= 1, "more than one initial invitation for a candidate")
        require(len(follow_ups) <= 1, "more than one follow-up for a candidate")
        require(not follow_ups or initials, "follow-up requires an initial invitation")
        if follow_ups and initials:
            require(follow_ups[0]["sent_at"] > initials[0]["sent_at"], "follow-up must occur after the initial invitation")
        initial_count += len(initials)
        follow_up_count += len(follow_ups)

    require(initial_count <= 10, "initial invitation limit exceeds 10")
    require(follow_up_count <= 10, "follow-up limit exceeds 10")
    require(len(events) <= 20, "total outbound message limit exceeds 20")

    required_eligibility = {
        "active_coding_agent_user": "confirmed",
        "current_real_task": "confirmed",
        "objective_reproducible_oracle": "confirmed",
        "correct_public_repair_known": "no",
        "sensitive_data_boundary_agreed": "confirmed",
    }
    for candidate in candidates:
        if candidate["review_status"] in {"invite_ready", "invited", "enrolled"}:
            eligibility = candidate["eligibility"]
            for gate, expected in required_eligibility.items():
                require(eligibility[gate] == expected, f"invite-ready candidate fails {gate}")
            require(
                eligibility["repository_authorization"] in {"public", "owner_authorized_not_accessed"},
                "invite-ready candidate lacks repository authorization",
            )
        if candidate["review_status"] == "enrolled":
            consent = candidate["consent_status"]
            require(consent["participation"] == "consented", "enrollment requires affirmative participation consent")
            require(consent["eligibility_record_retention"] == "consented", "enrollment requires eligibility-record retention consent")
            responses = [event["response"] for event in events_by_candidate.get(candidate["candidate_id"], [])]
            require(any(response == "interested" for response in responses), "nonresponse is not consent")

    return {
        "shortlist_candidates": len(candidates),
        "initial_invitations": initial_count,
        "follow_ups": follow_up_count,
        "enrolled_participants": len(enrolled),
    }


def validate_phase1_package(repo_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    require(entry.get("experiment_id") == EXPERIMENT_ID, "Phase 1 experiment ID is incorrect")
    require(entry.get("runner_kind") == RUNNER_KIND, "Phase 1 runner kind is incorrect")
    require(entry.get("operational_status") == "proposed", "Phase 1 must remain proposed")
    require(entry.get("state") == "proposed", "Phase 1 registry state must remain proposed")
    require(entry.get("scheduler_eligible") is False, "Phase 1 must remain scheduler-ineligible")

    package = repo_root / PACKAGE_RELATIVE
    protocol = load_json(resolve(repo_root, entry["protocol_path"]))
    approval = load_json(resolve(repo_root, entry["approval_path"]))
    budget = load_json(resolve(repo_root, entry["budget_path"]))
    stopping = load_json(resolve(repo_root, entry["stopping_policy_path"]))
    recruitment_budget = load_json(resolve(repo_root, entry["recruitment_budget_path"]))
    recruitment_stopping = load_json(resolve(repo_root, entry["recruitment_stopping_policy_path"]))
    shortlist = load_json(resolve(repo_root, entry["candidate_shortlist_template_path"]))
    outreach = load_json(resolve(repo_root, entry["outreach_ledger_template_path"]))

    validate_instance(protocol, resolve(repo_root, entry["artifact_schema_path"]), "protocol")
    validate_instance(approval, package / "schemas" / "approval-record.schema.json", "approval")
    validate_instance(budget, package / "schemas" / "budget.schema.json", "budget")
    validate_instance(stopping, package / "schemas" / "stopping-policy.schema.json", "stopping policy")

    require(protocol["lifecycle_state"] == "proposed", "protocol cannot be activated or preregistered before review")
    require(protocol["recruitment"]["minimum_participants"] == 3, "minimum participant limit must be 3")
    require(protocol["recruitment"]["maximum_participants"] == 5, "maximum participant limit must be 5")
    require(protocol["recruitment"]["maximum_tasks"] == 5, "maximum task limit must be 5")
    require(protocol["design"]["tasks_per_participant"] == 1, "each participant may supply only one task")
    require(protocol["recruitment"]["lead_asset"] == "Verified Experience Challenge", "recruitment must lead with the Verified Experience Challenge")

    expected_gates = {
        "repository-authorization", "license", "contribution-path", "reproduction",
        "freeze", "prior-repair-search", "pre-diagnosis-query", "baseline-plan",
        "evidence-plan", "privacy", "consent",
    }
    require({gate["id"] for gate in protocol["eligibility_gates"]} == expected_gates, "eligibility gates are incomplete or unexpected")
    expected_metrics = {
        "task-completion", "objective-oracle-result", "material-path-change",
        "commands-and-interventions", "participant-usefulness",
        "correct-recommendation-rate", "correct-abstention-rate",
        "misleading-retrieval-count",
    }
    require({metric["id"] for metric in protocol["primary_metrics"]} == expected_metrics, "primary metrics are incomplete or unexpected")
    require(
        set(protocol["design"]["retrieval_outcomes"]) == {
            "relevant_recommendation", "correct_abstention",
            "irrelevant_retrieval", "misleading_retrieval",
        },
        "retrieval outcome classification is incomplete",
    )
    required_definitions = {
        "relevant_recommendation", "misleading_retrieval",
        "material_repair_path_change", "observable_user_value",
        "uncontaminated_task", "independent_success", "protocol_violation",
        "task_level_success", "experiment_level_success",
    }
    require(set(protocol["definitions"]) == required_definitions, "computable outcome definitions are incomplete")
    require(
        "calibration evidence" in protocol["definitions"]["observable_user_value"]
        and "not affirmative AEG usefulness" in protocol["definitions"]["observable_user_value"],
        "correct abstention must not count as affirmative AEG usefulness",
    )
    require(
        "independent success" in protocol["definitions"]["task_level_success"],
        "task success must separate independent success",
    )
    for rate_name in ("recommendation_correctness", "abstention_correctness"):
        rate = protocol["metric_computation"][rate_name]
        require("Number of uncontaminated tasks" in rate["numerator"], f"{rate_name} numerator is not task-computable")
        require("Number of uncontaminated tasks" in rate["denominator"], f"{rate_name} denominator is not task-computable")
        require("raw counts" in rate["reporting"], f"{rate_name} must report raw counts")
        require("0/0" in rate["zero_denominator"] and "not success" in rate["zero_denominator"], f"{rate_name} zero denominator is unsafe")
    require(
        "calibration evidence only" in protocol["metric_computation"]["abstention_correctness"]["zero_denominator"],
        "abstention correctness must remain calibration-only",
    )
    require(protocol["stages"]["stage_a"]["maximum_participants"] == 3, "Stage A participant limit must be 3")
    require(protocol["stages"]["stage_a"]["maximum_tasks"] == 3, "Stage A task limit must be 3")
    require(protocol["stages"]["stage_b"]["maximum_participants"] == 2, "Stage B participant limit must be 2")
    require(protocol["stages"]["stage_b"]["maximum_tasks"] == 2, "Stage B task limit must be 2")
    require("never continues automatically" in protocol["stages"]["stage_a"]["continuation_rule"], "Stage A must stop for mandatory review")
    require("Stage B approval" in protocol["stages"]["stage_b"]["entry_approval"], "Stage B requires separate approval")
    require(
        set(protocol["outcome_classifications"]) == {
            "initial_positive_signal", "positive_retrieval_signal",
            "calibration_abstention_evidence_only", "inconclusive",
            "protocol_failure", "harmful_or_misleading_retrieval",
            "privacy_or_authorization_failure",
        },
        "experiment outcome classifications are incomplete",
    )
    require(
        "not affirmative AEG usefulness" in protocol["outcome_classifications"]["calibration_abstention_evidence_only"],
        "calibration-only classification overclaims abstention value",
    )
    require(
        all(
            term in protocol["outcome_classifications"]["initial_positive_signal"]
            for term in ("not PMF", "generalized effectiveness", "causal superiority", "commercial demand")
        ),
        "initial-positive-signal classification omits claim boundaries",
    )
    value_definition = protocol["design"]["observable_value_definition"].lower()
    require(
        "alone never satisfy" in value_definition
        and all(term in value_definition for term in ("participant ratings", "latency", "tokens", "commands")),
        "ratings/resource-only success is not forbidden",
    )
    require("Correct abstention is valuable calibration evidence" in protocol["design"]["observable_value_definition"], "abstention is incorrectly credited as usefulness")
    require(any("Misleading-retrieval count is 0" in item for item in protocol["thresholds"]["success"]), "success threshold must require zero misleading retrievals")
    require(any("At least 1 above-threshold AEG recommendation" in item for item in protocol["thresholds"]["success"]), "success must include one credited recommendation with objective path-change evidence")
    require(any("materially harmful or misleading" in item for item in protocol["thresholds"]["failure"]), "failure threshold must stop on materially harmful misleading retrieval")
    require(any("contaminated execution" in item for item in protocol["thresholds"]["failure"]), "failure threshold must stop on contaminated execution")

    required_promotion_terms = (
        "independent external reuse", "objective", "provenance", "privacy",
        "separate human approval", "experiences/verified.json",
    )
    promotion_text = "\n".join(protocol["promotion_requirements"])
    for term in required_promotion_terms:
        require(term in promotion_text, f"promotion boundary omits {term}")

    require(approval["status"] == "stage_a_recruitment_authorized_on_merge", "Stage A recruitment approval status is incorrect")
    require(
        "only when" in approval["effective_condition"]
        and "merged into main" in approval["effective_condition"]
        and "unmerged state grants no authority" in approval["effective_condition"],
        "recruitment activation must require a human-reviewed merge",
    )
    actions = approval["actions"]
    require(actions["repository_local_planning"] == "approved", "local planning approval is missing")
    require(actions["draft_pr"] == "approved", "draft PR approval is missing")
    for action in (
        "candidate_discovery", "candidate_shortlisting", "recruitment",
        "external_communication", "personalized_invitations", "stage_a_onboarding",
        "eligibility_and_task_submission_collection", "pseudonymous_consent_recording",
        "minimal_recruitment_record_retention",
    ):
        require(actions[action] == "approved", f"bounded {action} authorization is missing")
    for action in (
        "participant_task_execution", "evidence_retention", "model_or_agent_execution", "stage_b",
        "external_project_write", "experience_promotion",
        "verified_library_change", "result_publication", "release",
        "paid_execution", "secret_use",
    ):
        require(actions[action] == "pending", f"{action} must remain pending")
    require(actions["scheduled_task_creation_or_enablement"] == "denied", "Scheduled Task creation or enablement must remain denied")

    expected_recruitment_limits = {
        "shortlist_candidates": 10,
        "initial_invitations": 10,
        "follow_ups": 10,
        "total_outbound_messages": 20,
        "enrolled_participants": 3,
        "task_submissions": 3,
        "initial_invitations_per_candidate": 1,
        "follow_ups_per_candidate": 1,
        "participant_task_executions": 0,
        "aeg_queries_on_participant_tasks": 0,
        "model_calls": 0,
        "mass_posts": 0,
        "automated_messages": 0,
        "participant_payments_usd": 0,
        "paid_acquisition_usd": 0,
    }
    for name, maximum in expected_recruitment_limits.items():
        require(recruitment_budget[name]["used"] == 0, f"recruitment package has nonzero {name} usage")
        require(recruitment_budget[name]["maximum"] == maximum, f"recruitment {name} maximum is unsafe")

    recruitment_stop_text = "\n".join(recruitment_stopping["immediate_stop"])
    for term in (
        "human-approved merge", "individual invitation-review", "scraping",
        "10 initial invitations", "3 enrolled participants", "nonresponse",
        "private-repository", "participant-task execution", "external-project",
        "verified-library change", "Stage B", "Scheduled Task",
    ):
        require(term in recruitment_stop_text, f"recruitment stopping policy omits {term}")

    record_counts = validate_recruitment_records(repo_root, shortlist, outreach)
    require(shortlist["template_only"] and shortlist["records"] == [], "candidate shortlist must remain an empty template")
    require(outreach["template_only"] and outreach["records"] == [], "outreach ledger must remain an empty template")
    eligibility_text = (repo_root / RECRUITMENT_RELATIVE / "eligibility-checklist.md").read_text(encoding="utf-8")
    invitation_text = (repo_root / RECRUITMENT_RELATIVE / "invitation-review-checklist.md").read_text(encoding="utf-8")
    normalized_eligibility = eligibility_text.lower()
    for term in ("actively uses", "real, current", "objective reproducible oracle", "no correct public repair", "nonresponse is not consent"):
        require(term in normalized_eligibility, f"eligibility checklist omits {term}")
    for term in ("individual", "personalized", "no scraping", "single allowed follow-up", "no unsupported performance claim"):
        require(term.lower() in invitation_text.lower(), f"invitation review checklist omits {term}")

    limits = {
        "participants": 5,
        "tasks": 5,
        "model_calls": 40,
        "commands": 200,
        "tests": 100,
        "human_interventions": 40,
        "wall_clock_hours": 15,
        "tokens": 1000000,
        "model_cost_usd": 100,
        "participant_payments_usd": 0,
        "paid_acquisition_usd": 0,
        "same_failure_repeats": 2,
    }
    for name, maximum in limits.items():
        require(budget[name]["used"] == 0, f"planning package has nonzero {name} usage")
        require(budget[name]["maximum"] == maximum, f"{name} maximum differs from preregistration")
    require(budget["cost_estimate"]["maximum_usd"] == 100, "cost estimate must match the hard cost limit")
    require(
        budget["soft_limits_per_task"] == {
            "model_calls": 6,
            "commands": 30,
            "tests": 15,
            "human_interventions": 6,
            "wall_clock_hours": 2,
            "handling": budget["soft_limits_per_task"]["handling"],
        },
        "per-task soft limits differ from the preregistration",
    )
    require("never raises" in budget["soft_limits_per_task"]["handling"], "soft-limit crossing may not raise an absolute ceiling")

    require(len(stopping["immediate_stop"]) >= 10, "stopping policy is incomplete")
    stop_text = "\n".join(stopping["immediate_stop"])
    for term in ("recruitment", "model-assisted", "evidence-retention", "Stage A", "Stage B", "credential", "misleading recommendation", "contaminated execution", "unauthorized action", "verified-library", "Scheduled Task"):
        require(term in stop_text, f"stopping policy omits {term}")
    require(
        "budget is reached, or the next action would exceed it" in stop_text,
        "absolute budgets must stop before overrun",
    )

    for label, artifact in protocol["artifact_paths"].items():
        path = resolve(repo_root, artifact)
        if path.suffix == ".md" and label in {"github_invitation", "social_post", "direct_message"}:
            text = path.read_text(encoding="utf-8")
            require("DRAFT" in text and "DO NOT" in text, f"{label} is not visibly marked unsent")
            require("Verified Experience Challenge" in text, f"{label} does not lead with the Verified Experience Challenge")
            normalized_text = " ".join(text.lower().split())
            for disclosure in (
                "early research experiment", "may abstain", "no benefit",
                "credentials", "private repositories", "employer-confidential code",
                "customer data", "proprietary logs", "voluntary", "withdrawal",
                "anonymized evidence", "publicly publishing results", "separate",
                "No payment",
            ):
                require(disclosure.lower() in normalized_text, f"{label} omits participant disclosure: {disclosure}")

    ledger_template = load_json(package / "templates" / "participant-task-ledger-template.json")
    result_template = load_json(package / "templates" / "anonymized-result-template.json")
    validate_instance(ledger_template, package / "schemas" / "participant-task-ledger.schema.json", "ledger template")
    validate_instance(result_template, package / "schemas" / "anonymized-result.schema.json", "result template")
    require(ledger_template["records"] == [], "planning package must not contain participant or task records")
    require(result_template["status"] == "not_started", "result template must remain not started")
    require(result_template["recommendations_total"] == 0 and result_template["recommendation_correctness_rate"] is None, "empty recommendation denominator must be N/A")
    require(result_template["abstentions_total"] == 0 and result_template["correct_abstention_rate"] is None, "empty abstention denominator must be N/A")

    return {
        "status": "passed",
        "experiment_id": EXPERIMENT_ID,
        "lifecycle_state": protocol["lifecycle_state"],
        "scheduler_eligible": False,
        "maximum_participants": 5,
        "maximum_tasks": 5,
        "maximum_model_calls": 40,
        "maximum_model_cost_usd": 100,
        "stage_a_maximum_tasks": 3,
        "stage_b_maximum_tasks": 2,
        "recruitment_authorization": "effective_only_after_human_reviewed_merge_to_main",
        **record_counts,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    registry = yaml.safe_load(
        (repo_root / "autonomous-lab" / "experiments" / "registry.yaml").read_text(encoding="utf-8")
    )
    entries = [entry for entry in registry["experiments"] if entry.get("experiment_id") == EXPERIMENT_ID]
    if len(entries) != 1:
        raise SystemExit(f"expected one {EXPERIMENT_ID} registry entry, found {len(entries)}")
    print(json.dumps(validate_phase1_package(repo_root, entries[0]), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
