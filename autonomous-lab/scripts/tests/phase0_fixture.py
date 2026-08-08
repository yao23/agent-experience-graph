"""Explicit isolated Phase 0 fixtures independent of repository lifecycle state."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


EXPERIMENT = "aeg-assisted-agent-failure-recovery-service-v0"
EXPERIMENT_DIR = Path(
    "experiments/proposed/aeg-assisted-agent-failure-recovery-service"
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prepare_preregistered_phase0(root: Path) -> None:
    """Restore an isolated preregistered Phase 0 state from explicit data."""
    ledger_path = root / "ledger" / "events.jsonl"
    events = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    preregistration_index = next(
        index
        for index, event in enumerate(events)
        if event["experiment_id"] == EXPERIMENT and event.get("new_state") == "preregistered"
    )
    events = events[: preregistration_index + 1]
    ledger_path.write_text(
        "".join(
            json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )
    phase_events = [event for event in events if event["experiment_id"] == EXPERIMENT]
    preregistration = phase_events[-1]

    registry_path = root / "experiments" / "registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["current_experiment_id"] = EXPERIMENT
    entry = next(item for item in registry["experiments"] if item["experiment_id"] == EXPERIMENT)
    entry.update(
        {
            "operational_status": "active",
            "scheduler_eligible": True,
            "state": "preregistered",
            "conclusion": (
                "Only bounded repository-local Phase 0 preparation is approved. "
                "No customer contact, publication, payment, real repair, baseline or "
                "treatment arm, external write, promotion, release, Phase 1, or "
                "effectiveness claim is authorized."
            ),
        }
    )
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    experiment_dir = root / EXPERIMENT_DIR
    write_json(
        experiment_dir / "state.json",
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT,
            "state": "preregistered",
            "milestone": "Phase 0 preparation authorized and preregistered; awaiting deterministic readiness validation",
            "blocker": None,
            "updated_at": preregistration["timestamp"],
            "approved_phase": "phase0_preparation",
            "phase_run_count": 0,
            "approval_record_path": "autonomous-lab/experiments/proposed/aeg-assisted-agent-failure-recovery-service/approvals/phase0-approvals.jsonl",
            "approval_event_sha256": "d22bc8999e4dbe5fd7a578ba24c99f8a21b396919bc44b1e2e84d82f257dac16",
            "approval_file_sha256": "5f57927f3ff28dd937ab0654d4aa56ae3f678658629d6c1d08f960d1feb22384",
            "usage_observability": {
                "model_calls": "tracked by scheduled/model-assisted run count",
                "tokens": "unavailable",
                "cost_usd": "unavailable",
            },
            "budget_used": {
                "iterations": 0,
                "commands": 0,
                "tests": 0,
                "model_calls": 0,
                "wall_minutes": 0,
                "tokens": 0,
                "cost_usd": 0,
            },
            "retry_count": 0,
            "approvals": {
                "begin_experiment": "approved",
                "model_or_agent_execution": "approved",
                "paid_execution": "pending",
                "external_project_write": "pending",
                "contact_external_user": "pending",
                "open_or_merge_pull_request": "pending",
                "candidate_promotion": "pending",
                "verified_library_change": "pending",
                "release_publication": "pending",
                "secret_creation_or_use": "pending",
            },
            "ledger_event_count": len(phase_events),
            "ledger_head_sha256": preregistration["event_sha256"],
            "verified_library_sha256": "7cfe56dd68d7d901cd7fa6d0ed01c8149b06711d7c0381f0ca6a3c95acb838d3",
        },
    )
    write_json(
        experiment_dir / "scorecard.json",
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT,
            "status": "incomplete",
            "comparison_pairs": 0,
            "acceptance_results": [],
            "metrics": {
                "objective_recovery_rate": None,
                "retrieval_effect_rate": None,
                "external_acceptance_rate": None,
                "paid_pilot_conversion": None,
                "phase0_artifacts_complete": None,
                "external_actions": 0,
                "model_calls": 0,
                "tokens": "unavailable",
                "cost_usd": "unavailable",
            },
            "decision": "pending",
            "limitations": [
                "Only repository-local Phase 0 preparation is authorized.",
                "No repair, baseline, treatment, customer contact, external-value, generalized-effectiveness, or PMF evidence exists.",
                "Exact token and dollar cost telemetry is unavailable and is not estimated as zero.",
            ],
        },
    )
    write_json(
        experiment_dir / "escalation.json",
        {
            "schema_version": 1,
            "escalation_id": "failure-recovery-v0-begin-approval",
            "experiment_id": EXPERIMENT,
            "created_at": "2026-08-08T04:25:00Z",
            "status": "resolved",
            "reason_code": "approval_required",
            "summary": "Repository-local Phase 0 preparation is approved; external validation and Phase 1 remain blocked.",
            "evidence": [
                "approvals/phase0-approvals.jsonl contains the scoped authorization",
                "state.json links the approval event and file hashes",
                "External writes, customer contacts, paid experiments, and verified-library modifications remain limited to zero",
            ],
            "requested_decision": "No human decision is required during authorized repository-local Phase 0 preparation.",
            "allowed_resolutions": ["continue bounded Phase 0 preparation", "stop Phase 0"],
            "tradeoffs": [
                "Continuing may improve the reviewability of the unpublished service package but supplies no external-value or repair-effect evidence.",
                "Stopping preserves all external, payment, publication, promotion, and repair-execution boundaries.",
            ],
            "recommended_choice": "Continue only the bounded repository-local Phase 0 package validation.",
            "resolved_at": "2026-08-08T04:25:00Z",
            "resolution": "Phase 0 preparation only was approved; Phase 1 and all external actions remain unapproved.",
        },
    )
    write_json(
        experiment_dir / "phase0-validation.json",
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT,
            "approved_phase": "phase0_preparation",
            "validated_at": preregistration["timestamp"],
            "transition": "activation",
            "approval_event_sha256": "d22bc8999e4dbe5fd7a578ba24c99f8a21b396919bc44b1e2e84d82f257dac16",
            "approval_file_sha256": "5f57927f3ff28dd937ab0654d4aa56ae3f678658629d6c1d08f960d1feb22384",
            "required_artifacts": 16,
            "artifact_checks_passed": True,
            "internal_links_checked": 0,
            "internal_links_resolve": True,
            "claims_and_evidence_boundaries_passed": True,
            "sensitive_content_absent": True,
            "verified_library_modifications": 0,
            "external_actions": 0,
            "customer_contacts": 0,
            "paid_experiments": 0,
            "baseline_treatment_repairs": 0,
            "phase_run_count": 0,
            "result": "valid",
        },
    )
    write_json(
        experiment_dir / "phase0-scorecard.json",
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT,
            "approved_phase": "phase0_preparation",
            "status": "preregistered",
            "required_artifacts": 16,
            "artifact_checks_passed": None,
            "internal_links_resolve": None,
            "claims_match_batch_evidence": None,
            "unsupported_claims_absent": None,
            "private_or_proprietary_information_absent": None,
            "sample_is_sanitized_and_reproducible": None,
            "pricing_labeled_hypothesis": None,
            "outreach_is_draft_only": None,
            "external_actions": 0,
            "customer_contacts": 0,
            "paid_experiments": 0,
            "verified_library_modifications": 0,
            "baseline_treatment_repairs": 0,
            "scheduled_or_model_assisted_runs": 0,
            "model_calls": 0,
            "tokens": "unavailable",
            "cost_usd": "unavailable",
            "next_requested_decision": "whether to begin Phase 1 seed-user recruitment",
            "decision": "pending deterministic Phase 0 validation",
            "limitations": [
                "Repository-local package preparation is not repair-effectiveness evidence.",
                "No user, maintainer, customer, payment, publication, or external acceptance evidence exists.",
                "Exact token and dollar cost telemetry is unavailable and is not estimated as zero.",
            ],
        },
    )
