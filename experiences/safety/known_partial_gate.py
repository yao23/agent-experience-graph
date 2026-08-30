#!/usr/bin/env python3
"""Fail-closed retrieval/recommendation gate for known-partial experiences."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional, Set

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SAFETY_ROOT = Path(__file__).resolve().parent
PROFILE_REGISTRY = SAFETY_ROOT / "experience-safety-registry-v1.json"
KNOWN_PARTIAL_REGISTRY = SAFETY_ROOT / "known-partial-registry-v1.json"
POLICY_PATH = SAFETY_ROOT / "known-partial-disconfirmation-policy-v1.json"
PROFILE_SCHEMA = SAFETY_ROOT / "schemas" / "recommendation-safety-profile.schema.json"
KNOWN_PARTIAL_SCHEMA = SAFETY_ROOT / "schemas" / "known-partial-entry.schema.json"
DECISION_SCHEMA = SAFETY_ROOT / "schemas" / "recommendation-decision.schema.json"
SANITIZATION_PROVENANCE = (
    ROOT
    / "experiments"
    / "situated-experience-benchmark-v1"
    / "efficiency-transfer"
    / "seb-requests-tls-efficiency-transfer-smoke-v2"
    / "publication-sanitization-v1.json"
)
SANITIZATION_POLICY = "aeg-publication-sanitization-v1"
PROVENANCE_RECORD_PATH = (
    "experiments/situated-experience-benchmark-v1/efficiency-transfer/"
    "seb-requests-tls-efficiency-transfer-smoke-v2/publication-sanitization-v1.json"
)
EXPECTED_DERIVATIVES = {
    (
        "experiments/situated-experience-benchmark-v1/efficiency-transfer/"
        "seb-requests-tls-efficiency-transfer-smoke-v2/manifest.json"
    ): {
        "original_git_blob_sha": "53c6e43be8e0b8a7c155fdea71ef8cba973fb83c",
        "original_sha256": "1fca863aa91361ad17a0aaf79b9292a0663967a528d4baf2082ca568fd750fe0",
    },
    (
        "experiments/situated-experience-benchmark-v1/efficiency-transfer/"
        "seb-requests-tls-efficiency-transfer-smoke-v2/results/top-level-run-01/audit.json"
    ): {
        "original_git_blob_sha": "c5ec00614471c5155d5812dfc965d8bae00b26fd",
        "original_sha256": "bd11eb884470f73ff9aec44007786cde7ef5859ccf3691b8e74bc1dc97765c7e",
    },
}
REQUIRED_PUBLIC_LIMITATIONS = {
    "two-arm smoke with one run per condition",
    "faithful public extract rather than a full historical Requests and urllib3 stack",
    "fixed A-then-B order with no replication",
    "process-level deny rules rather than disposable-VM or cryptographic isolation",
    "model input attribution was inferred from the frozen runner and private bundle rather than a cryptographic prompt receipt",
    "runner wall time cannot be independently reconstructed from the deleted temporary workspaces",
    "candidate-solution overlap is not evidence of hidden-patch exposure under the frozen prospective policy",
}

WORKER_WITHHELD_NOTICE = (
    "Experience found, but recommendation withheld because its safe "
    "applicability could not be verified."
)

DECISION_PRECEDENCE = [
    "irrelevant",
    "quarantined_harmful_transfer",
    "administratively_ineligible",
    "unresolved_negative_transfer",
    "partial_or_unknown_completeness",
    "known_partial_without_executable_disconfirmation",
    "missing_or_ambiguous_local_checks",
    "incomplete_repair_component_coverage",
    "unresolved_invariants",
    "environment_mismatch",
    "applicability_unverified",
    "known_partial_disconfirmation_failed",
]

CONCEPT_PATTERNS = {
    "instantiate_new_object": [
        r"\b(?:new|fresh|create|creates|created|construct|constructs|constructed|instantiate|instantiates|allocate|allocates)\b",
        r"\b(?:build|builds|built)\s+(?:a\s+)?(?:new|fresh)\b",
    ],
    "per_operation_lifetime": [
        r"\b(?:per|each|every)\s+(?:request|call|invocation|operation)\b",
        r"\bon\s+each\s+(?:request|call|invocation|operation)\b",
        r"\b(?:request|call|invocation|operation)[-_ ]local\b",
    ],
    "security_context": [
        r"\b(?:tls|ssl|security)[-_ ]?context\b",
        r"\bcontext\s+(?:for|used by)\s+(?:tls|ssl|security)\b",
    ],
    "configuration_ownership": [
        r"\b(?:configuration|request)\s+(?:owns|holds|retains|carries)\b",
        r"\b(?:move|keep|retain)\b.{0,40}\b(?:identity|security)\b.{0,40}\bconfiguration\b",
    ],
    "lifetime_isolation": [
        r"\b(?:isolate|isolated|independent)\b.{0,40}\b(?:lifetime|request|operation)\b",
        r"\bno\s+(?:cross|shared)[-_ ](?:request|operation)\b",
    ],
    "concrete_list_only": [
        r"\b(?:type|type_)\b.{0,24}\b(?:is|equals?|==)\s+(?:the\s+)?(?:built[- ]?in\s+)?list\b",
        r"\b(?:concrete|built[- ]?in)[-_ ]list[-_ ]only\b",
        r"\blist[-_ ]only\s+(?:repair|check|handling|predicate)\b",
    ],
    "field_metadata_type": [
        r"\bfield\b.{0,32}\b(?:metadata|type|type_)\b",
        r"\b(?:metadata|type|type_)\b.{0,32}\bfield\b",
    ],
    "single_platform_scope": [
        r"\b(?:windows|macos|linux)[-_ ]only\b",
        r"\bonly\s+(?:the\s+)?(?:windows|macos|linux)\b",
        r"\bone\s+platform\b",
    ],
    "explicit_target_binding": [
        r"\bexplicit(?:ly)?\b.{0,32}\b(?:target|interpreter|python)\b",
        r"\b--python\b",
        r"\bbind\b.{0,24}\btarget\b",
    ],
}

PRIVATE_PATH_RE = re.compile(
    r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\)"
)
HOST_LOCAL_PATH_RE = re.compile(
    r"(?:/(?:Applications|Library|private|tmp|var|opt|usr|bin|sbin)(?:/|\b))"
)
TOKEN_RE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})")
PROTECTED_ANSWER_RE = re.compile(
    r"(?:controller[-_ ]only|protected[-_ ]answer|answer[-_ ]bearing)", re.IGNORECASE
)
PROHIBITED_DERIVED_KEYS = {
    "canonicalexecutablepath",
    "codexpath",
    "command",
    "commands",
    "environment",
    "environments",
    "firststatedapproach",
    "perarm",
    "prompt",
    "promptpath",
    "repairapproach",
    "transcript",
    "transcripts",
}


class GateValidationError(ValueError):
    """Raised when safety evidence or a gate input fails closed."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateValidationError(message)


def _scan_public_value(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _scan_public_value(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_public_value(child, f"{path}[{index}]")
    elif isinstance(value, str):
        _require(not PRIVATE_PATH_RE.search(value), f"{path} contains a private host path")
        _require(not TOKEN_RE.search(value), f"{path} contains credential-shaped content")
        _require(
            not PROTECTED_ANSWER_RE.search(value),
            f"{path} contains a protected evaluator or answer-bearing path",
        )


def _scan_derived_value(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            _require(normalized not in PROHIBITED_DERIVED_KEYS, f"{path}.{key} is forbidden in derived evidence")
            _scan_derived_value(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_derived_value(child, f"{path}[{index}]")
    elif isinstance(value, str):
        _require(not HOST_LOCAL_PATH_RE.search(value), f"{path} contains a host-local path")


def validate_publication_sanitization(
    provenance_path: Path = SANITIZATION_PROVENANCE,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate derived public evidence and fail closed on missing provenance or leakage."""

    root = Path(root).resolve()
    provenance_path = Path(provenance_path)
    _require(provenance_path.is_file(), "publication sanitization provenance is missing")
    provenance = load_json(provenance_path)
    _scan_public_value(provenance)
    _require(provenance.get("schema_version") == "1.0.0", "sanitization provenance schema version mismatch")
    policy = provenance.get("sanitization_policy", {})
    _require(policy == {"id": SANITIZATION_POLICY, "version": "1.0.0"}, "sanitization policy mismatch")
    _require(provenance.get("raw_originals_in_release") is False, "raw originals are not excluded")
    _require(
        provenance.get("scientific_confidence_statement")
        == "This derivation removes publication-unsafe process material and does not upgrade scientific confidence, transfer evidence, or product-market-fit evidence.",
        "scientific confidence boundary mismatch",
    )
    runtime = provenance.get("runtime_dependency", {})
    _require(
        runtime
        == {
            "name": "jsonschema",
            "version": "4.25.1",
            "existing_pin": "autonomous-lab/requirements.txt",
            "installed_or_downloaded_for_derivation": False,
        },
        "runtime dependency provenance mismatch",
    )

    rows = provenance.get("derivatives")
    _require(isinstance(rows, list) and len(rows) == len(EXPECTED_DERIVATIVES), "derived evidence inventory mismatch")
    by_path = {}
    loaded = {}
    for row in rows:
        _require(isinstance(row, dict), "derived evidence record must be an object")
        relative_value = row.get("path")
        _require(isinstance(relative_value, str) and relative_value in EXPECTED_DERIVATIVES, "unexpected derived evidence path")
        _require(relative_value not in by_path, f"duplicate derived evidence path: {relative_value}")
        by_path[relative_value] = row
        expected = EXPECTED_DERIVATIVES[relative_value]
        _require(row.get("publication_status") == "DERIVED_PUBLIC_SAFE", "derived publication status mismatch")
        _require(row.get("original_git_blob_sha") == expected["original_git_blob_sha"], "original Git blob hash mismatch")
        _require(row.get("original_sha256") == expected["original_sha256"], "original SHA-256 mismatch")
        _require(isinstance(row.get("removed_field_categories"), list) and row["removed_field_categories"], "removed field categories are required")
        _require(isinstance(row.get("preserved_semantic_fields"), list) and row["preserved_semantic_fields"], "preserved semantic fields are required")

        relative = Path(relative_value)
        _require(not relative.is_absolute() and ".." not in relative.parts, "derived evidence path escapes repository")
        derivative_path = root / relative
        _require(derivative_path.is_file(), f"derived evidence is missing: {relative_value}")
        _require(sha256_file(derivative_path) == row.get("derived_sha256"), f"derived evidence hash mismatch: {relative_value}")
        derivative = load_json(derivative_path)
        _scan_public_value(derivative)
        _scan_derived_value(derivative)
        _require(derivative.get("publication_status") == "DERIVED_PUBLIC_SAFE", "derived file status mismatch")
        _require(derivative.get("sanitization_policy") == SANITIZATION_POLICY, "derived file policy mismatch")
        source = derivative.get("source_binding", {})
        _require(source.get("original_git_blob_sha") == expected["original_git_blob_sha"], "derived original Git blob mismatch")
        _require(source.get("original_sha256") == expected["original_sha256"], "derived original SHA-256 mismatch")
        _require(source.get("provenance_record") == PROVENANCE_RECORD_PATH, "derived provenance link mismatch")
        loaded[relative_value] = derivative

    _require(set(by_path) == set(EXPECTED_DERIVATIVES), "derived evidence set is incomplete")
    audit_path = next(path for path in loaded if path.endswith("/audit.json"))
    audit = loaded[audit_path]
    terminal = audit.get("terminal_classification", {})
    _require(terminal.get("audit_verdict") == "harmful_transfer", "audit verdict was weakened")
    _require(terminal.get("runner_classification") == "harmful_transfer", "runner classification was weakened")
    _require(terminal.get("classification_predicate", {}).get("matched") is True, "classification predicate is not verified")
    limitations = audit.get("scientific_limitations")
    _require(isinstance(limitations, list), "scientific limitations are missing")
    _require(REQUIRED_PUBLIC_LIMITATIONS <= set(limitations), "one or more required scientific limitations are missing")
    return {
        "status": "valid_derived_public_safe_evidence_v1",
        "derivatives": len(rows),
        "raw_originals_in_release": False,
    }


def _validate_with_schema(instance: Any, schema_path: Path, label: str) -> None:
    validator = Draft202012Validator(load_json(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(item) for item in first.path) or "$"
        raise GateValidationError(f"{label} schema failure at {location}: {first.message}")


def _canonical_verified_record_hash(experience_id: str) -> str | None:
    for record in load_json(ROOT / "experiences" / "verified.json"):
        if record.get("id") == experience_id:
            return sha256_bytes(canonical_json(record))
    return None


def validate_safety_artifacts() -> dict[str, Any]:
    sanitization = validate_publication_sanitization()
    profiles = load_json(PROFILE_REGISTRY)
    partials = load_json(KNOWN_PARTIAL_REGISTRY)
    policy = load_json(POLICY_PATH)
    _require(isinstance(profiles, list) and profiles, "safety profile registry is empty")
    _require(isinstance(partials, list) and partials, "known-partial registry is empty")
    _require(policy.get("policy_id") == "aeg-known-partial-disconfirmation-gate-v1", "policy ID mismatch")
    _require(policy.get("withhold_precedence") == DECISION_PRECEDENCE, "policy precedence differs from code")
    _require(policy.get("worker_notice") == WORKER_WITHHELD_NOTICE, "worker notice differs from code")
    _scan_public_value({"profiles": profiles, "partials": partials, "policy": policy})

    profile_ids: set[str] = set()
    partial_ids: set[str] = set()
    for entry in partials:
        _validate_with_schema(entry, KNOWN_PARTIAL_SCHEMA, "known-partial entry")
        partial_id = entry["partial_repair_id"]
        _require(partial_id not in partial_ids, f"duplicate known-partial ID: {partial_id}")
        partial_ids.add(partial_id)
        artifact = ROOT / entry["evidence_provenance"]["artifact"]
        _require(artifact.is_file(), f"known-partial evidence missing: {artifact}")
        _require(
            sha256_file(artifact) == entry["evidence_provenance"]["artifact_sha256"],
            f"known-partial evidence hash mismatch: {partial_id}",
        )

    for profile in profiles:
        _validate_with_schema(profile, PROFILE_SCHEMA, "safety profile")
        experience_id = profile["experience_id"]
        _require(experience_id not in profile_ids, f"duplicate safety profile: {experience_id}")
        profile_ids.add(experience_id)
        _require(set(profile["known_partial_repair_ids"]) <= partial_ids, f"unknown partial repair in {experience_id}")
        if profile["recommendation_eligible"]:
            _require(profile["completeness_status"] == "complete", f"eligible profile {experience_id} is not complete")
            _require(profile["negative_transfer_status"] != "unresolved", f"eligible profile {experience_id} has unresolved negative transfer")
            _require(profile["quarantine"] is None, f"eligible profile {experience_id} is quarantined")
        if profile["quarantine"] is not None:
            _require(not profile["recommendation_eligible"], f"quarantined profile {experience_id} is eligible")
            _require(profile["negative_transfer_status"] == "unresolved", f"quarantined profile {experience_id} lacks unresolved transfer state")
        for evidence in profile["evidence_provenance"]:
            artifact = ROOT / evidence["artifact"]
            _require(artifact.is_file(), f"profile evidence missing: {artifact}")
            _require(sha256_file(artifact) == evidence["artifact_sha256"], f"profile evidence hash mismatch: {experience_id}")

        expected_version = _canonical_verified_record_hash(experience_id)
        if experience_id == "seb-requests-tls-efficiency-experience-v1":
            expected_version = sha256_file(
                ROOT
                / "experiments"
                / "situated-experience-benchmark-v1"
                / "efficiency-transfer"
                / "requests-tls-efficiency-experience-v1.json"
            )
        _require(expected_version == profile["experience_version_sha256"], f"experience version hash mismatch: {experience_id}")

    verified_ids = {record["id"] for record in load_json(ROOT / "experiences" / "verified.json")}
    _require(verified_ids <= profile_ids, "one or more verified experiences lack a fail-closed safety profile")

    decision_examples = [
        _decision_not_retrieved(),
        _decision_withheld("example", ["administratively_ineligible"], []),
        _decision_recommended("example", []),
    ]
    for decision in decision_examples:
        _validate_with_schema(decision, DECISION_SCHEMA, "recommendation decision")
    return {
        "status": "valid_known_partial_disconfirmation_gate_v1",
        "profiles": len(profiles),
        "known_partial_repairs": len(partials),
        "quarantined_experiences": sum(profile["quarantine"] is not None for profile in profiles),
        "verified_experiences_profiled": len(verified_ids),
        "publication_sanitization": sanitization,
        "worker_notice": WORKER_WITHHELD_NOTICE,
        "model_calls": 0,
    }


def load_profiles(path: Path = PROFILE_REGISTRY) -> dict[str, dict[str, Any]]:
    rows = load_json(path)
    _require(isinstance(rows, list), "safety profile registry must be an array")
    profiles = {}
    for row in rows:
        _validate_with_schema(row, PROFILE_SCHEMA, "safety profile")
        _scan_public_value(row)
        experience_id = row["experience_id"]
        _require(experience_id not in profiles, f"duplicate safety profile: {experience_id}")
        if row["recommendation_eligible"]:
            _require(row["completeness_status"] == "complete", f"eligible profile {experience_id} is incomplete")
            _require(row["quarantine"] is None, f"eligible profile {experience_id} is quarantined")
            _require(row["negative_transfer_status"] != "unresolved", f"eligible profile {experience_id} has unresolved transfer")
        profiles[experience_id] = row
    return profiles


def load_known_partials(path: Path = KNOWN_PARTIAL_REGISTRY) -> list[dict[str, Any]]:
    rows = load_json(path)
    _require(isinstance(rows, list), "known-partial registry must be an array")
    seen = set()
    for row in rows:
        _validate_with_schema(row, KNOWN_PARTIAL_SCHEMA, "known-partial entry")
        _scan_public_value(row)
        partial_id = row["partial_repair_id"]
        _require(partial_id not in seen, f"duplicate known-partial ID: {partial_id}")
        seen.add(partial_id)
    return rows


def semantic_concepts(value: str) -> set[str]:
    normalized = re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ").lower())
    return {
        concept
        for concept, patterns in CONCEPT_PATTERNS.items()
        if any(re.search(pattern, normalized) for pattern in patterns)
    }


def match_known_partials(
    proposed_repair: dict[str, Any] | None,
    known_partials: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not proposed_repair:
        return []
    text = "\n".join(
        str(proposed_repair.get(field, ""))
        for field in ("description", "plan", "patch_summary", "diff")
    )
    concepts = semantic_concepts(text)
    matches = []
    for entry in known_partials:
        required = set(entry["semantic_signature"]["required_concepts"])
        coverage = len(required & concepts) / len(required)
        if coverage >= entry["semantic_signature"]["minimum_concept_coverage"]:
            matches.append(
                {
                    "partial_repair_id": entry["partial_repair_id"],
                    "coverage": round(coverage, 4),
                    "matched_concepts": sorted(required & concepts),
                }
            )
    return matches


def _decision_not_retrieved() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "state": "not_retrieved_irrelevant",
        "retrieval_decision": "not_retrieved",
        "recommendation_decision": "not_applicable",
        "worker_payload": {"notice": "No relevant verified experience was found."},
        "private_evidence": {
            "experience_id": None,
            "precedence": 1,
            "reasons": ["irrelevant"],
            "known_partial_matches": [],
            "output_similarity_is_leakage": False,
        },
    }


def _decision_withheld(
    experience_id: str,
    reasons: list[str],
    known_partial_ids: list[str],
) -> dict[str, Any]:
    ordered = sorted(set(reasons), key=DECISION_PRECEDENCE.index)
    return {
        "schema_version": "1.0.0",
        "state": "retrieved_but_recommendation_withheld",
        "retrieval_decision": "retrieved",
        "recommendation_decision": "withheld",
        "worker_payload": {"notice": WORKER_WITHHELD_NOTICE},
        "private_evidence": {
            "experience_id": experience_id,
            "precedence": DECISION_PRECEDENCE.index(ordered[0]) + 1,
            "reasons": ordered,
            "known_partial_matches": known_partial_ids,
            "output_similarity_is_leakage": False,
        },
    }


def _decision_recommended(experience_id: str, known_partial_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "state": "retrieved_and_recommended",
        "retrieval_decision": "retrieved",
        "recommendation_decision": "recommended",
        "worker_payload": {
            "recommendation_authorized": True,
            "experience_id": experience_id,
        },
        "private_evidence": {
            "experience_id": experience_id,
            "precedence": None,
            "reasons": [],
            "known_partial_matches": known_partial_ids,
            "output_similarity_is_leakage": False,
        },
    }


def _check_result_passes(result: dict[str, Any], required_invariants: set[str]) -> bool:
    return (
        result.get("worker_visible") is True
        and result.get("forbidden_sources_used") is False
        and result.get("environment_supported") is True
        and result.get("exit_code") == 0
        and required_invariants <= set(result.get("demonstrated_invariants", []))
    )


def evaluate_recommendation(
    *,
    relevant: bool,
    experience_id: str,
    profile: dict[str, Any] | None,
    task_context: dict[str, Any] | None,
    known_partials: list[dict[str, Any]],
    proposed_repair: dict[str, Any] | None = None,
    disconfirmation_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate relevance and recommendation separately without returning content when withheld."""

    if not relevant:
        return _decision_not_retrieved()
    context = task_context or {}
    reasons: list[str] = []
    matches = match_known_partials(proposed_repair, known_partials)
    matched_ids = [match["partial_repair_id"] for match in matches]
    if profile is None:
        reasons.extend(["administratively_ineligible", "partial_or_unknown_completeness"])
        return _decision_withheld(experience_id, reasons, matched_ids)

    if profile.get("quarantine") is not None:
        reasons.append("quarantined_harmful_transfer")
    if profile.get("recommendation_eligible") is not True:
        reasons.append("administratively_ineligible")
    if profile.get("negative_transfer_status") == "unresolved":
        reasons.append("unresolved_negative_transfer")
    if profile.get("completeness_status") != "complete":
        reasons.append("partial_or_unknown_completeness")

    registered_partial_ids = set(profile.get("known_partial_repair_ids", []))
    relevant_partials = [entry for entry in known_partials if entry["partial_repair_id"] in registered_partial_ids or entry["partial_repair_id"] in matched_ids]
    if any(not all(check["executable"] for check in entry["required_disconfirmation_checks"]) for entry in relevant_partials):
        reasons.append("known_partial_without_executable_disconfirmation")

    required_local_checks = profile.get("required_local_checks", [])
    local_results = {row.get("check_id"): row for row in context.get("local_check_results", [])}
    local_checks_valid = bool(required_local_checks)
    for check in required_local_checks:
        result = local_results.get(check.get("check_id"))
        if not check.get("executable") or not check.get("worker_visible") or result is None:
            local_checks_valid = False
            continue
        if not _check_result_passes(result, set(check.get("demonstrates_invariants", []))):
            local_checks_valid = False
    if not local_checks_valid:
        reasons.append("missing_or_ambiguous_local_checks")

    required_components = set(profile.get("required_repair_components", []))
    covered_components = set(context.get("repair_component_coverage", []))
    if not required_components or not required_components <= covered_components:
        reasons.append("incomplete_repair_component_coverage")

    invariant_status = profile.get("invariant_status", {})
    if any(invariant_status.get(name) == "unresolved" for name in ("ownership", "lifetime", "representation", "compatibility", "environment")):
        reasons.append("unresolved_invariants")
    if context.get("environment_match") is not True or context.get("environment_assumptions_checked") is not True:
        reasons.append("environment_mismatch")
    if context.get("applicability_established") is not True:
        reasons.append("applicability_unverified")

    if matches:
        results_by_id = {row.get("check_id"): row for row in (disconfirmation_results or [])}
        all_disconfirmed = True
        for entry in relevant_partials:
            if entry["partial_repair_id"] not in matched_ids:
                continue
            for check in entry["required_disconfirmation_checks"]:
                result = results_by_id.get(check["check_id"])
                if not check["executable"] or result is None or not _check_result_passes(result, set(check["demonstrates_invariants"])):
                    all_disconfirmed = False
        if not all_disconfirmed:
            reasons.append("known_partial_disconfirmation_failed")

    if reasons:
        return _decision_withheld(experience_id, reasons, matched_ids)
    return _decision_recommended(experience_id, matched_ids)


def execute_worker_visible_checks(
    workspace: Path,
    checks: list[dict[str, Any]],
    worker_visible_paths: list[str],
    isolation_attestation: dict[str, Any],
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    """Run registered argv-only checks inside an already isolated worker-visible bundle."""

    root = workspace.resolve()
    _require(root.is_dir(), "worker workspace does not exist")
    _require(isolation_attestation.get("bundle_audit_passed") is True, "worker bundle audit is not attested")
    _require(isolation_attestation.get("protected_sources_unreachable") is True, "protected sources are not attested unreachable")
    _require(isolation_attestation.get("credentials_unavailable") is True, "credential isolation is not attested")
    visible = set(worker_visible_paths)
    for relative in visible:
        candidate = Path(relative)
        _require(not candidate.is_absolute() and ".." not in candidate.parts, "worker-visible path escapes workspace")
        _require((root / candidate).exists(), f"worker-visible path is missing: {relative}")
    current_bundle = audit_worker_visible_bundle(root, sorted(visible))
    _require(
        isolation_attestation.get("manifest_sha256") == current_bundle["manifest_sha256"],
        "worker bundle changed after isolation attestation",
    )

    results = []
    for check in checks:
        _require(check.get("executable") is True, f"check {check.get('check_id')} is not executable")
        command = check.get("command")
        _require(isinstance(command, list) and len(command) >= 2, "check command must be argv")
        for token in command:
            _require(isinstance(token, str) and token, "check command contains an empty token")
            _require(not Path(token).is_absolute() and ".." not in Path(token).parts, "check command escapes worker workspace")
            _require(not PROTECTED_ANSWER_RE.search(token), "check command names a protected controller artifact")
        required_paths = set(check.get("worker_visible_paths", []))
        _require(required_paths <= visible, f"check {check['check_id']} requires non-visible evidence")
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        results.append(
            {
                "check_id": check["check_id"],
                "command_sha256": sha256_bytes(canonical_json(command)),
                "exit_code": completed.returncode,
                "stdout_sha256": sha256_bytes(completed.stdout),
                "stderr_sha256": sha256_bytes(completed.stderr),
                "worker_visible": True,
                "forbidden_sources_used": False,
                "environment_supported": True,
                "demonstrated_invariants": check["demonstrates_invariants"] if completed.returncode == 0 else [],
            }
        )
    return results


def audit_worker_visible_bundle(
    workspace: Path,
    declared_paths: list[str],
    protected_artifact_hashes: Optional[Set[str]] = None,
) -> dict[str, Any]:
    """Prove a bundle contains exactly declared regular files and no protected bytes."""

    root = workspace.resolve()
    _require(root.is_dir(), "worker workspace does not exist")
    declared = set(declared_paths)
    for relative in declared:
        candidate = Path(relative)
        _require(not candidate.is_absolute() and ".." not in candidate.parts, "declared path escapes workspace")
    observed: set[str] = set()
    manifest = []
    protected = protected_artifact_hashes or set()
    for path in sorted(root.rglob("*")):
        _require(not path.is_symlink(), f"worker bundle contains a symlink: {path.name}")
        if path.is_dir():
            continue
        _require(path.is_file(), f"worker bundle contains a non-regular entry: {path.name}")
        relative = path.relative_to(root).as_posix()
        observed.add(relative)
        digest = sha256_file(path)
        _require(digest not in protected, "worker bundle contains bytes from a protected controller artifact")
        manifest.append({"path": relative, "sha256": digest, "size": path.stat().st_size})
    _require(observed == declared, "worker bundle differs from its declared visible-file manifest")
    return {
        "bundle_audit_passed": True,
        "files": len(manifest),
        "manifest_sha256": sha256_bytes(canonical_json(manifest)),
        "protected_artifact_matches": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate schemas, registries, provenance, privacy, and policy/code parity.")
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(validate_safety_artifacts(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
