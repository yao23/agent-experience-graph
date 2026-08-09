#!/usr/bin/env python3
"""Validate the proposed Phase 1 seed-user package without authorizing it."""

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
    require("Latency or token savings alone never satisfy" in protocol["design"]["observable_value_definition"], "latency/token-only success is not forbidden")
    require(any("Misleading-retrieval count is 0" in item for item in protocol["thresholds"]["success"]), "success threshold must require zero misleading retrievals")
    require(any("at least 1 relevant recommendation" in item for item in protocol["thresholds"]["success"]), "success must include one relevant recommendation with objective path-change evidence")
    require(any("materially changes" in item for item in protocol["thresholds"]["failure"]), "failure threshold must stop on materially harmful misleading retrieval")

    required_promotion_terms = (
        "independent external reuse", "objective", "provenance", "privacy",
        "separate human approval", "experiences/verified.json",
    )
    promotion_text = "\n".join(protocol["promotion_requirements"])
    for term in required_promotion_terms:
        require(term in promotion_text, f"promotion boundary omits {term}")

    actions = approval["actions"]
    require(actions["repository_local_planning"] == "approved", "local planning approval is missing")
    require(actions["draft_pr"] == "approved", "draft PR approval is missing")
    for action in (
        "recruitment", "external_communication", "participant_task_execution",
        "model_or_agent_execution", "external_project_write", "candidate_promotion",
        "verified_library_change", "publication", "release", "paid_execution", "secret_use",
    ):
        require(actions[action] == "pending", f"{action} must remain pending")
    require(actions["scheduled_task_creation_or_enablement"] == "denied", "Scheduled Task creation or enablement must remain denied")

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

    require(len(stopping["immediate_stop"]) >= 8, "stopping policy is incomplete")
    stop_text = "\n".join(stopping["immediate_stop"])
    for term in ("recruitment", "model-assisted", "credential", "misleading retrieval", "verified-library", "Scheduled Task"):
        require(term in stop_text, f"stopping policy omits {term}")

    for label, artifact in protocol["artifact_paths"].items():
        path = resolve(repo_root, artifact)
        if path.suffix == ".md" and label in {"github_invitation", "social_post", "direct_message"}:
            text = path.read_text(encoding="utf-8")
            require("DRAFT" in text and "DO NOT" in text, f"{label} is not visibly marked unsent")
            require("Verified Experience Challenge" in text, f"{label} does not lead with the Verified Experience Challenge")

    ledger_template = load_json(package / "templates" / "participant-task-ledger-template.json")
    result_template = load_json(package / "templates" / "anonymized-result-template.json")
    validate_instance(ledger_template, package / "schemas" / "participant-task-ledger.schema.json", "ledger template")
    validate_instance(result_template, package / "schemas" / "anonymized-result.schema.json", "result template")
    require(ledger_template["records"] == [], "planning package must not contain participant or task records")
    require(result_template["status"] == "not_started", "result template must remain not started")

    return {
        "status": "passed",
        "experiment_id": EXPERIMENT_ID,
        "lifecycle_state": protocol["lifecycle_state"],
        "scheduler_eligible": False,
        "maximum_participants": 5,
        "maximum_tasks": 5,
        "maximum_model_calls": 40,
        "maximum_model_cost_usd": 100,
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
