#!/usr/bin/env python3
"""Deterministic validator for the approved repository-local Phase 0 package."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PHASE = "phase0_preparation"
MAX_RUNS = 8
REQUIRED_ARTIFACTS = (
    "service-spec.md", "target-customer.md", "problem-statement.md",
    "intake-questionnaire.md", "eligibility-checklist.md", "delivery-workflow.md",
    "customer-report-template.md", "sanitized-sample-report.md",
    "pricing-hypotheses.md", "landing-page-copy.md", "outreach-drafts.md",
    "baseline-treatment-protocol.md", "metrics-plan.md",
    "privacy-and-ip-boundaries.md", "phase0-scorecard.json", "phase0-decision.md",
)
ZERO_LIMITS = {
    "customer_contacts": 0,
    "external_writes": 0,
    "paid_experiments": 0,
    "verified_library_modifications": 0,
}
FORBIDDEN_APPROVALS = (
    "paid_execution", "external_project_write", "contact_external_user",
    "candidate_promotion", "verified_library_change", "release_publication",
    "secret_creation_or_use",
)
SENSITIVE = re.compile(
    r"(/" + "Users" + r"/|/home/[^ /]+/|BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})"
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


class Phase0ValidationError(ValueError):
    """Raised when the Phase 0 authorization or package is invalid."""


def canonical_approval_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "approval_event_sha256"}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_approval(path: Path) -> dict[str, Any]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise Phase0ValidationError("Phase 0 approval record must contain exactly one append-only event")
    record = json.loads(lines[0])
    if record.get("approval_event_sha256") != canonical_approval_hash(record):
        raise Phase0ValidationError("Phase 0 approval event hash does not match its content")
    return record


def validate_package(repo_root: Path, entry: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    experiment_dir = (repo_root / entry["state_path"]).parent
    approval_path = repo_root / entry["approval_record_path"]
    approval = load_approval(approval_path)
    file_hash = hashlib.sha256(approval_path.read_bytes()).hexdigest()
    event_hash = approval["approval_event_sha256"]

    if approval.get("approved_phase") != PHASE or state.get("approved_phase") != PHASE:
        raise Phase0ValidationError("authorization is not limited to phase0_preparation")
    if approval.get("experiment_id") != state.get("experiment_id"):
        raise Phase0ValidationError("approval experiment identity does not match state")
    for record in (entry, state):
        if record.get("approval_event_sha256") != event_hash:
            raise Phase0ValidationError("approval event hash link is inconsistent")
        if record.get("approval_file_sha256") != file_hash:
            raise Phase0ValidationError("approval file hash link is inconsistent")
    limits = approval.get("limits", {})
    if limits.get("scheduled_or_model_assisted_runs") != MAX_RUNS:
        raise Phase0ValidationError("Phase 0 run limit must be exactly eight")
    if limits.get("state_transitions_per_run") != 1 or limits.get("same_failure_repetitions") != 3:
        raise Phase0ValidationError("Phase 0 transition or repetition limit is invalid")
    if any(limits.get(key) != value for key, value in ZERO_LIMITS.items()):
        raise Phase0ValidationError("external, paid, customer, and verified-library limits must remain zero")
    if any(state["approvals"].get(key) == "approved" for key in FORBIDDEN_APPROVALS):
        raise Phase0ValidationError("approval state authorizes an action outside Phase 0")
    if state.get("phase_run_count", 0) > MAX_RUNS:
        raise Phase0ValidationError("Phase 0 run count exceeds its authorization")

    configured = tuple(Path(path).name for path in entry.get("phase0_artifact_paths", ()))
    if configured != REQUIRED_ARTIFACTS:
        raise Phase0ValidationError("registry Phase 0 artifact list is incomplete or reordered")
    missing = [name for name in REQUIRED_ARTIFACTS if not (experiment_dir / name).is_file()]
    if missing:
        raise Phase0ValidationError(f"required Phase 0 artifacts are missing: {missing}")

    link_count = 0
    for name in REQUIRED_ARTIFACTS:
        path = experiment_dir / name
        text = path.read_text(encoding="utf-8")
        if SENSITIVE.search(text):
            raise Phase0ValidationError(f"sensitive content or private path found in {name}")
        if path.suffix == ".md":
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.split("#", 1)[0].strip().strip("<>")
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                link_count += 1
                if not (path.parent / target).resolve().is_file():
                    raise Phase0ValidationError(f"unresolved internal link in {name}: {target}")

    sample = (experiment_dir / "sanitized-sample-report.md").read_text(encoding="utf-8").lower()
    pricing = (experiment_dir / "pricing-hypotheses.md").read_text(encoding="utf-8").lower()
    outreach = (experiment_dir / "outreach-drafts.md").read_text(encoding="utf-8").lower()
    decision = (experiment_dir / "phase0-decision.md").read_text(encoding="utf-8").lower()
    required_phrases = (
        (sample, "illustrative"), (sample, "no aeg retrieval effect"),
        (pricing, "hypoth"), (pricing, "no payment"),
        (outreach, "unsent"), (decision, "phase 1 seed-user recruitment"),
    )
    if any(phrase not in text for text, phrase in required_phrases):
        raise Phase0ValidationError("Phase 0 evidence/claims labels are incomplete")

    scorecard = json.loads((experiment_dir / "phase0-scorecard.json").read_text())
    for score_key in (
        "external_actions", "customer_contacts", "paid_experiments",
        "verified_library_modifications", "baseline_treatment_repairs",
    ):
        if scorecard.get(score_key) != 0:
            raise Phase0ValidationError(f"Phase 0 scorecard must keep {score_key}=0 before external approval")
    if scorecard.get("tokens") != "unavailable" or scorecard.get("cost_usd") != "unavailable":
        raise Phase0ValidationError("unavailable token and cost telemetry must not be reported as zero")

    return {
        "schema_version": 1,
        "experiment_id": state["experiment_id"],
        "approved_phase": PHASE,
        "approval_event_sha256": event_hash,
        "approval_file_sha256": file_hash,
        "required_artifacts": len(REQUIRED_ARTIFACTS),
        "artifact_checks_passed": True,
        "internal_links_checked": link_count,
        "internal_links_resolve": True,
        "claims_and_evidence_boundaries_passed": True,
        "sensitive_content_absent": True,
        "verified_library_modifications": 0,
        "external_actions": 0,
        "customer_contacts": 0,
        "paid_experiments": 0,
        "baseline_treatment_repairs": 0,
        "phase_run_count": state.get("phase_run_count", 0),
        "result": "valid",
    }
