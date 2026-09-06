#!/usr/bin/env python3
"""Bounded, repository-backed control plane for the AEG Foundry pilot."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterator
import uuid


ROOT = Path(__file__).resolve().parents[1]
FOUNDRY = Path("foundry")
PUBLIC_RUNTIME_PATHS = {
    "foundry/backlog.json",
    "foundry/state.json",
    "foundry/rounds.jsonl",
    "foundry/STATUS.md",
}
BOOTSTRAP_PATHS = PUBLIC_RUNTIME_PATHS | {
    ".gitignore",
    ".agents/skills/aeg-foundry/SKILL.md",
    "foundry/CHARTER.md",
    "foundry/pilot.json",
    "foundry/SCHEDULED_TASK.md",
    "scripts/aeg_foundry.py",
    "scripts/test_aeg_foundry.py",
}
PILOT_CONTRACT = {
    "activation": {
        "ends_at": "2026-10-18T07:22:29Z",
        "starts_at": "2026-09-06T07:22:29Z",
    },
    "authorization": {
        "additional_credits_usd": 0,
        "codex_ruleset": "PRESERVE_UNCHANGED",
        "external_communication": "REQUIRES_SEPARATE_AUTHORIZATION",
        "host_privilege_expansion": "REQUIRES_SEPARATE_AUTHORIZATION",
        "new_paid_api_usd": 0,
        "new_paid_cloud_usd": 0,
        "private_material_export": "REQUIRES_SEPARATE_AUTHORIZATION",
        "production_deployment": "REQUIRES_SEPARATE_AUTHORIZATION",
        "production_merge": "REQUIRES_SEPARATE_AUTHORIZATION",
        "registry_promotion": "REQUIRES_SEPARATE_AUTHORIZATION",
        "repository_ruleset_change": "REQUIRES_SEPARATE_AUTHORIZATION",
        "subscription_upgrade_usd": 0,
    },
    "budgets": {
        "max_round_seconds": 2700,
        "max_rounds_per_day": 2,
        "max_rounds_total": 84,
        "max_worker_starts_per_day": 6,
    },
    "config_version": "0.1.2",
    "execution": {
        "cleanup_after_checkpoint_only": True,
        "concurrency": 1,
        "controls_enforcement_level": "CONVENTION_LEVEL",
        "historical_state_policy": "DO_NOT_READ_DOT_AEG",
        "private_directory": ".aeg-foundry-private",
        "required_branch": "codex/aeg-experience-foundry-pilot-v0.1",
        "runtime_class": "LOCAL_PROJECT",
        "untrusted_execution_gate": "REQUIRES_VERIFIED_DISPOSABLE_RUNTIME",
    },
    "model_policy": {
        "automation_model": "gpt-5.6-terra",
        "automation_reasoning_effort": "low",
        "discovery_preference": "gpt-5.6-luna",
        "repair_preference": "gpt-5.6-terra",
        "server_attestation": "UNKNOWN_UNLESS_REPORTED_BY_CLIENT",
    },
    "pilot_id": "AEG-EXPERIENCE-FOUNDRY-PILOT-V0.1",
    "schedule": {
        "cadence": "PT12H",
        "notification_policy": "MEANINGFUL_CHANGE_OR_ACTION_ONLY",
    },
    "schema_version": 2,
    "source": {
        "bootstrap_sha": "999efa64e9ba016efc9d3327df4b70e1fc79b804",
        "charter_path": "foundry/CHARTER.md",
        "remote": "origin",
        "remote_ref": "refs/remotes/origin/main",
        "remote_url": "https://github.com/yao23/agent-experience-graph.git",
    },
    "targets": {
        "deduplicated_external_candidates": 30,
        "external_users_with_strong_evidence": 1,
        "held_out_positive_transfers": 3,
        "independently_behavior_verified_tasks": 10,
        "max_uncontrolled_incidents": 0,
        "qualified_tasks": 15,
        "release_review_experiences_max": 8,
        "release_review_experiences_min": 5,
        "verified_external_users": 3,
    },
}
TASK_STATUSES = {
    "READY",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "BLOCKED_ENVIRONMENT",
    "BLOCKED_APPROVAL",
    "BLOCKED_UNCERTAIN_EFFECT",
}
STAGES = {
    "DISCOVERY",
    "REPRODUCTION",
    "REPAIR",
    "VERIFICATION",
    "TRANSFER_EVALUATION",
    "RELEASE_MATERIAL",
    "REPORTING",
}
OUTCOMES = {"SUCCESS", "FAILURE", "NEUTRAL", "HARMFUL", "INVALID", "BLOCKED"}
ORACLE_STATUSES = {"PASSED", "FAILED", "NOT_RUN", "INVALID"}
CHANNEL_STATUSES = {"ACTIVE", "PAUSED", "QUARANTINED", "BLOCKED_ENVIRONMENT"}
FAILURE_CLASSES = {"NONE", "TASK", "INFRASTRUCTURE", "AUTH", "QUOTA", "ENVIRONMENT"}
EFFECT_TYPES = {
    "READ_PUBLIC_SOURCE",
    "CLONE_PUBLIC_REPOSITORY",
    "INSTALL_PINNED_DEPENDENCIES",
    "RUN_FROZEN_ORACLE",
    "PUSH_PILOT_BRANCH",
    "CREATE_OR_UPDATE_DRAFT_PR",
    "UPDATE_NATIVE_AUTOMATION",
}
UNTRUSTED_EXECUTION_EFFECT_TYPES = {
    "CLONE_PUBLIC_REPOSITORY",
    "INSTALL_PINNED_DEPENDENCIES",
    "RUN_FROZEN_ORACLE",
}
NO_DISPOSABLE_RUNTIME_CODE = "BLOCKED_ENVIRONMENT_NO_DISPOSABLE_RUNTIME"
GITHUB_ISSUE_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/issues/[1-9][0-9]*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CHANNEL_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
CANDIDATE_ID_RE = re.compile(r"^AEG-C-[0-9]{3}$")
EXPERIENCE_ID_RE = re.compile(r"^AEG-X-[0-9]{3}$")
TRANSFER_ID_RE = re.compile(r"^AEG-T-[0-9]{3}$")
BEHAVIOR_ID_RE = re.compile(r"^AEG-V-[0-9]{3}$")
EXTERNAL_USER_ID_RE = re.compile(r"^AEG-U-[0-9]{3}$")
EXTERNAL_REUSE_ID_RE = re.compile(r"^AEG-ER-[0-9]{3}$")
INTEGRITY_INCIDENT_ID_RE = re.compile(r"^AEG-II-[0-9]{3}$")
EFFECT_ID_RE = re.compile(r"^AEG-I-[0-9a-f]{32}$")
RUNTIME_ENVIRONMENT_ID_RE = re.compile(r"^AEG-E-[0-9]{3}$")
RUNTIME_CLAIM_ID_RE = re.compile(r"^AEG-EC-[0-9A-F]{32}$")
CODE_VALUE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,127}$")
CANDIDATE_KEYS = {
    "candidate_id",
    "category",
    "contamination",
    "family",
    "issue_number",
    "oracle_kind",
    "qualification",
    "repository",
    "source_state",
    "source_url",
}
BEHAVIOR_VERIFICATION_KEYS = {
    "baseline",
    "budget",
    "candidate_id",
    "finished_at",
    "model_config",
    "oracle_kind",
    "oracle_version",
    "outcome",
    "repaired",
    "result_revision",
    "solver_code",
    "started_at",
    "status",
    "target_revision",
    "task_id",
    "verification_id",
    "verifier_code",
}
BEHAVIOR_ARM_KEYS = {
    "command_argv",
    "environment_code",
    "evidence_digest_sha256",
    "evidence_summary_codes",
    "exit_code",
    "oracle_observation",
    "workspace_code",
}
EXTERNAL_USER_KEYS = {
    "actor_class",
    "evidence_digest_sha256",
    "evidence_kind",
    "evidence_summary_codes",
    "observed_at",
    "status",
    "user_id",
    "verifier_code",
}
EXTERNAL_REUSE_KEYS = {
    "command_argv",
    "evidence_digest_sha256",
    "evidence_summary_codes",
    "experience_id",
    "experience_version",
    "finished_at",
    "oracle_kind",
    "oracle_observation",
    "oracle_version",
    "outcome",
    "started_at",
    "status",
    "target_revision",
    "user_id",
    "verification_environment_code",
    "verifier_code",
    "reuse_id",
    "exit_code",
}
INTEGRITY_INCIDENT_KEYS = {
    "affected_record_code",
    "containment_code",
    "evidence_digest_sha256",
    "incident_code",
    "incident_id",
    "observed_at",
    "status",
}
RUNTIME_ENVIRONMENT_KEYS = {
    "company_data_mounted",
    "dependency_host_codes",
    "dependency_network_policy",
    "disposable",
    "environment_id",
    "evidence_digest_sha256",
    "expires_at",
    "fresh_instance",
    "github_write_credentials_present",
    "host_home_mounted",
    "isolation_class",
    "model_credentials_present",
    "qualified_at",
    "qualification_status",
    "test_host_codes",
    "test_network_policy",
    "verifier_code",
}
RUNTIME_CLAIM_KEYS = {
    "claim_id",
    "claimed_at",
    "environment_id",
    "round_id",
}
ORACLE_EFFECT_INTENT_KEYS = {
    "effect_id",
    "effect_type",
    "environment_id",
    "oracle_kind",
    "recorded_at",
    "round_id",
    "target_code",
    "target_revision",
}
ORACLE_EFFECT_COMPLETED_KEYS = ORACLE_EFFECT_INTENT_KEYS | {
    "command_argv",
    "evidence_digest_sha256",
    "evidence_summary_codes",
    "exit_code",
    "oracle_observation",
    "outcome",
    "resolved_at",
}
ORACLE_EFFECT_FAILED_KEYS = ORACLE_EFFECT_INTENT_KEYS | {
    "failure_code",
    "outcome",
    "resolved_at",
}
ORACLE_EFFECT_NOT_PERFORMED_KEYS = ORACLE_EFFECT_INTENT_KEYS | {
    "outcome",
    "resolved_at",
}
EXPERIENCE_ARTIFACT_KEYS = {
    "schema_version",
    "experience_id",
    "version",
    "family",
    "problem_signature_codes",
    "precondition_codes",
    "procedure_steps",
    "oracle_kind",
    "source_candidate_ids",
    "limitation_codes",
}
TRANSFER_EVALUATION_KEYS = {
    "all_attempts_retained",
    "assisted",
    "baseline",
    "budget",
    "decision_rule_code",
    "evaluator_feedback_visible_to_assisted",
    "experience_id",
    "experience_version",
    "model_config",
    "oracle_kind",
    "oracle_version",
    "outcome",
    "preregistered_at",
    "retry_rule_code",
    "run_order",
    "status",
    "target_candidate_id",
    "target_revision",
    "task_id",
    "tool_permission_profile",
    "transfer_id",
    "visible_material_codes",
}
TRANSFER_ARM_KEYS = {
    "attempts",
    "context_code",
    "environment_code",
    "oracle_observation",
    "run_status",
    "workspace_code",
}
TRANSFER_ATTEMPT_KEYS = {
    "attempt_id",
    "attempt_number",
    "command_argv",
    "evidence_digest_sha256",
    "evidence_summary_codes",
    "exit_code",
    "finished_at",
    "oracle_executor_code",
    "oracle_observation",
    "run_status",
    "solver_code",
    "started_at",
}
TRANSFER_DECISION_RULE = (
    "BASELINE_FAILURE_ASSISTED_SUCCESS_POSITIVE__MATCH_NEUTRAL__REGRESSION_HARMFUL"
)
ROUND_RECORD_V2_KEYS = {
    "call_method",
    "channel_code",
    "channel_status_after",
    "charter_sha256",
    "completed_at",
    "compute_cost_basis_code",
    "compute_usd",
    "configured_model",
    "elapsed_seconds",
    "failure_class",
    "failure_code",
    "founder_hours",
    "input_tokens",
    "market_estimate_source_code",
    "market_estimate_usd",
    "model",
    "model_attestation",
    "next_step_code",
    "oracle_status",
    "outcome",
    "output_tokens",
    "quota_observation_code",
    "record_schema_version",
    "retry_count",
    "round_id",
    "source_ref",
    "source_ref_sha",
    "source_ref_verified_at",
    "stage",
    "started_at",
    "task_id",
    "total_tokens",
    "worker_starts",
}
WORKER_EVENT_V2_STARTED_KEYS = {
    "call_method",
    "channel_code",
    "configured_model",
    "event_id",
    "kind",
    "model",
    "record_schema_version",
    "round_id",
    "started_at",
    "status",
}
WORKER_EVENT_V2_TERMINAL_KEYS = WORKER_EVENT_V2_STARTED_KEYS | {
    "channel_status_after",
    "completed_at",
    "compute_cost_basis_code",
    "compute_usd",
    "failure_code",
    "input_tokens",
    "market_estimate_source_code",
    "market_estimate_usd",
    "model_attestation",
    "output_tokens",
    "retry_count",
    "total_tokens",
}
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SENSITIVE_VALUE_RES = (
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
    re.compile(r"\b(?:gh[pousr]_|sk-)[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)
FORBIDDEN_PUBLIC_KEYS = {
    "raw_output",
    "raw_prompt",
    "prompt",
    "transcript",
    "patch",
    "diff",
    "credential",
    "credentials",
    "api_key",
    "token",
    "tokens",
    "stderr",
    "stdout",
    "email",
}


class FoundryError(RuntimeError):
    exit_code = 11


class PausedError(FoundryError):
    exit_code = 10


class BudgetError(FoundryError):
    exit_code = 12


class LeaseError(FoundryError):
    exit_code = 13


class UnsafeRepositoryError(FoundryError):
    exit_code = 14


class ConfigError(FoundryError):
    exit_code = 15


class NoWorkError(FoundryError):
    exit_code = 20


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ConfigError(f"invalid UTC timestamp: {value}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigError(f"invalid UTC timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ConfigError(f"timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_decimal_measurement(value: Any) -> bool:
    if value == "UNKNOWN":
        return True
    try:
        return Decimal(str(value)) >= 0
    except (InvalidOperation, ValueError):
        return False


def valid_token_measurement(value: Any) -> bool:
    return value == "UNKNOWN" or (
        isinstance(value, str) and value.isdigit() and int(value) >= 0
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"cannot read valid JSON: {path}") from error


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    atomic_write(path, existing + json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def run_git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments], cwd=root, text=True, capture_output=True, check=False
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise UnsafeRepositoryError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def git_value(root: Path, *arguments: str) -> str:
    return run_git(root, *arguments).stdout.strip()


def repository_preflight(root: Path, pilot: dict[str, Any], require_clean: bool = False) -> None:
    discovered = Path(git_value(root, "rev-parse", "--show-toplevel")).resolve()
    if discovered != root.resolve():
        raise UnsafeRepositoryError("repository root mismatch")
    branch = git_value(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    required = pilot["execution"]["required_branch"]
    if branch != required:
        raise UnsafeRepositoryError(f"required branch {required!r}; found {branch!r}")
    remote = pilot["source"]["remote"]
    actual_url = git_value(root, "remote", "get-url", remote)
    if actual_url != pilot["source"]["remote_url"]:
        raise UnsafeRepositoryError("configured remote URL does not match")
    common = Path(git_value(root, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        if (common / marker).exists():
            raise UnsafeRepositoryError(f"Git operation in progress: {marker}")
    if require_clean and run_git(root, "status", "--porcelain=v1", "--untracked-files=all").stdout:
        raise UnsafeRepositoryError("scheduled round requires a clean starting worktree")


def private_directory(root: Path, pilot: dict[str, Any]) -> Path:
    configured = pilot["execution"]["private_directory"]
    if configured != ".aeg-foundry-private":
        raise ConfigError("private directory must remain .aeg-foundry-private")
    path = root / configured
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


@contextmanager
def control_lock(root: Path, pilot: dict[str, Any], blocking: bool = False) -> Iterator[None]:
    lock_path = private_directory(root, pilot) / "control.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        operation = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), operation)
        except BlockingIOError as error:
            raise LeaseError("another local controller process holds the mutex") from error
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def paths(root: Path) -> dict[str, Path]:
    foundry = root / FOUNDRY
    return {
        "pilot": foundry / "pilot.json",
        "charter": foundry / "CHARTER.md",
        "backlog": foundry / "backlog.json",
        "state": foundry / "state.json",
        "rounds": foundry / "rounds.jsonl",
        "status": foundry / "STATUS.md",
        "reports": foundry / "reports",
        "experiences": foundry / "experiences",
    }


def load_all(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    located = paths(root)
    pilot = load_json(located["pilot"])
    if pilot != PILOT_CONTRACT:
        raise ConfigError("fixed pilot control contract changed")
    return pilot, load_json(located["backlog"]), load_json(located["state"])


def _walk_public(value: Any, location: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in FORBIDDEN_PUBLIC_KEYS:
                errors.append(f"forbidden public key at {location}.{key}")
            errors.extend(_walk_public(item, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_walk_public(item, f"{location}[{index}]"))
    elif isinstance(value, str):
        for pattern in SENSITIVE_VALUE_RES:
            if pattern.search(value):
                errors.append(f"sensitive-shaped public value at {location}")
                break
    return errors


def audit_public(root: Path) -> dict[str, Any]:
    located = paths(root)
    errors: list[str] = []
    for name in ("pilot", "backlog", "state"):
        errors.extend(_walk_public(load_json(located[name]), name))
    if located["rounds"].exists():
        for number, line in enumerate(located["rounds"].read_text(encoding="utf-8").splitlines(), 1):
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"invalid JSONL at rounds line {number}")
                continue
            errors.extend(_walk_public(record, f"rounds[{number}]"))
    for markdown in [located["status"], *sorted(located["reports"].glob("*.md"))]:
        if not markdown.exists():
            continue
        content = markdown.read_text(encoding="utf-8")
        for pattern in SENSITIVE_VALUE_RES:
            if pattern.search(content):
                errors.append(f"sensitive-shaped public markdown: {markdown.relative_to(root)}")
                break
    if located["experiences"].exists():
        for artifact in sorted(located["experiences"].iterdir()):
            if not artifact.is_file() or artifact.suffix != ".json":
                errors.append("Experience artifacts must be direct JSON files")
                continue
            try:
                content = load_json(artifact)
            except ConfigError as error:
                errors.append(str(error))
                continue
            errors.extend(_walk_public(content, f"experience_artifact.{artifact.name}"))
    return {"ok": not errors, "errors": errors, "scanned_private_directory": False}


def validate_committed_foundry_history(
    root: Path, backlog: dict[str, Any], state: dict[str, Any]
) -> list[str]:
    """Reject rewrites of versioned artifacts, preregistration, and terminal results."""
    previous_result = run_git(root, "show", "HEAD:foundry/backlog.json", check=False)
    if previous_result.returncode != 0:
        return []
    try:
        previous = json.loads(previous_result.stdout)
    except json.JSONDecodeError:
        return ["committed foundry backlog is not valid JSON"]

    errors: list[str] = []
    previous_rounds = run_git(root, "show", "HEAD:foundry/rounds.jsonl", check=False)
    if previous_rounds.returncode == 0:
        current_rounds = paths(root)["rounds"].read_text(encoding="utf-8")
        if not current_rounds.startswith(previous_rounds.stdout):
            errors.append("committed round ledger was rewritten instead of appended")
    current_candidates = {
        item.get("candidate_id"): item
        for item in backlog.get("candidates", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    }
    for prior in previous.get("candidates", []):
        if not isinstance(prior, dict) or not isinstance(prior.get("candidate_id"), str):
            continue
        candidate_id = prior["candidate_id"]
        current = current_candidates.get(candidate_id)
        if current is None:
            errors.append(f"committed candidate was deleted: {candidate_id}")
        elif current != prior:
            errors.append(f"committed candidate classification was rewritten: {candidate_id}")

    current_verifications = {
        item.get("verification_id"): item
        for item in backlog.get("behavior_verifications", [])
        if isinstance(item, dict) and isinstance(item.get("verification_id"), str)
    }
    for prior in previous.get("behavior_verifications", []):
        if not isinstance(prior, dict) or not isinstance(prior.get("verification_id"), str):
            continue
        verification_id = prior["verification_id"]
        current = current_verifications.get(verification_id)
        if current is None:
            errors.append(f"committed behavior verification was deleted: {verification_id}")
        elif current != prior:
            errors.append(f"committed behavior verification was rewritten: {verification_id}")

    current_experiences = {
        (item.get("experience_id"), item.get("version")): item
        for item in backlog.get("experiences", [])
        if isinstance(item, dict)
        and isinstance(item.get("experience_id"), str)
        and isinstance(item.get("version"), int)
    }
    for prior in previous.get("experiences", []):
        if not isinstance(prior, dict):
            continue
        key = (prior.get("experience_id"), prior.get("version"))
        current = current_experiences.get(key)
        if current is None:
            errors.append(f"committed Experience version was deleted: {key}")
            continue
        prior_core = {key: value for key, value in prior.items() if key != "release_review_status"}
        current_core = {
            key: value for key, value in current.items() if key != "release_review_status"
        }
        if current_core != prior_core:
            errors.append(f"committed Experience version was rewritten: {key}")
        prior_review = prior.get("release_review_status")
        current_review = current.get("release_review_status")
        if current_review != prior_review and not (
            prior_review == "NOT_READY" and current_review == "READY"
        ):
            errors.append(f"invalid Experience review transition: {key}")

    current_transfers = {
        item.get("transfer_id"): item
        for item in backlog.get("transfer_evaluations", [])
        if isinstance(item, dict) and isinstance(item.get("transfer_id"), str)
    }
    mutable_transfer_keys = {
        "all_attempts_retained",
        "assisted",
        "baseline",
        "outcome",
        "status",
    }
    frozen_arm_keys = {"context_code", "environment_code", "workspace_code"}
    for prior in previous.get("transfer_evaluations", []):
        if not isinstance(prior, dict) or not isinstance(prior.get("transfer_id"), str):
            continue
        transfer_id = prior["transfer_id"]
        current = current_transfers.get(transfer_id)
        if current is None:
            errors.append(f"committed transfer evaluation was deleted: {transfer_id}")
            continue
        if prior.get("status") in {"COMPLETED", "INVALID"}:
            if current != prior:
                errors.append(f"terminal transfer evaluation was rewritten: {transfer_id}")
            continue
        prior_frozen = {
            key: value for key, value in prior.items() if key not in mutable_transfer_keys
        }
        current_frozen = {
            key: value for key, value in current.items() if key not in mutable_transfer_keys
        }
        if current_frozen != prior_frozen:
            errors.append(f"preregistered transfer freeze was rewritten: {transfer_id}")
        for arm_name in ("baseline", "assisted"):
            prior_arm = prior.get(arm_name)
            current_arm = current.get(arm_name)
            if not isinstance(prior_arm, dict) or not isinstance(current_arm, dict):
                continue
            if any(prior_arm.get(key) != current_arm.get(key) for key in frozen_arm_keys):
                errors.append(
                    f"preregistered {arm_name} isolation was rewritten: {transfer_id}"
                )

    previous_state_result = run_git(root, "show", "HEAD:foundry/state.json", check=False)
    if previous_state_result.returncode != 0:
        return errors
    try:
        previous_state = json.loads(previous_state_result.stdout)
    except json.JSONDecodeError:
        errors.append("committed foundry state is not valid JSON")
        return errors
    for field in ("rounds_started", "rounds_completed", "founder_interventions"):
        prior_value = previous_state.get(field)
        current_value = state.get(field)
        if (
            isinstance(prior_value, int)
            and isinstance(current_value, int)
            and current_value < prior_value
        ):
            errors.append(f"committed monotonic counter decreased: {field}")
    prior_daily = previous_state.get("counters_by_utc_day", {})
    current_daily = state.get("counters_by_utc_day", {})
    if isinstance(prior_daily, dict) and isinstance(current_daily, dict):
        for day, prior_counter in prior_daily.items():
            current_counter = current_daily.get(day)
            if not isinstance(prior_counter, dict) or not isinstance(current_counter, dict):
                errors.append(f"committed daily counter was deleted: {day}")
                continue
            for field in ("round_starts", "worker_starts"):
                if (
                    isinstance(prior_counter.get(field), int)
                    and isinstance(current_counter.get(field), int)
                    and current_counter[field] < prior_counter[field]
                ):
                    errors.append(f"committed daily counter decreased: {day}:{field}")
    for list_name, id_key in (
        ("external_users", "user_id"),
        ("external_reuse_events", "reuse_id"),
    ):
        current_records = {
            item.get(id_key): item
            for item in state.get(list_name, [])
            if isinstance(item, dict) and isinstance(item.get(id_key), str)
        }
        for prior in previous_state.get(list_name, []):
            if not isinstance(prior, dict) or not isinstance(prior.get(id_key), str):
                continue
            record_id = prior[id_key]
            current = current_records.get(record_id)
            if current is None:
                errors.append(f"committed {list_name} record was deleted: {record_id}")
                continue
            if prior.get("status") in {"VERIFIED_EXTERNAL_USER", "VERIFIED", "INVALID"}:
                if current != prior:
                    errors.append(f"terminal {list_name} record was rewritten: {record_id}")
            elif current.get(id_key) != record_id:
                errors.append(f"committed {list_name} identity was rewritten: {record_id}")
    prior_effect_events = previous_state.get("effect_events", [])
    current_effect_events = state.get("effect_events", [])
    if isinstance(prior_effect_events, list) and isinstance(current_effect_events, list) and (
        current_effect_events[: len(prior_effect_events)] != prior_effect_events
    ):
        errors.append("committed external-effect receipt ledger was rewritten")
    current_workers = {
        item.get("event_id"): item
        for item in state.get("worker_events", [])
        if isinstance(item, dict) and isinstance(item.get("event_id"), str)
    }
    for prior in previous_state.get("worker_events", []):
        if not isinstance(prior, dict) or not isinstance(prior.get("event_id"), str):
            continue
        event_id = prior["event_id"]
        current = current_workers.get(event_id)
        if current is None:
            errors.append(f"committed worker event was deleted: {event_id}")
        elif prior.get("status") != "STARTED" and current != prior:
            errors.append(f"terminal worker event was rewritten: {event_id}")
        elif prior.get("status") == "STARTED":
            for field in WORKER_EVENT_V2_STARTED_KEYS - {"status"}:
                if prior.get(field) != current.get(field):
                    errors.append(f"started worker identity was rewritten: {event_id}")
                    break
    prior_incidents = previous_state.get("integrity_incidents", [])
    current_incidents = state.get("integrity_incidents", [])
    if isinstance(prior_incidents, list) and isinstance(current_incidents, list) and (
        current_incidents[: len(prior_incidents)] != prior_incidents
    ):
        errors.append("committed integrity incident ledger was rewritten")
    for list_name in ("runtime_environments", "runtime_environment_claims"):
        prior_records = previous_state.get(list_name, [])
        current_records = state.get(list_name, [])
        if isinstance(prior_records, list) and isinstance(current_records, list) and (
            current_records[: len(prior_records)] != prior_records
        ):
            errors.append(f"committed {list_name} ledger was rewritten")
    return errors


def validate(root: Path, check_git: bool = True) -> dict[str, Any]:
    pilot, backlog, state = load_all(root)
    errors: list[str] = []
    if pilot != PILOT_CONTRACT:
        raise ConfigError("fixed pilot control contract changed")
    try:
        starts = parse_time(pilot["activation"]["starts_at"])
        ends = parse_time(pilot["activation"]["ends_at"])
        if ends - starts != timedelta(days=42):
            errors.append("pilot duration must remain exactly 42 days")
    except (KeyError, ConfigError) as error:
        errors.append(str(error))
    budgets = pilot.get("budgets", {})
    try:
        source_remote_head_ref(pilot)
    except (KeyError, ConfigError) as error:
        errors.append(str(error))
    if backlog.get("schema_version") != 2 or state.get("schema_version") != 4:
        errors.append("unsupported backlog or state schema")

    channels = state.get("channels")
    if not isinstance(channels, dict) or not channels:
        errors.append("execution channels must be a non-empty object")
        channels = {}
    for channel_code, channel in channels.items():
        if not isinstance(channel_code, str) or not CHANNEL_RE.fullmatch(channel_code):
            errors.append(f"invalid execution channel code: {channel_code}")
            continue
        if not isinstance(channel, dict) or channel.get("status") not in CHANNEL_STATUSES:
            errors.append(f"invalid execution channel status: {channel_code}")
            continue
        streak = channel.get("consecutive_infrastructure_failures", 0)
        if not isinstance(streak, int) or streak < 0 or streak > 2:
            errors.append(f"invalid infrastructure failure streak: {channel_code}")
        if channel.get("status") == "QUARANTINED" and streak < 2:
            errors.append(f"quarantined channel lacks two consecutive failures: {channel_code}")

    runtime_environment_ids: set[str] = set()
    runtime_environment_by_id: dict[str, dict[str, Any]] = {}
    runtime_windows: dict[str, tuple[datetime, datetime]] = {}
    runtime_environments = state.get("runtime_environments")
    if not isinstance(runtime_environments, list):
        errors.append("runtime_environments must be a list")
        runtime_environments = []
    for environment in runtime_environments:
        if not isinstance(environment, dict):
            errors.append("runtime environment records must be objects")
            continue
        environment_id = environment.get("environment_id")
        if set(environment) != RUNTIME_ENVIRONMENT_KEYS:
            errors.append(
                f"runtime environment fields are not allowlisted for {environment_id}"
            )
        if (
            not isinstance(environment_id, str)
            or not RUNTIME_ENVIRONMENT_ID_RE.fullmatch(environment_id)
            or environment_id in runtime_environment_ids
        ):
            errors.append("runtime environment IDs must be unique and well formed")
        else:
            runtime_environment_ids.add(environment_id)
            runtime_environment_by_id[environment_id] = environment
        if environment.get("qualification_status") != "VERIFIED_DISPOSABLE_RUNTIME":
            errors.append(f"runtime environment is not verified for {environment_id}")
        if environment.get("isolation_class") != "QUALIFIED_ONE_TIME_RUNTIME":
            errors.append(f"runtime environment has invalid isolation class for {environment_id}")
        for field, required in (
            ("disposable", True),
            ("fresh_instance", True),
            ("host_home_mounted", False),
            ("company_data_mounted", False),
            ("model_credentials_present", False),
            ("github_write_credentials_present", False),
        ):
            if environment.get(field) is not required:
                errors.append(f"runtime environment violates isolation field {field}: {environment_id}")
        for prefix in ("dependency", "test"):
            policy = environment.get(f"{prefix}_network_policy")
            hosts = environment.get(f"{prefix}_host_codes")
            if policy not in {"DENY_ALL", "ALLOWLISTED"}:
                errors.append(f"invalid {prefix} network policy for {environment_id}")
            if (
                not isinstance(hosts, list)
                or any(
                    not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                    for item in hosts
                )
                or len(set(hosts)) != len(hosts)
                or (policy == "DENY_ALL" and hosts)
                or (policy == "ALLOWLISTED" and not hosts)
            ):
                errors.append(f"invalid {prefix} network host codes for {environment_id}")
        if not isinstance(environment.get("verifier_code"), str) or not CODE_VALUE_RE.fullmatch(
            environment.get("verifier_code", "")
        ):
            errors.append(f"invalid runtime verifier for {environment_id}")
        if not isinstance(environment.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
            environment.get("evidence_digest_sha256", "")
        ):
            errors.append(f"invalid runtime evidence digest for {environment_id}")
        try:
            qualified_at = parse_time(environment.get("qualified_at", ""))
            expires_at = parse_time(environment.get("expires_at", ""))
            if expires_at <= qualified_at:
                errors.append(f"runtime qualification window is empty for {environment_id}")
            elif isinstance(environment_id, str):
                runtime_windows[environment_id] = (qualified_at, expires_at)
        except ConfigError:
            errors.append(f"invalid runtime qualification timing for {environment_id}")

    runtime_claim_ids: set[str] = set()
    claimed_runtime_environment_ids: set[str] = set()
    runtime_claims = state.get("runtime_environment_claims")
    if not isinstance(runtime_claims, list):
        errors.append("runtime_environment_claims must be a list")
        runtime_claims = []
    for claim in runtime_claims:
        if not isinstance(claim, dict):
            errors.append("runtime environment claim records must be objects")
            continue
        claim_id = claim.get("claim_id")
        environment_id = claim.get("environment_id")
        if set(claim) != RUNTIME_CLAIM_KEYS:
            errors.append(f"runtime claim fields are not allowlisted for {claim_id}")
        if (
            not isinstance(claim_id, str)
            or not RUNTIME_CLAIM_ID_RE.fullmatch(claim_id)
            or claim_id in runtime_claim_ids
        ):
            errors.append("runtime claim IDs must be unique and well formed")
        else:
            runtime_claim_ids.add(claim_id)
        if environment_id not in runtime_environment_ids:
            errors.append(f"runtime claim references unknown environment for {claim_id}")
        elif environment_id in claimed_runtime_environment_ids:
            errors.append(f"disposable runtime environment was claimed more than once: {environment_id}")
        else:
            claimed_runtime_environment_ids.add(environment_id)
        round_id = claim.get("round_id")
        if not isinstance(round_id, str) or not round_id.startswith("AEG-R-"):
            errors.append(f"runtime claim has invalid round ID for {claim_id}")
        try:
            claimed_at = parse_time(claim.get("claimed_at", ""))
            window = runtime_windows.get(environment_id)
            if window is not None and not (window[0] <= claimed_at < window[1]):
                errors.append(f"runtime claim falls outside qualification window for {claim_id}")
        except ConfigError:
            errors.append(f"runtime claim has invalid time for {claim_id}")

    effect_events = state.get("effect_events")
    if not isinstance(effect_events, list):
        errors.append("effect_events must be a list")
        effect_events = []
    oracle_effect_records = [
        item
        for item in [*effect_events, state.get("pending_effect")]
        if isinstance(item, dict) and item.get("effect_type") == "RUN_FROZEN_ORACLE"
    ]
    for effect in oracle_effect_records:
        effect_id = effect.get("effect_id")
        outcome = effect.get("outcome")
        if outcome is None:
            expected_keys = ORACLE_EFFECT_INTENT_KEYS
        elif outcome == "COMPLETED":
            expected_keys = ORACLE_EFFECT_COMPLETED_KEYS
        elif outcome == "FAILED":
            expected_keys = ORACLE_EFFECT_FAILED_KEYS
        elif outcome == "NOT_PERFORMED":
            expected_keys = ORACLE_EFFECT_NOT_PERFORMED_KEYS
        else:
            expected_keys = set()
            errors.append(f"invalid frozen-oracle effect outcome for {effect_id}")
        if set(effect) != expected_keys:
            errors.append(f"frozen-oracle effect fields are not allowlisted for {effect_id}")
        if not isinstance(effect_id, str) or not EFFECT_ID_RE.fullmatch(effect_id):
            errors.append("frozen-oracle effect ID is not well formed")
        environment_id = effect.get("environment_id")
        round_id = effect.get("round_id")
        if environment_id not in runtime_environment_ids or not any(
            claim.get("environment_id") == environment_id and claim.get("round_id") == round_id
            for claim in runtime_claims
            if isinstance(claim, dict)
        ):
            errors.append(f"frozen-oracle effect lacks its runtime claim for {effect_id}")
        for field in ("oracle_kind", "target_code"):
            if not isinstance(effect.get(field), str) or not CODE_VALUE_RE.fullmatch(
                effect.get(field, "")
            ):
                errors.append(f"invalid frozen-oracle {field} for {effect_id}")
        if not isinstance(effect.get("target_revision"), str) or not SHA_RE.fullmatch(
            effect.get("target_revision", "")
        ):
            errors.append(f"invalid frozen-oracle target revision for {effect_id}")
        try:
            recorded_at = parse_time(effect.get("recorded_at", ""))
            if outcome is not None:
                resolved_at = parse_time(effect.get("resolved_at", ""))
                if resolved_at < recorded_at:
                    errors.append(f"frozen-oracle effect timing is reversed for {effect_id}")
        except ConfigError:
            errors.append(f"invalid frozen-oracle effect timing for {effect_id}")
        if outcome == "COMPLETED":
            command = effect.get("command_argv")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(item, str) or not item for item in command)
            ):
                errors.append(f"frozen-oracle effect lacks command argv for {effect_id}")
            if type(effect.get("exit_code")) is not int:
                errors.append(f"frozen-oracle effect lacks exit status for {effect_id}")
            if effect.get("oracle_observation") not in {"SUCCESS", "FAILURE"}:
                errors.append(f"frozen-oracle effect has invalid observation for {effect_id}")
            if not isinstance(effect.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
                effect.get("evidence_digest_sha256", "")
            ):
                errors.append(f"frozen-oracle effect lacks evidence digest for {effect_id}")
            evidence_codes = effect.get("evidence_summary_codes")
            if (
                not isinstance(evidence_codes, list)
                or not evidence_codes
                or any(
                    not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                    for item in evidence_codes
                )
                or len(set(evidence_codes)) != len(evidence_codes)
            ):
                errors.append(f"frozen-oracle effect has invalid evidence summary for {effect_id}")
        elif outcome == "FAILED" and (
            not isinstance(effect.get("failure_code"), str)
            or not CODE_VALUE_RE.fullmatch(effect.get("failure_code", ""))
        ):
            errors.append(f"failed frozen-oracle effect lacks a failure code for {effect_id}")

    worker_event_ids: set[str] = set()
    worker_events = state.get("worker_events")
    if not isinstance(worker_events, list):
        errors.append("worker_events must be a list")
        worker_events = []
    for event in worker_events:
        if not isinstance(event, dict):
            errors.append("worker event records must be objects")
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or event_id in worker_event_ids:
            errors.append("worker event IDs must be unique strings")
        else:
            worker_event_ids.add(event_id)
        if event.get("record_schema_version") != 2:
            continue
        status = event.get("status")
        terminal = status != "STARTED"
        expected_keys = WORKER_EVENT_V2_TERMINAL_KEYS if terminal else WORKER_EVENT_V2_STARTED_KEYS
        if set(event) != expected_keys:
            errors.append(f"worker event v2 fields are not allowlisted for {event_id}")
        if event.get("channel_code") not in channels:
            errors.append(f"worker event references unknown channel for {event_id}")
        if not isinstance(event.get("model"), str) or not event.get("model"):
            errors.append(f"worker event lacks actual model for {event_id}")
        if not isinstance(event.get("configured_model"), str) or not event.get(
            "configured_model"
        ):
            errors.append(f"worker event lacks configured model for {event_id}")
        if not isinstance(event.get("call_method"), str) or not CODE_VALUE_RE.fullmatch(
            event.get("call_method", "")
        ):
            errors.append(f"worker event has invalid call method for {event_id}")
        try:
            parse_time(event.get("started_at", ""))
        except ConfigError:
            errors.append(f"worker event has invalid start time for {event_id}")
        if not terminal:
            continue
        if status not in {
            "PASSED",
            "FAILED",
            "INFRASTRUCTURE_FAILED",
            "AUTH_FAILED",
            "QUOTA_FAILED",
        }:
            errors.append(f"worker event has invalid terminal status for {event_id}")
        try:
            parse_time(event.get("completed_at", ""))
        except ConfigError:
            errors.append(f"worker event has invalid completion time for {event_id}")
        for field in ("compute_usd", "market_estimate_usd"):
            if not valid_decimal_measurement(event.get(field)):
                errors.append(f"worker event has invalid {field} for {event_id}")
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            if not valid_token_measurement(event.get(field)):
                errors.append(f"worker event has invalid {field} for {event_id}")
        token_values = tuple(
            event.get(field) for field in ("input_tokens", "output_tokens", "total_tokens")
        )
        if all(value != "UNKNOWN" for value in token_values) and all(
            valid_token_measurement(value) for value in token_values
        ) and int(token_values[0]) + int(token_values[1]) != int(token_values[2]):
            errors.append(f"worker event token total mismatch for {event_id}")
        for field in (
            "compute_cost_basis_code",
            "market_estimate_source_code",
            "model_attestation",
        ):
            if not isinstance(event.get(field), str) or not CODE_VALUE_RE.fullmatch(
                event.get(field, "")
            ):
                errors.append(f"worker event has invalid {field} for {event_id}")
        if event.get("compute_usd") != "UNKNOWN" and event.get(
            "compute_cost_basis_code"
        ) == "UNKNOWN":
            errors.append(f"worker event known cost lacks basis for {event_id}")
        if event.get("market_estimate_usd") != "UNKNOWN" and event.get(
            "market_estimate_source_code"
        ) == "UNKNOWN":
            errors.append(f"worker event market estimate lacks source for {event_id}")
        if not isinstance(event.get("retry_count"), int) or event.get("retry_count", -1) < 0:
            errors.append(f"worker event has invalid retry count for {event_id}")

    candidate_ids: set[str] = set()
    candidate_by_id: dict[str, dict[str, Any]] = {}
    dedupe: set[tuple[str, int]] = set()
    for candidate in backlog.get("candidates", []):
        if not isinstance(candidate, dict):
            errors.append("candidate records must be objects")
            continue
        candidate_id = candidate.get("candidate_id")
        repository = candidate.get("repository")
        number = candidate.get("issue_number")
        if (
            not isinstance(candidate_id, str)
            or not CANDIDATE_ID_RE.fullmatch(candidate_id)
            or candidate_id in candidate_ids
        ):
            errors.append("candidate IDs must be unique and well formed")
        else:
            candidate_ids.add(candidate_id)
            candidate_by_id[candidate_id] = candidate
        if set(candidate) != CANDIDATE_KEYS:
            errors.append(f"candidate fields are not allowlisted for {candidate_id}")
        if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
            errors.append(f"invalid repository for {candidate_id}")
        if not isinstance(number, int) or number <= 0:
            errors.append(f"invalid issue number for {candidate_id}")
        elif isinstance(repository, str):
            identity = (repository.lower(), number)
            if identity in dedupe:
                errors.append(f"duplicate candidate source {identity}")
            dedupe.add(identity)
        url = candidate.get("source_url")
        if not isinstance(url, str) or not GITHUB_ISSUE_RE.fullmatch(url):
            errors.append(f"invalid source URL for {candidate_id}")
        if candidate.get("category") not in {
            "RETROSPECTIVE_REPRODUCTION",
            "PROSPECTIVE_REPAIR",
            "HELD_OUT_TRANSFER",
        }:
            errors.append(f"invalid category for {candidate_id}")
        if candidate.get("qualification") not in {"QUALIFIED", "NOT_QUALIFIED"}:
            errors.append(f"invalid qualification for {candidate_id}")
        if candidate.get("contamination") not in {"LOW", "MODERATE", "HIGH", "UNKNOWN"}:
            errors.append(f"invalid contamination for {candidate_id}")
        if candidate.get("source_state") not in {"OPEN", "CLOSED"}:
            errors.append(f"invalid source state for {candidate_id}")
        for field in ("family", "oracle_kind"):
            if not isinstance(candidate.get(field), str) or not CODE_VALUE_RE.fullmatch(
                candidate.get(field, "")
            ):
                errors.append(f"invalid {field} for {candidate_id}")

    task_ids: set[str] = set()
    task_by_id: dict[str, dict[str, Any]] = {}
    in_progress: list[dict[str, Any]] = []
    for task in backlog.get("work_items", []):
        if not isinstance(task, dict):
            errors.append("work item records must be objects")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task_id in task_ids:
            errors.append("task IDs must be unique strings")
        else:
            task_ids.add(task_id)
            task_by_id[task_id] = task
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"invalid status for {task_id}")
        if task.get("stage") not in STAGES:
            errors.append(f"invalid stage for {task_id}")
        channel_code = task.get("channel_code")
        if channel_code not in channels:
            errors.append(f"unknown execution channel for {task_id}")
        if not set(task.get("candidate_ids", [])).issubset(candidate_ids):
            errors.append(f"unknown candidate reference for {task_id}")
        if task.get("status") == "IN_PROGRESS":
            in_progress.append(task)
            if not isinstance(task.get("claim"), dict):
                errors.append(f"in-progress task {task_id} has no claim")

    behavior_verifications = backlog.get("behavior_verifications")
    if not isinstance(behavior_verifications, list):
        errors.append("behavior_verifications must be a list")
        behavior_verifications = []
    verification_ids: set[str] = set()
    verified_candidate_ids: set[str] = set()
    for verification in behavior_verifications:
        if not isinstance(verification, dict):
            errors.append("behavior verification records must be objects")
            continue
        verification_id = verification.get("verification_id")
        if set(verification) != BEHAVIOR_VERIFICATION_KEYS:
            errors.append(f"behavior verification fields are not allowlisted for {verification_id}")
        if (
            not isinstance(verification_id, str)
            or not BEHAVIOR_ID_RE.fullmatch(verification_id)
            or verification_id in verification_ids
        ):
            errors.append("behavior verification IDs must be unique and well formed")
        else:
            verification_ids.add(verification_id)
        candidate_id = verification.get("candidate_id")
        candidate = candidate_by_id.get(candidate_id) if isinstance(candidate_id, str) else None
        if (
            candidate is None
            or candidate.get("qualification") != "QUALIFIED"
            or candidate.get("category") == "HELD_OUT_TRANSFER"
        ):
            errors.append(f"behavior verification requires a qualified non-held-out candidate: {verification_id}")
        task_id = verification.get("task_id")
        task = task_by_id.get(task_id)
        if (
            task is None
            or task.get("stage") != "VERIFICATION"
            or task.get("status") != "COMPLETED"
            or candidate_id not in task.get("candidate_ids", [])
        ):
            errors.append(f"invalid completed verification work item for {verification_id}")
        for field in ("target_revision", "result_revision"):
            if not isinstance(verification.get(field), str) or not SHA_RE.fullmatch(
                verification.get(field, "")
            ):
                errors.append(f"invalid frozen {field} for {verification_id}")
        oracle_kind = verification.get("oracle_kind")
        if (
            not isinstance(oracle_kind, str)
            or not CODE_VALUE_RE.fullmatch(oracle_kind)
            or (candidate is not None and oracle_kind != candidate.get("oracle_kind"))
        ):
            errors.append(f"invalid frozen oracle for {verification_id}")
        if not isinstance(verification.get("oracle_version"), int) or verification.get(
            "oracle_version", 0
        ) <= 0:
            errors.append(f"invalid oracle version for {verification_id}")
        model_config = verification.get("model_config")
        if (
            not isinstance(model_config, dict)
            or set(model_config) != {"model", "reasoning_effort"}
            or any(not isinstance(value, str) or not value for value in model_config.values())
        ):
            errors.append(f"invalid frozen model configuration for {verification_id}")
        budget = verification.get("budget")
        if (
            not isinstance(budget, dict)
            or set(budget) != {"max_retries", "max_seconds", "max_worker_starts"}
            or any(
                not isinstance(budget.get(field), int) or budget[field] < minimum
                for field, minimum in (
                    ("max_retries", 0),
                    ("max_seconds", 1),
                    ("max_worker_starts", 1),
                )
            )
        ):
            errors.append(f"invalid verification budget for {verification_id}")
        solver_code = verification.get("solver_code")
        verifier_code = verification.get("verifier_code")
        if (
            not isinstance(solver_code, str)
            or not CODE_VALUE_RE.fullmatch(solver_code)
            or not isinstance(verifier_code, str)
            or not CODE_VALUE_RE.fullmatch(verifier_code)
            or solver_code == verifier_code
        ):
            errors.append(f"independent verifier missing for {verification_id}")
        try:
            started_at = parse_time(verification.get("started_at", ""))
            finished_at = parse_time(verification.get("finished_at", ""))
            if finished_at < started_at:
                errors.append(f"verification timing is reversed for {verification_id}")
        except ConfigError:
            errors.append(f"invalid verification timing for {verification_id}")
        arms: dict[str, dict[str, Any]] = {}
        for arm_name in ("baseline", "repaired"):
            arm = verification.get(arm_name)
            if not isinstance(arm, dict) or set(arm) != BEHAVIOR_ARM_KEYS:
                errors.append(f"invalid {arm_name} evidence fields for {verification_id}")
                continue
            arms[arm_name] = arm
            for code_field in ("environment_code", "workspace_code"):
                if not isinstance(arm.get(code_field), str) or not CODE_VALUE_RE.fullmatch(
                    arm.get(code_field, "")
                ):
                    errors.append(f"invalid {arm_name} {code_field} for {verification_id}")
            command = arm.get("command_argv")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(item, str) or not item for item in command)
            ):
                errors.append(f"missing {arm_name} oracle command for {verification_id}")
            if not isinstance(arm.get("exit_code"), int):
                errors.append(f"missing {arm_name} oracle exit status for {verification_id}")
            if arm.get("oracle_observation") not in {"SUCCESS", "FAILURE"}:
                errors.append(f"invalid {arm_name} oracle observation for {verification_id}")
            if not isinstance(arm.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
                arm.get("evidence_digest_sha256", "")
            ):
                errors.append(f"invalid {arm_name} evidence digest for {verification_id}")
            evidence_codes = arm.get("evidence_summary_codes")
            if (
                not isinstance(evidence_codes, list)
                or not evidence_codes
                or any(
                    not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                    for item in evidence_codes
                )
                or len(set(evidence_codes)) != len(evidence_codes)
            ):
                errors.append(f"invalid {arm_name} evidence summary for {verification_id}")
        if len(arms) == 2 and (
            arms["baseline"].get("environment_code") == arms["repaired"].get("environment_code")
            or arms["baseline"].get("workspace_code") == arms["repaired"].get("workspace_code")
        ):
            errors.append(f"baseline and repaired verification are not isolated: {verification_id}")
        status = verification.get("status")
        outcome = verification.get("outcome")
        if status not in {"COMPLETED", "INVALID"}:
            errors.append(f"invalid behavior verification status for {verification_id}")
        if outcome not in {"VERIFIED_REPAIR", "FAILED", "INVALID"}:
            errors.append(f"invalid behavior verification outcome for {verification_id}")
        observations = tuple(
            arms.get(name, {}).get("oracle_observation") for name in ("baseline", "repaired")
        )
        if status == "COMPLETED" and outcome == "VERIFIED_REPAIR":
            if observations != ("FAILURE", "SUCCESS"):
                errors.append(f"verified repair arm results disagree for {verification_id}")
            elif isinstance(candidate_id, str):
                if candidate_id in verified_candidate_ids:
                    errors.append(f"candidate has duplicate verified behavior: {candidate_id}")
                verified_candidate_ids.add(candidate_id)
        elif status == "COMPLETED":
            errors.append(f"completed behavior verification is not a verified repair: {verification_id}")

    experiences = backlog.get("experiences")
    if not isinstance(experiences, list):
        errors.append("experiences must be a list")
        experiences = []
    experience_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    ready_versions_by_id: dict[str, int] = {}
    for experience in experiences:
        if not isinstance(experience, dict):
            errors.append("Experience records must be objects")
            continue
        experience_id = experience.get("experience_id")
        version = experience.get("version")
        key = (experience_id, version)
        if (
            not isinstance(experience_id, str)
            or not EXPERIENCE_ID_RE.fullmatch(experience_id)
            or not isinstance(version, int)
            or version <= 0
            or key in experience_by_key
        ):
            errors.append("Experience identity/version must be unique and well formed")
            continue
        experience_by_key[key] = experience
        source_candidates = experience.get("source_candidate_ids")
        builders = experience.get("builder_task_ids")
        if (
            not isinstance(source_candidates, list)
            or not source_candidates
            or any(not isinstance(item, str) for item in source_candidates)
            or len(set(source_candidates)) != len(source_candidates)
            or not set(source_candidates).issubset(candidate_ids)
        ):
            errors.append(f"invalid source candidates for {experience_id} v{version}")
        elif any(
            candidate_by_id[item].get("category") == "HELD_OUT_TRANSFER"
            for item in source_candidates
        ):
            errors.append(f"held-out candidate used to build {experience_id} v{version}")
        if (
            not isinstance(builders, list)
            or not builders
            or any(not isinstance(item, str) for item in builders)
            or len(set(builders)) != len(builders)
            or not set(builders).issubset(task_ids)
        ):
            errors.append(f"invalid builder tasks for {experience_id} v{version}")
        elif any(task_by_id[item].get("stage") == "TRANSFER_EVALUATION" for item in builders):
            errors.append(f"transfer task used to build {experience_id} v{version}")
        artifact_path = experience.get("artifact_path")
        artifact_path_valid = not (
            not isinstance(artifact_path, str)
            or not artifact_path.startswith("foundry/experiences/")
            or artifact_path.startswith("/")
            or ".." in Path(artifact_path).parts
            or len(Path(artifact_path).parts) != 3
            or not artifact_path.endswith(".json")
        )
        if not artifact_path_valid:
            errors.append(f"invalid artifact path for {experience_id} v{version}")
        else:
            artifact_file = root / artifact_path
            artifact_sha = experience.get("artifact_sha256")
            if not artifact_file.is_file():
                errors.append(f"missing Experience artifact for {experience_id} v{version}")
            elif not isinstance(artifact_sha, str) or not SHA256_RE.fullmatch(artifact_sha):
                errors.append(f"invalid artifact digest for {experience_id} v{version}")
            elif sha256_bytes(artifact_file.read_bytes()) != artifact_sha:
                errors.append(f"artifact digest mismatch for {experience_id} v{version}")
            else:
                artifact = load_json(artifact_file)
                if not isinstance(artifact, dict) or set(artifact) != EXPERIENCE_ARTIFACT_KEYS:
                    errors.append(f"artifact fields are not allowlisted for {experience_id} v{version}")
                else:
                    if (
                        artifact.get("schema_version") != 1
                        or artifact.get("experience_id") != experience_id
                        or artifact.get("version") != version
                        or artifact.get("family") != experience.get("family")
                        or artifact.get("source_candidate_ids") != source_candidates
                    ):
                        errors.append(f"artifact identity/provenance mismatch for {experience_id} v{version}")
                    for field in (
                        "problem_signature_codes",
                        "precondition_codes",
                        "limitation_codes",
                    ):
                        values = artifact.get(field)
                        if (
                            not isinstance(values, list)
                            or (field != "limitation_codes" and not values)
                            or any(
                                not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                                for item in values
                            )
                            or len(set(values)) != len(values)
                        ):
                            errors.append(f"invalid allowlisted {field} for {experience_id} v{version}")
                    if not isinstance(artifact.get("oracle_kind"), str) or not CODE_VALUE_RE.fullmatch(
                        artifact.get("oracle_kind", "")
                    ):
                        errors.append(f"invalid artifact oracle for {experience_id} v{version}")
                    steps = artifact.get("procedure_steps")
                    if not isinstance(steps, list) or not steps:
                        errors.append(f"missing artifact procedure for {experience_id} v{version}")
                    else:
                        for step in steps:
                            if not isinstance(step, dict) or set(step) != {
                                "action_code",
                                "verification_code",
                            } or any(
                                not isinstance(value, str) or not CODE_VALUE_RE.fullmatch(value)
                                for value in step.values()
                            ):
                                errors.append(
                                    f"invalid allowlisted procedure step for {experience_id} v{version}"
                                )
                                break
        if experience.get("family") != backlog.get("discovery", {}).get("selected_family"):
            errors.append(f"Experience family drift for {experience_id} v{version}")
        review_status = experience.get("release_review_status")
        if review_status not in {"NOT_READY", "READY"}:
            errors.append(f"invalid release review status for {experience_id} v{version}")
        elif review_status == "READY":
            if experience_id in ready_versions_by_id:
                errors.append(f"multiple release-ready versions for {experience_id}")
            ready_versions_by_id[experience_id] = version
            if not isinstance(source_candidates, list) or not set(source_candidates).issubset(
                verified_candidate_ids
            ):
                errors.append(
                    f"release-ready Experience lacks independently verified sources: {experience_id} v{version}"
                )

    transfer_evaluations = backlog.get("transfer_evaluations")
    if not isinstance(transfer_evaluations, list):
        errors.append("transfer_evaluations must be a list")
        transfer_evaluations = []
    transfer_ids: set[str] = set()
    transfer_targets: set[tuple[str, int, str]] = set()
    transfer_attempt_ids: set[str] = set()
    completed_transfer_keys: set[tuple[str, int]] = set()
    for transfer in transfer_evaluations:
        if not isinstance(transfer, dict):
            errors.append("transfer evaluation records must be objects")
            continue
        transfer_id = transfer.get("transfer_id")
        if set(transfer) != TRANSFER_EVALUATION_KEYS:
            errors.append(f"transfer fields are not allowlisted for {transfer_id}")
        if (
            not isinstance(transfer_id, str)
            or not TRANSFER_ID_RE.fullmatch(transfer_id)
            or transfer_id in transfer_ids
        ):
            errors.append("transfer IDs must be unique and well formed")
        else:
            transfer_ids.add(transfer_id)
        transfer_experience_id = transfer.get("experience_id")
        transfer_experience_version = transfer.get("experience_version")
        if not isinstance(transfer_experience_id, str) or not isinstance(
            transfer_experience_version, int
        ):
            errors.append(f"invalid Experience reference for {transfer_id}")
            experience_key = ("INVALID", -1)
        else:
            experience_key = (transfer_experience_id, transfer_experience_version)
        experience = experience_by_key.get(experience_key)
        if experience is None:
            errors.append(f"unknown Experience version for {transfer_id}")
        target_id = transfer.get("target_candidate_id")
        target = candidate_by_id.get(target_id) if isinstance(target_id, str) else None
        if (
            target is None
            or target.get("category") != "HELD_OUT_TRANSFER"
            or target.get("qualification") != "QUALIFIED"
        ):
            errors.append(f"transfer target must be a qualified held-out candidate for {transfer_id}")
        target_key = (*experience_key, target_id if isinstance(target_id, str) else "INVALID")
        if target_key in transfer_targets:
            errors.append(f"duplicate Experience/target transfer for {transfer_id}")
        transfer_targets.add(target_key)
        task_id = transfer.get("task_id")
        task = task_by_id.get(task_id)
        if task is None or task.get("stage") != "TRANSFER_EVALUATION" or target_id not in task.get(
            "candidate_ids", []
        ):
            errors.append(f"invalid transfer work item for {transfer_id}")
        if experience and (
            target_id in experience.get("source_candidate_ids", [])
            or task_id in experience.get("builder_task_ids", [])
        ):
            errors.append(f"held-out separation violated for {transfer_id}")
        if not isinstance(transfer.get("target_revision"), str) or not SHA_RE.fullmatch(
            transfer.get("target_revision", "")
        ):
            errors.append(f"invalid frozen target revision for {transfer_id}")
        if not isinstance(transfer.get("oracle_kind"), str) or not transfer.get("oracle_kind"):
            errors.append(f"missing frozen oracle for {transfer_id}")
        if not isinstance(transfer.get("oracle_version"), int) or transfer.get(
            "oracle_version", 0
        ) <= 0:
            errors.append(f"invalid oracle version for {transfer_id}")
        try:
            parse_time(transfer.get("preregistered_at", ""))
        except ConfigError:
            errors.append(f"invalid preregistration time for {transfer_id}")
        model_config = transfer.get("model_config")
        if not isinstance(model_config, dict) or not model_config.get("model") or not model_config.get(
            "reasoning_effort"
        ):
            errors.append(f"invalid frozen model config for {transfer_id}")
        budget = transfer.get("budget")
        if not isinstance(budget, dict) or any(
            not isinstance(budget.get(field), int) or budget[field] < minimum
            for field, minimum in (("max_seconds", 1), ("max_worker_starts", 1), ("max_retries", 0))
        ):
            errors.append(f"invalid frozen transfer budget for {transfer_id}")
        if transfer.get("run_order") not in {"BASELINE_FIRST", "ASSISTED_FIRST"}:
            errors.append(f"invalid frozen run order for {transfer_id}")
        if transfer.get("decision_rule_code") != TRANSFER_DECISION_RULE:
            errors.append(f"invalid frozen decision rule for {transfer_id}")
        if not isinstance(transfer.get("retry_rule_code"), str) or not transfer.get(
            "retry_rule_code"
        ):
            errors.append(f"missing retry rule for {transfer_id}")
        if not isinstance(transfer.get("tool_permission_profile"), str) or not transfer.get(
            "tool_permission_profile"
        ):
            errors.append(f"missing shared tool permission profile for {transfer_id}")
        if transfer.get("evaluator_feedback_visible_to_assisted") is not False:
            errors.append(f"evaluator feedback leakage not forbidden for {transfer_id}")
        visibility = transfer.get("visible_material_codes")
        experience_token = f"EXPERIENCE:{experience_key[0]}:V{experience_key[1]}"
        if (
            not isinstance(visibility, dict)
            or set(visibility) != {"baseline", "assisted"}
            or not isinstance(visibility.get("baseline"), list)
            or not isinstance(visibility.get("assisted"), list)
            or any(
                not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                for arm_values in visibility.values()
                if isinstance(arm_values, list)
                for item in arm_values
            )
            or any(item.startswith("EXPERIENCE:") for item in visibility.get("baseline", []))
            or [
                item for item in visibility.get("assisted", []) if item.startswith("EXPERIENCE:")
            ]
            != [experience_token]
        ):
            errors.append(f"invalid arm visibility freeze for {transfer_id}")
        arms: dict[str, dict[str, Any]] = {}
        preregistered_at: datetime | None = None
        try:
            preregistered_at = parse_time(transfer.get("preregistered_at", ""))
        except ConfigError:
            pass
        for arm_name in ("baseline", "assisted"):
            arm = transfer.get(arm_name)
            if not isinstance(arm, dict):
                errors.append(f"missing {arm_name} arm for {transfer_id}")
                continue
            arms[arm_name] = arm
            if set(arm) != TRANSFER_ARM_KEYS:
                errors.append(f"{arm_name} arm fields are not allowlisted for {transfer_id}")
            if not isinstance(arm.get("context_code"), str) or not CODE_VALUE_RE.fullmatch(
                arm.get("context_code", "")
            ):
                errors.append(f"missing {arm_name} context for {transfer_id}")
            if not isinstance(arm.get("workspace_code"), str) or not CODE_VALUE_RE.fullmatch(
                arm.get("workspace_code", "")
            ):
                errors.append(f"missing {arm_name} workspace for {transfer_id}")
            if not isinstance(arm.get("environment_code"), str) or not CODE_VALUE_RE.fullmatch(
                arm.get("environment_code", "")
            ):
                errors.append(f"missing {arm_name} environment for {transfer_id}")
            if arm.get("run_status") not in {"PENDING", "VALID", "INVALID", "FAILED"}:
                errors.append(f"invalid {arm_name} run status for {transfer_id}")
            if arm.get("oracle_observation") not in {"PENDING", "SUCCESS", "FAILURE", "NOT_RUN"}:
                errors.append(f"invalid {arm_name} oracle observation for {transfer_id}")
            attempts = arm.get("attempts")
            if not isinstance(attempts, list):
                errors.append(f"invalid {arm_name} attempt ledger for {transfer_id}")
                attempts = []
            max_attempts = (
                budget.get("max_retries", -1) + 1 if isinstance(budget, dict) else 0
            )
            if len(attempts) > max_attempts:
                errors.append(f"{arm_name} attempt ledger exceeds frozen retry budget for {transfer_id}")
            for attempt_number, attempt in enumerate(attempts, 1):
                if not isinstance(attempt, dict) or set(attempt) != TRANSFER_ATTEMPT_KEYS:
                    errors.append(f"invalid {arm_name} attempt fields for {transfer_id}")
                    continue
                attempt_id = attempt.get("attempt_id")
                if (
                    not isinstance(attempt_id, str)
                    or not CODE_VALUE_RE.fullmatch(attempt_id)
                    or attempt_id in transfer_attempt_ids
                ):
                    errors.append(f"invalid or duplicate transfer attempt ID for {transfer_id}")
                else:
                    transfer_attempt_ids.add(attempt_id)
                if attempt.get("attempt_number") != attempt_number:
                    errors.append(f"non-sequential {arm_name} attempt ledger for {transfer_id}")
                attempt_status = attempt.get("run_status")
                attempt_observation = attempt.get("oracle_observation")
                if attempt_status not in {"VALID", "INVALID", "FAILED"}:
                    errors.append(f"invalid {arm_name} attempt status for {transfer_id}")
                if attempt_observation not in {"SUCCESS", "FAILURE", "NOT_RUN"}:
                    errors.append(f"invalid {arm_name} attempt observation for {transfer_id}")
                if attempt_status == "VALID" and attempt_observation not in {
                    "SUCCESS",
                    "FAILURE",
                }:
                    errors.append(f"valid {arm_name} attempt lacks oracle result for {transfer_id}")
                if attempt_status != "VALID" and attempt_observation == "SUCCESS":
                    errors.append(f"non-valid {arm_name} attempt claims success for {transfer_id}")
                command = attempt.get("command_argv")
                if (
                    not isinstance(command, list)
                    or not command
                    or any(not isinstance(item, str) or not item for item in command)
                ):
                    errors.append(f"missing {arm_name} oracle command for {transfer_id}")
                if not isinstance(attempt.get("exit_code"), int):
                    errors.append(f"missing {arm_name} oracle exit status for {transfer_id}")
                if not isinstance(attempt.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
                    attempt.get("evidence_digest_sha256", "")
                ):
                    errors.append(f"invalid {arm_name} evidence digest for {transfer_id}")
                evidence_codes = attempt.get("evidence_summary_codes")
                if (
                    not isinstance(evidence_codes, list)
                    or not evidence_codes
                    or any(
                        not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                        for item in evidence_codes
                    )
                    or len(set(evidence_codes)) != len(evidence_codes)
                ):
                    errors.append(f"invalid {arm_name} evidence summary for {transfer_id}")
                solver_code = attempt.get("solver_code")
                oracle_executor_code = attempt.get("oracle_executor_code")
                if (
                    not isinstance(solver_code, str)
                    or not CODE_VALUE_RE.fullmatch(solver_code)
                    or not isinstance(oracle_executor_code, str)
                    or not CODE_VALUE_RE.fullmatch(oracle_executor_code)
                    or solver_code == oracle_executor_code
                ):
                    errors.append(f"independent oracle executor missing for {transfer_id}")
                try:
                    started_at = parse_time(attempt.get("started_at", ""))
                    finished_at = parse_time(attempt.get("finished_at", ""))
                    if (
                        preregistered_at is None
                        or started_at < preregistered_at
                        or finished_at < started_at
                    ):
                        errors.append(f"attempt timing violates preregistration for {transfer_id}")
                except ConfigError:
                    errors.append(f"invalid {arm_name} attempt timing for {transfer_id}")
            if attempts:
                terminal = attempts[-1]
                if any(item.get("run_status") == "VALID" for item in attempts[:-1]):
                    errors.append(f"{arm_name} retried after a valid terminal attempt for {transfer_id}")
                if (
                    arm.get("run_status") != terminal.get("run_status")
                    or arm.get("oracle_observation") != terminal.get("oracle_observation")
                ):
                    errors.append(f"{arm_name} summary does not match terminal attempt for {transfer_id}")
        if len(arms) == 2 and (
            arms["baseline"].get("context_code") == arms["assisted"].get("context_code")
            or arms["baseline"].get("workspace_code") == arms["assisted"].get("workspace_code")
            or arms["baseline"].get("environment_code")
            == arms["assisted"].get("environment_code")
        ):
            errors.append(f"baseline and assisted isolation violated for {transfer_id}")
        status = transfer.get("status")
        outcome = transfer.get("outcome")
        if status not in {"PREREGISTERED", "COMPLETED", "INVALID"}:
            errors.append(f"invalid transfer status for {transfer_id}")
        if outcome not in {"PENDING", "POSITIVE", "NEUTRAL", "HARMFUL", "INVALID", "FAILED"}:
            errors.append(f"invalid transfer outcome for {transfer_id}")
        if status == "PREREGISTERED" and outcome != "PENDING":
            errors.append(f"preregistered transfer has a terminal outcome for {transfer_id}")
        if status == "COMPLETED":
            if transfer.get("all_attempts_retained") is not True or any(
                arm.get("run_status") != "VALID" or not arm.get("attempts")
                for arm in arms.values()
            ):
                errors.append(f"completed transfer lacks complete valid attempts for {transfer_id}")
            else:
                completed_transfer_keys.add(experience_key)
            observations = tuple(
                arms.get(name, {}).get("oracle_observation") for name in ("baseline", "assisted")
            )
            expected = {
                "POSITIVE": ("FAILURE", "SUCCESS"),
                "HARMFUL": ("SUCCESS", "FAILURE"),
            }
            if outcome in expected and observations != expected[outcome]:
                errors.append(f"{outcome} transfer arm results disagree for {transfer_id}")
            if outcome == "NEUTRAL" and observations[0] != observations[1]:
                errors.append(f"NEUTRAL transfer arm results disagree for {transfer_id}")
            if outcome not in {"POSITIVE", "NEUTRAL", "HARMFUL"}:
                errors.append(f"completed transfer lacks a valid outcome for {transfer_id}")

    for experience_key, experience in experience_by_key.items():
        if experience.get("release_review_status") == "READY" and experience_key not in completed_transfer_keys:
            errors.append(
                f"release-ready Experience lacks an independent completed transfer: {experience_key}"
            )
    active = state.get("active_round")
    if active is None and in_progress:
        errors.append("in-progress task exists without active round")
    if active is not None:
        if len(in_progress) != 1 or in_progress[0].get("task_id") != active.get("task_id"):
            errors.append("active round and claimed task disagree")
        bound_runtime_environment_ids = active.get("runtime_environment_ids", [])
        if (
            not isinstance(bound_runtime_environment_ids, list)
            or any(
                not isinstance(item, str) or not RUNTIME_ENVIRONMENT_ID_RE.fullmatch(item)
                for item in bound_runtime_environment_ids
            )
            or len(set(bound_runtime_environment_ids)) != len(bound_runtime_environment_ids)
        ):
            errors.append("active round has an invalid disposable runtime binding list")
            bound_runtime_environment_ids = []
        for runtime_environment_id in bound_runtime_environment_ids:
            matching_claims = [
                claim
                for claim in runtime_claims
                if claim.get("environment_id") == runtime_environment_id
                and claim.get("round_id") == active.get("round_id")
            ]
            if (
                active.get("channel_code") != "DISPOSABLE_RUNTIME"
                or runtime_environment_id not in runtime_environment_ids
                or len(matching_claims) != 1
            ):
                errors.append("active round has an invalid disposable runtime binding")
    if state.get("rounds_completed", 0) > state.get("rounds_started", 0):
        errors.append("completed round count exceeds started round count")
    daily_counters = state.get("counters_by_utc_day")
    if not isinstance(daily_counters, dict):
        errors.append("daily counters must be an object")
        daily_counters = {}
    for day, counter in daily_counters.items():
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except (TypeError, ValueError):
            errors.append(f"invalid daily counter date: {day}")
        if not isinstance(counter, dict) or set(counter) != {"round_starts", "worker_starts"}:
            errors.append(f"invalid daily counter fields: {day}")
            continue
        for field, maximum in (
            ("round_starts", budgets.get("max_rounds_per_day", -1)),
            ("worker_starts", budgets.get("max_worker_starts_per_day", -1)),
        ):
            if (
                not isinstance(counter.get(field), int)
                or counter[field] < 0
                or counter[field] > maximum
            ):
                errors.append(f"daily counter exceeds fixed budget: {day}:{field}")
    if sum(
        counter.get("round_starts", 0)
        for counter in daily_counters.values()
        if isinstance(counter, dict)
    ) != state.get("rounds_started"):
        errors.append("daily round counters do not equal total starts")
    if sum(
        counter.get("worker_starts", 0)
        for counter in daily_counters.values()
        if isinstance(counter, dict)
    ) != state.get("rounds_started", 0) + len(worker_events):
        errors.append("daily worker counters do not equal scheduled plus registered starts")
    if state.get("pilot_status") not in {"ACTIVE", "PAUSED", "EXPIRED"}:
        errors.append("invalid pilot status")
    if not isinstance(state.get("founder_interventions"), int) or state.get(
        "founder_interventions", -1
    ) < 0:
        errors.append("founder interventions must be a non-negative integer")
    for state_list in ("external_users", "human_decision_queue", "integrity_incidents"):
        if not isinstance(state.get(state_list), list):
            errors.append(f"{state_list} must be a list")

    incident_ids: set[str] = set()
    integrity_incidents = state.get("integrity_incidents", [])
    if isinstance(integrity_incidents, list):
        for incident in integrity_incidents:
            if not isinstance(incident, dict):
                errors.append("integrity incident records must be objects")
                continue
            incident_id = incident.get("incident_id")
            if set(incident) != INTEGRITY_INCIDENT_KEYS:
                errors.append(f"integrity incident fields are not allowlisted for {incident_id}")
            if (
                not isinstance(incident_id, str)
                or not INTEGRITY_INCIDENT_ID_RE.fullmatch(incident_id)
                or incident_id in incident_ids
            ):
                errors.append("integrity incident IDs must be unique and well formed")
            else:
                incident_ids.add(incident_id)
            if incident.get("status") not in {"CONTROLLED", "UNCONTROLLED"}:
                errors.append(f"invalid integrity incident status for {incident_id}")
            for field in ("affected_record_code", "containment_code", "incident_code"):
                if not isinstance(incident.get(field), str) or not CODE_VALUE_RE.fullmatch(
                    incident.get(field, "")
                ):
                    errors.append(f"invalid {field} for {incident_id}")
            if not isinstance(incident.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
                incident.get("evidence_digest_sha256", "")
            ):
                errors.append(f"invalid integrity evidence digest for {incident_id}")
            try:
                parse_time(incident.get("observed_at", ""))
            except ConfigError:
                errors.append(f"invalid integrity incident time for {incident_id}")

    external_users = state.get("external_users", [])
    external_user_ids: set[str] = set()
    verified_external_user_ids: set[str] = set()
    if isinstance(external_users, list):
        for user in external_users:
            if not isinstance(user, dict):
                errors.append("external user records must be objects")
                continue
            user_id = user.get("user_id")
            if set(user) != EXTERNAL_USER_KEYS:
                errors.append(f"external user fields are not allowlisted for {user_id}")
            if (
                not isinstance(user_id, str)
                or not EXTERNAL_USER_ID_RE.fullmatch(user_id)
                or user_id in external_user_ids
            ):
                errors.append("external user IDs must be unique and well formed")
            else:
                external_user_ids.add(user_id)
            if user.get("actor_class") != "EXTERNAL":
                errors.append(f"non-external actor cannot be an external user: {user_id}")
            status = user.get("status")
            evidence_kind = user.get("evidence_kind")
            if status not in {"SELF_REPORTED", "VERIFIED_EXTERNAL_USER", "INVALID"}:
                errors.append(f"invalid external user status for {user_id}")
            if evidence_kind not in {
                "SELF_REPORT",
                "INDEPENDENT_OBSERVATION",
                "RECEIPT",
                "REPEAT_USE",
                "NEW_TASK",
            }:
                errors.append(f"invalid external user evidence kind for {user_id}")
            if status == "VERIFIED_EXTERNAL_USER":
                if evidence_kind == "SELF_REPORT" or user.get("verifier_code") == "UNVERIFIED":
                    errors.append(f"self-report cannot verify external user {user_id}")
                elif isinstance(user_id, str):
                    verified_external_user_ids.add(user_id)
            if not isinstance(user.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
                user.get("evidence_digest_sha256", "")
            ):
                errors.append(f"invalid external user evidence digest for {user_id}")
            evidence_codes = user.get("evidence_summary_codes")
            if (
                not isinstance(evidence_codes, list)
                or not evidence_codes
                or any(
                    not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                    for item in evidence_codes
                )
                or len(set(evidence_codes)) != len(evidence_codes)
            ):
                errors.append(f"invalid external user evidence summary for {user_id}")
            if not isinstance(user.get("verifier_code"), str) or not CODE_VALUE_RE.fullmatch(
                user.get("verifier_code", "")
            ):
                errors.append(f"invalid external user verifier for {user_id}")
            try:
                parse_time(user.get("observed_at", ""))
            except ConfigError:
                errors.append(f"invalid external user observation time for {user_id}")

    external_reuse_events = state.get("external_reuse_events")
    if not isinstance(external_reuse_events, list):
        errors.append("external_reuse_events must be a list")
        external_reuse_events = []
    external_reuse_ids: set[str] = set()
    for reuse in external_reuse_events:
        if not isinstance(reuse, dict):
            errors.append("external reuse records must be objects")
            continue
        reuse_id = reuse.get("reuse_id")
        if set(reuse) != EXTERNAL_REUSE_KEYS:
            errors.append(f"external reuse fields are not allowlisted for {reuse_id}")
        if (
            not isinstance(reuse_id, str)
            or not EXTERNAL_REUSE_ID_RE.fullmatch(reuse_id)
            or reuse_id in external_reuse_ids
        ):
            errors.append("external reuse IDs must be unique and well formed")
        else:
            external_reuse_ids.add(reuse_id)
        raw_user_id = reuse.get("user_id")
        user_id = raw_user_id if isinstance(raw_user_id, str) else "INVALID"
        if user_id not in external_user_ids:
            errors.append(f"external reuse references unknown user for {reuse_id}")
        raw_experience_id = reuse.get("experience_id")
        raw_experience_version = reuse.get("experience_version")
        experience_key = (
            raw_experience_id if isinstance(raw_experience_id, str) else "INVALID",
            raw_experience_version if isinstance(raw_experience_version, int) else -1,
        )
        if experience_key not in experience_by_key:
            errors.append(f"external reuse references unknown Experience for {reuse_id}")
        if not isinstance(reuse.get("target_revision"), str) or not SHA_RE.fullmatch(
            reuse.get("target_revision", "")
        ):
            errors.append(f"invalid external reuse target revision for {reuse_id}")
        if not isinstance(reuse.get("oracle_kind"), str) or not CODE_VALUE_RE.fullmatch(
            reuse.get("oracle_kind", "")
        ):
            errors.append(f"invalid external reuse oracle for {reuse_id}")
        if not isinstance(reuse.get("oracle_version"), int) or reuse.get(
            "oracle_version", 0
        ) <= 0:
            errors.append(f"invalid external reuse oracle version for {reuse_id}")
        if not isinstance(reuse.get("evidence_digest_sha256"), str) or not SHA256_RE.fullmatch(
            reuse.get("evidence_digest_sha256", "")
        ):
            errors.append(f"invalid external reuse evidence digest for {reuse_id}")
        evidence_codes = reuse.get("evidence_summary_codes")
        if (
            not isinstance(evidence_codes, list)
            or not evidence_codes
            or any(
                not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                for item in evidence_codes
            )
            or len(set(evidence_codes)) != len(evidence_codes)
        ):
            errors.append(f"invalid external reuse evidence summary for {reuse_id}")
        try:
            started_at = parse_time(reuse.get("started_at", ""))
            finished_at = parse_time(reuse.get("finished_at", ""))
            if finished_at < started_at:
                errors.append(f"external reuse timing is reversed for {reuse_id}")
        except ConfigError:
            errors.append(f"invalid external reuse timing for {reuse_id}")
        status = reuse.get("status")
        outcome = reuse.get("outcome")
        observation = reuse.get("oracle_observation")
        command = reuse.get("command_argv")
        exit_code = reuse.get("exit_code")
        environment_code = reuse.get("verification_environment_code")
        verifier_code = reuse.get("verifier_code")
        if status == "SELF_REPORTED":
            if (
                outcome != "CLAIMED_SUCCESS"
                or observation != "NOT_RUN"
                or command != []
                or exit_code is not None
                or environment_code != "UNVERIFIED"
                or verifier_code != "UNVERIFIED"
            ):
                errors.append(f"self-reported reuse claims verification for {reuse_id}")
        elif status == "VERIFIED":
            if user_id not in verified_external_user_ids:
                errors.append(f"verified reuse lacks a verified external user for {reuse_id}")
            if outcome not in {"SUCCESS", "FAILURE"} or observation != outcome:
                errors.append(f"verified reuse outcome disagrees with oracle for {reuse_id}")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(item, str) or not item for item in command)
                or not isinstance(exit_code, int)
            ):
                errors.append(f"verified reuse lacks command and exit status for {reuse_id}")
            if (
                not isinstance(environment_code, str)
                or not CODE_VALUE_RE.fullmatch(environment_code)
                or environment_code == "UNVERIFIED"
                or not isinstance(verifier_code, str)
                or not CODE_VALUE_RE.fullmatch(verifier_code)
                or verifier_code == "UNVERIFIED"
            ):
                errors.append(f"verified reuse lacks independent execution evidence for {reuse_id}")
        elif status == "INVALID":
            if outcome != "INVALID":
                errors.append(f"invalid external reuse has non-invalid outcome for {reuse_id}")
        else:
            errors.append(f"invalid external reuse status for {reuse_id}")

    errors.extend(validate_committed_foundry_history(root, backlog, state))

    seen_rounds: set[str] = set()
    successful = 0
    rounds_path = paths(root)["rounds"]
    for number, line in enumerate(rounds_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"invalid rounds JSON at line {number}")
            continue
        round_id = record.get("round_id")
        if record.get("record_schema_version") == 2:
            if set(record) != ROUND_RECORD_V2_KEYS:
                errors.append(f"round v2 fields are not allowlisted at line {number}")
            for field in ("founder_hours", "compute_usd", "market_estimate_usd"):
                if not valid_decimal_measurement(record.get(field)):
                    errors.append(f"invalid {field} at rounds line {number}")
            for field in ("input_tokens", "output_tokens", "total_tokens"):
                if not valid_token_measurement(record.get(field)):
                    errors.append(f"invalid {field} at rounds line {number}")
            token_values = tuple(
                record.get(field) for field in ("input_tokens", "output_tokens", "total_tokens")
            )
            if all(value != "UNKNOWN" for value in token_values) and all(
                valid_token_measurement(value) for value in token_values
            ) and int(token_values[0]) + int(token_values[1]) != int(token_values[2]):
                errors.append(f"token total mismatch at rounds line {number}")
            for field in (
                "call_method",
                "compute_cost_basis_code",
                "market_estimate_source_code",
                "model_attestation",
                "quota_observation_code",
            ):
                if not isinstance(record.get(field), str) or not CODE_VALUE_RE.fullmatch(
                    record.get(field, "")
                ):
                    errors.append(f"invalid {field} at rounds line {number}")
            for field in ("model", "configured_model"):
                if not isinstance(record.get(field), str) or not record.get(field):
                    errors.append(f"invalid {field} at rounds line {number}")
            if record.get("compute_usd") != "UNKNOWN" and record.get(
                "compute_cost_basis_code"
            ) == "UNKNOWN":
                errors.append(f"known compute cost lacks basis at rounds line {number}")
            if record.get("market_estimate_usd") != "UNKNOWN" and record.get(
                "market_estimate_source_code"
            ) == "UNKNOWN":
                errors.append(f"known market estimate lacks source at rounds line {number}")
            if not isinstance(record.get("retry_count"), int) or record.get("retry_count", -1) < 0:
                errors.append(f"invalid retry count at rounds line {number}")
            if not isinstance(record.get("worker_starts"), int) or record.get(
                "worker_starts", 0
            ) < 1:
                errors.append(f"invalid worker starts at rounds line {number}")
            if not isinstance(record.get("elapsed_seconds"), int) or record.get(
                "elapsed_seconds", -1
            ) < 0:
                errors.append(f"invalid elapsed time at rounds line {number}")
            for field in ("started_at", "completed_at", "source_ref_verified_at"):
                try:
                    parse_time(record.get(field, ""))
                except ConfigError:
                    errors.append(f"invalid {field} at rounds line {number}")
        if round_id in seen_rounds:
            errors.append(f"duplicate completed round ID {round_id}")
        seen_rounds.add(round_id)
        if record.get("outcome") == "SUCCESS":
            successful += 1
            if record.get("oracle_status") != "PASSED":
                errors.append(f"successful round {round_id} lacks a passed oracle")
    if len(seen_rounds) != state.get("rounds_completed"):
        errors.append("round ledger count does not equal completed counter")

    try:
        report_start = parse_time(pilot["activation"]["starts_at"])
        for report in paths(root)["reports"].glob("week-*.md"):
            match = re.fullmatch(r"week-([0-9]{2})\.md", report.name)
            if not match or not 1 <= int(match.group(1)) <= 6:
                errors.append(f"invalid weekly report name: {report.name}")
                continue
            week = int(match.group(1))
            errors.extend(_weekly_report_schema_errors(report, week, report_start))
    except (KeyError, ConfigError) as error:
        errors.append(f"cannot validate weekly report windows: {error}")

    public_result = audit_public(root)
    errors.extend(public_result["errors"])
    if check_git:
        try:
            repository_preflight(root, pilot)
        except FoundryError as error:
            errors.append(str(error))
    if errors:
        raise ConfigError("; ".join(errors))
    return {
        "ok": True,
        "candidate_count": len(candidate_ids),
        "qualified_candidate_count": sum(
            item.get("qualification") == "QUALIFIED" for item in backlog["candidates"]
        ),
        "completed_round_count": len(seen_rounds),
        "successful_round_count": successful,
        "public_scan": "PASSED",
    }


def current_source_identity(root: Path, pilot: dict[str, Any]) -> tuple[str, str]:
    remote_ref = pilot["source"]["remote_ref"]
    revision = git_value(root, "rev-parse", "--verify", remote_ref)
    if not SHA_RE.fullmatch(revision):
        raise UnsafeRepositoryError("remote/ref did not resolve to a commit")
    charter = (root / pilot["source"]["charter_path"]).read_bytes()
    return revision, sha256_bytes(charter)


def source_remote_head_ref(pilot: dict[str, Any]) -> str:
    remote = pilot["source"]["remote"]
    configured_ref = pilot["source"]["remote_ref"]
    prefix = f"refs/remotes/{remote}/"
    if not configured_ref.startswith(prefix) or configured_ref == prefix:
        raise ConfigError("source remote_ref must name a branch on the configured remote")
    return "refs/heads/" + configured_ref.removeprefix(prefix)


def _today_counter(state: dict[str, Any], now: datetime) -> dict[str, int]:
    day = now.date().isoformat()
    counters = state.setdefault("counters_by_utc_day", {})
    return counters.setdefault(day, {"round_starts": 0, "worker_starts": 0})


def _channel(state: dict[str, Any], channel_code: str) -> dict[str, Any]:
    channels = state.get("channels")
    if not isinstance(channels, dict) or channel_code not in channels:
        raise ConfigError(f"unknown execution channel: {channel_code}")
    channel = channels[channel_code]
    if not isinstance(channel, dict):
        raise ConfigError(f"invalid execution channel state: {channel_code}")
    return channel


def _channel_is_active(state: dict[str, Any], channel_code: str) -> bool:
    return _channel(state, channel_code).get("status") == "ACTIVE"


def _available_runtime_environment_ids(
    state: dict[str, Any], now: datetime
) -> list[str]:
    claimed = {
        claim.get("environment_id")
        for claim in state.get("runtime_environment_claims", [])
        if isinstance(claim, dict)
    }
    available: list[str] = []
    for environment in state.get("runtime_environments", []):
        if (
            not isinstance(environment, dict)
            or environment.get("qualification_status") != "VERIFIED_DISPOSABLE_RUNTIME"
            or environment.get("environment_id") in claimed
        ):
            continue
        try:
            current = (
                parse_time(environment["qualified_at"])
                <= now
                < parse_time(environment["expires_at"])
            )
        except (KeyError, ConfigError):
            current = False
        if current:
            available.append(environment["environment_id"])
    return sorted(available)


def _required_runtime_count(task: dict[str, Any]) -> int:
    return 2 if task.get("stage") in {"VERIFICATION", "TRANSFER_EVALUATION"} else 1


def _synchronize_disposable_runtime_availability(
    backlog: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Derive channel/task availability from immutable, unclaimed runtime receipts."""

    available_ids = _available_runtime_environment_ids(state, now)
    available_count = len(available_ids)
    channel = _channel(state, "DISPOSABLE_RUNTIME")
    changes: list[str] = []
    if (
        available_count
        and channel.get("status") == "BLOCKED_ENVIRONMENT"
        and channel.get("status_reason_code") == NO_DISPOSABLE_RUNTIME_CODE
    ):
        channel["status"] = "ACTIVE"
        channel["status_reason_code"] = None
        channel["status_recorded_at"] = format_time(now)
        changes.append("CHANNEL_REACTIVATED_FROM_VERIFIED_RECEIPT")
    elif not available_count and channel.get("status") == "ACTIVE":
        channel["status"] = "BLOCKED_ENVIRONMENT"
        channel["status_reason_code"] = NO_DISPOSABLE_RUNTIME_CODE
        channel["status_recorded_at"] = format_time(now)
        changes.append("CHANNEL_BLOCKED_NO_AVAILABLE_RUNTIME")

    channel_active = channel.get("status") == "ACTIVE"
    for task in backlog.get("work_items", []):
        if not isinstance(task, dict) or task.get("channel_code") != "DISPOSABLE_RUNTIME":
            continue
        enough_runtime = available_count >= _required_runtime_count(task)
        if (
            channel_active
            and enough_runtime
            and task.get("status") == "BLOCKED_ENVIRONMENT"
            and task.get("failure_code") == NO_DISPOSABLE_RUNTIME_CODE
        ):
            task["status"] = "READY"
            task["failure_code"] = None
            changes.append(f"TASK_REACTIVATED:{task.get('task_id')}")
        elif task.get("status") == "READY" and (not channel_active or not enough_runtime):
            task["status"] = "BLOCKED_ENVIRONMENT"
            task["failure_code"] = NO_DISPOSABLE_RUNTIME_CODE
            changes.append(f"TASK_BLOCKED:{task.get('task_id')}")
    return {
        "available_environment_ids": available_ids,
        "changes": changes,
    }


def _append_stage_successor(
    backlog: dict[str, Any], task: dict[str, Any]
) -> dict[str, Any] | None:
    successor_specs = {
        "REPRODUCTION": (
            "REPAIR",
            "DISPOSABLE_RUNTIME",
            task.get("oracle_kind"),
            "IMPLEMENT_BOUNDED_REPAIR_AT_FROZEN_SCOPE",
            95,
        ),
        "REPAIR": (
            "VERIFICATION",
            "DISPOSABLE_RUNTIME",
            task.get("oracle_kind"),
            "RUN_INDEPENDENT_BASELINE_AND_REPAIRED_VERIFICATION",
            94,
        ),
        "VERIFICATION": (
            "RELEASE_MATERIAL",
            "MODEL_WORKER",
            "EXPERIENCE_ARTIFACT_SCHEMA_AND_DIGEST",
            "BUILD_VERSIONED_EXPERIENCE_ARTIFACT",
            85,
        ),
    }
    spec = successor_specs.get(task.get("stage"))
    if spec is None:
        return None
    stage, channel_code, oracle_kind, next_step_code, priority = spec
    candidate_ids = list(task.get("candidate_ids", []))
    if any(
        isinstance(item, dict)
        and item.get("stage") == stage
        and item.get("candidate_ids") == candidate_ids
        for item in backlog.get("work_items", [])
    ):
        return None
    successor = {
        "attempts": 0,
        "candidate_ids": candidate_ids,
        "channel_code": channel_code,
        "claim": None,
        "failure_code": None,
        "generated_by_controller": True,
        "next_step_code": next_step_code,
        "oracle_kind": oracle_kind,
        "priority": priority,
        "stage": stage,
        "status": "READY",
        "task_id": _next_work_item_id(backlog),
    }
    backlog["work_items"].append(successor)
    return successor


def _ensure_qualified_candidate_reproduction_tasks(
    backlog: dict[str, Any],
) -> list[dict[str, Any]]:
    existing_candidate_ids = {
        candidate_id
        for task in backlog.get("work_items", [])
        if isinstance(task, dict)
        and task.get("stage") in {
            "REPRODUCTION",
            "REPAIR",
            "VERIFICATION",
            "RELEASE_MATERIAL",
        }
        for candidate_id in task.get("candidate_ids", [])
    }
    created: list[dict[str, Any]] = []
    for candidate in backlog.get("candidates", []):
        candidate_id = candidate.get("candidate_id")
        if (
            candidate.get("qualification") != "QUALIFIED"
            or candidate.get("category") == "HELD_OUT_TRANSFER"
            or candidate.get("family") != backlog.get("discovery", {}).get("selected_family")
            or candidate_id in existing_candidate_ids
        ):
            continue
        task = {
            "attempts": 0,
            "candidate_ids": [candidate_id],
            "channel_code": "DISPOSABLE_RUNTIME",
            "claim": None,
            "failure_code": None,
            "generated_by_controller": True,
            "next_step_code": "FREEZE_TARGET_AND_REPRODUCE_BASELINE_FAILURE",
            "oracle_kind": candidate["oracle_kind"],
            "priority": 90,
            "stage": "REPRODUCTION",
            "status": "READY",
            "task_id": _next_work_item_id(backlog),
        }
        backlog["work_items"].append(task)
        existing_candidate_ids.add(candidate_id)
        created.append(task)
    return created


def _record_channel_result(
    state: dict[str, Any],
    channel_code: str,
    failure_class: str,
    failure_code: str | None,
    now: datetime,
) -> dict[str, Any]:
    channel = _channel(state, channel_code)
    if failure_class not in FAILURE_CLASSES:
        raise ConfigError("invalid failure class")
    if failure_class in {"INFRASTRUCTURE", "AUTH", "QUOTA", "ENVIRONMENT"} and not failure_code:
        raise ConfigError(f"{failure_class} result requires a failure code")
    if failure_class == "INFRASTRUCTURE":
        prior_code = channel.get("last_infrastructure_failure_code")
        streak = int(channel.get("consecutive_infrastructure_failures", 0))
        streak = streak + 1 if prior_code == failure_code else 1
        channel["consecutive_infrastructure_failures"] = streak
        channel["last_infrastructure_failure_code"] = failure_code
        channel["last_failure_at"] = format_time(now)
        if streak >= 2:
            channel["status"] = "QUARANTINED"
            channel["status_reason_code"] = failure_code
            channel["status_recorded_at"] = format_time(now)
    elif failure_class in {"AUTH", "QUOTA"}:
        channel["status"] = "PAUSED"
        channel["status_reason_code"] = failure_code
        channel["status_recorded_at"] = format_time(now)
    elif failure_class == "ENVIRONMENT":
        channel["status"] = "BLOCKED_ENVIRONMENT"
        channel["status_reason_code"] = failure_code
        channel["status_recorded_at"] = format_time(now)
    elif failure_class == "NONE" and channel.get("status") == "ACTIVE":
        channel["consecutive_infrastructure_failures"] = 0
        channel["last_infrastructure_failure_code"] = None
    return channel


def _expire_if_needed(state: dict[str, Any], pilot: dict[str, Any], now: datetime) -> None:
    if now >= parse_time(pilot["activation"]["ends_at"]):
        if state.get("pilot_status") == "EXPIRED" and (state.get("pause") or {}).get(
            "reason_code"
        ) == "FIXED_TERM_ENDED":
            return
        state["pilot_status"] = "EXPIRED"
        state["pause"] = {
            "reason_code": "FIXED_TERM_ENDED",
            "recorded_at": format_time(now),
        }


def _recover_expired_round(
    backlog: dict[str, Any], state: dict[str, Any], now: datetime
) -> dict[str, Any] | None:
    active = state.get("active_round")
    if active is None or parse_time(active["expires_at"]) > now:
        return None
    task = next(item for item in backlog["work_items"] if item["task_id"] == active["task_id"])
    pending = state.get("pending_effect")
    if pending and pending.get("round_id") == active["round_id"]:
        task["status"] = "BLOCKED_UNCERTAIN_EFFECT"
        task["failure_code"] = "UNRESOLVED_EXTERNAL_EFFECT_AFTER_CRASH"
    else:
        task["status"] = "READY"
        task["failure_code"] = "CRASH_RECOVERED_AT_EXPIRED_CHECKPOINT"
    task["claim"] = None
    state["active_round"] = None
    return {
        "recovered_round_id": active["round_id"],
        "recovered_task_id": active["task_id"],
        "resulting_task_status": task["status"],
    }


def _next_work_item_id(backlog: dict[str, Any]) -> str:
    numbers = []
    for item in backlog["work_items"]:
        match = re.fullmatch(r"AEG-W-([0-9]{3})", item["task_id"])
        if not match:
            raise ConfigError(f"unsupported task ID format: {item['task_id']}")
        numbers.append(int(match.group(1)))
    return f"AEG-W-{max(numbers, default=0) + 1:03d}"


def _weekly_report_schema_errors(
    report: Path, week: int, start: datetime
) -> list[str]:
    if not report.is_file():
        return [f"missing week {week} report"]
    content = report.read_text(encoding="utf-8")
    window_start = start + timedelta(days=7 * (week - 1))
    window_end = start + timedelta(days=7 * week)
    exact_lines = {
        f"# AEG Foundry week {week}",
        f"- Window start: `{format_time(window_start)}`",
        f"- Window end: `{format_time(window_end)}`",
    }
    required_prefixes = (
        "- Candidates: `",
        "- Qualified: `",
        "- Qualification rate: `",
        "- Behavior verified: `",
        "- Release-review Experiences: `",
        "- Positive held-out transfers: `",
        "- Verified external users: `",
        "- External users with strong evidence: `",
        "- Independently verified external successful reuses: `",
        "- Most important recorded outcome: `",
        "- Weekly outcome counts: `",
        "- Weekly founder hours: `",
        "- Weekly compute USD: `",
        "- Acquisition founder hours per qualified task: `",
        "- Acquisition compute USD per qualified task: `",
        "- Verified external reuse per founder hour: `",
        "- Verified external reuse per compute USD: `",
        "- Weekly worker starts: `",
        "- Weekly model usage events: `",
        "- Founder interventions: `",
        "- Integrity incident counts: `",
        "- Account quota observation: `",
        "- Bottleneck: `",
        "- Next focus: `",
        "- Human decision queue: `",
    )
    lines = content.splitlines()
    errors = [
        f"week {week} report lacks required line: {line}"
        for line in exact_lines
        if lines.count(line) != 1
    ]
    errors.extend(
        f"week {week} report lacks unique field: {prefix}"
        for prefix in required_prefixes
        if sum(line.startswith(prefix) for line in lines) != 1
    )
    return errors


def _missing_week_reports(root: Path, pilot: dict[str, Any], now: datetime) -> list[int]:
    start = parse_time(pilot["activation"]["starts_at"])
    completed_weeks = min(6, max(0, int((now - start).total_seconds() // (7 * 86400))))
    return [
        week
        for week in range(1, completed_weeks + 1)
        if _weekly_report_schema_errors(
            paths(root)["reports"] / f"week-{week:02d}.md", week, start
        )
    ]


def synthesize_next_work(
    root: Path,
    backlog: dict[str, Any],
    state: dict[str, Any],
    pilot: dict[str, Any],
    now: datetime,
) -> dict[str, Any] | None:
    """Create one bounded continuation unit when the queue is empty but a target is unmet."""

    due_reports = _missing_week_reports(root, pilot, now)
    if due_reports and _channel_is_active(state, "MODEL_WORKER"):
        task = {
            "attempts": 0,
            "candidate_ids": [],
            "channel_code": "MODEL_WORKER",
            "claim": None,
            "failure_code": None,
            "generated_by_controller": True,
            "next_step_code": "CONTINUE_HIGHEST_VALUE_AUTHORIZED_WORK",
            "oracle_kind": "WEEKLY_REPORT_SCHEMA_AND_WINDOW_CHECK",
            "priority": 110,
            "report_week": due_reports[0],
            "stage": "REPORTING",
            "status": "READY",
            "task_id": _next_work_item_id(backlog),
        }
        backlog["work_items"].append(task)
        return task
    candidates = backlog["candidates"]
    qualified_count = sum(
        item.get("qualification") == "QUALIFIED" for item in candidates
    )
    candidate_target_met = (
        len(candidates) >= pilot["targets"]["deduplicated_external_candidates"]
    )
    qualification_target_met = qualified_count >= pilot["targets"]["qualified_tasks"]
    if candidate_target_met and qualification_target_met:
        return None
    channel_code = "PUBLIC_GITHUB_READ"
    if not _channel_is_active(state, channel_code):
        return None
    task_id = _next_work_item_id(backlog)
    if state.get("discovery_no_qualified_streak", 0) >= 2:
        task = {
            "attempts": 0,
            "candidate_ids": [],
            "channel_code": channel_code,
            "claim": None,
            "failure_code": None,
            "generated_by_controller": True,
            "next_step_code": "CHANGE_EXACTLY_ONE_ACQUISITION_STRATEGY",
            "oracle_kind": "ONE_ACQUISITION_STRATEGY_VERSION_INCREMENT",
            "priority": 80,
            "stage": "DISCOVERY",
            "status": "READY",
            "task_id": task_id,
        }
    else:
        task = {
            "attempts": 0,
            "candidate_ids": [],
            "channel_code": channel_code,
            "claim": None,
            "failure_code": None,
            "family": backlog["discovery"]["selected_family"],
            "generated_by_controller": True,
            "next_step_code": "DISCOVER_AND_SCREEN_NEXT_FAMILY_LOCKED_BATCH",
            "oracle_kind": "CANDIDATE_BATCH_SCHEMA_DEDUP_AND_SOURCE_CHECK",
            "priority": 80,
            "stage": "DISCOVERY",
            "status": "READY",
            "target_candidate_count": (
                len(candidates) + 10
                if candidate_target_met
                else min(
                    len(candidates) + 10,
                    pilot["targets"]["deduplicated_external_candidates"],
                )
            ),
            "task_id": task_id,
        }
    backlog["work_items"].append(task)
    return task


def _remote_contains_push_intent(root: Path, pilot: dict[str, Any], effect_id: str) -> tuple[bool, str | None]:
    remote = pilot["source"]["remote"]
    branch = pilot["execution"]["required_branch"]
    result = run_git(root, "ls-remote", "--heads", remote, f"refs/heads/{branch}", check=False)
    if result.returncode != 0:
        raise UnsafeRepositoryError("cannot verify prior push against the remote")
    if not result.stdout.strip():
        return False, None
    remote_sha = result.stdout.split()[0]
    fetch = run_git(root, "fetch", "--quiet", remote, f"refs/heads/{branch}", check=False)
    if fetch.returncode != 0:
        raise UnsafeRepositoryError("cannot fetch prior push for intent verification")
    remote_state = run_git(root, "show", f"{remote_sha}:foundry/state.json", check=False)
    if remote_state.returncode != 0:
        return False, remote_sha
    try:
        observed = json.loads(remote_state.stdout).get("pending_effect")
    except json.JSONDecodeError:
        return False, remote_sha
    return isinstance(observed, dict) and observed.get("effect_id") == effect_id, remote_sha


def reconcile_push(root: Path, pilot: dict[str, Any], state: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    pending = state.get("pending_effect")
    if not pending:
        return None
    if pending.get("effect_type") != "PUSH_PILOT_BRANCH":
        raise LeaseError("a non-push external effect is unresolved; verify it before retry")
    completed, remote_sha = _remote_contains_push_intent(root, pilot, pending["effect_id"])
    if not completed:
        raise LeaseError(
            "prior push intent is not present at the remote tip; effect is unresolved and was not retried"
        )
    result = {
        "effect_id": pending["effect_id"],
        "remote_sha": remote_sha,
        "verified_at": format_time(now),
        "outcome": "COMPLETED_VERIFIED",
    }
    state.setdefault("effect_events", []).append(result)
    state["pending_effect"] = None
    return result


def reconcile_push_command(root: Path, now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        repository_preflight(root, pilot, require_clean=True)
        result = reconcile_push(root, pilot, state, now)
        if result is None:
            return {"outcome": "NO_PENDING_PUSH"}
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return result


def set_automation(
    root: Path,
    automation_id: str,
    status: str,
    next_run_at: str,
    project_id: str,
    location_code: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        if state.get("active_round") or state.get("pending_effect"):
            raise LeaseError("cannot update automation identity with active or unresolved work")
        if status not in {"ACTIVE", "PAUSED", "DELETED"}:
            raise ConfigError("invalid automation status")
        if not automation_id or any(character.isspace() for character in automation_id):
            raise ConfigError("invalid automation ID")
        parse_time(next_run_at)
        state["automation"] = {
            "id": automation_id,
            "kind": "CRON",
            "location_code": location_code,
            "model": pilot["model_policy"]["automation_model"],
            "next_run_at": next_run_at,
            "project_id": project_id,
            "reasoning_effort": pilot["model_policy"]["automation_reasoning_effort"],
            "recorded_at": format_time(now),
            "status": status,
        }
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return state["automation"]


def begin_round(
    root: Path,
    *,
    now: datetime | None = None,
    reconcile_prior_push: bool = False,
    check_git: bool = True,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        validate(root, check_git=check_git)
        if check_git:
            repository_preflight(root, pilot, require_clean=True)
        prior_status = state["pilot_status"]
        prior_pause = state.get("pause")
        reconciliation = None
        if now >= parse_time(pilot["activation"]["ends_at"]):
            if state.get("pilot_status") == "PAUSED" or (
                state.get("pause")
                and (state.get("pause") or {}).get("reason_code") != "FIXED_TERM_ENDED"
            ):
                _expire_if_needed(state, pilot, now)
                atomic_write_json(paths(root)["state"], state)
                generate_due_reports(root, pilot, backlog, state, now)
                render_status(root, pilot, backlog, state, now)
                raise PausedError(f"pilot is {state['pilot_status']}")
            if reconcile_prior_push:
                reconciliation = reconcile_push(root, pilot, state, now)
            elif state.get("pending_effect"):
                raise LeaseError("an external effect is unresolved; reconciliation is required")
            _expire_if_needed(state, pilot, now)
            if state["pilot_status"] != prior_status or state.get("pause") != prior_pause or reconciliation:
                atomic_write_json(paths(root)["state"], state)
                generate_due_reports(root, pilot, backlog, state, now)
                render_status(root, pilot, backlog, state, now)
            raise PausedError(f"pilot is {state['pilot_status']}")
        _expire_if_needed(state, pilot, now)
        if state["pilot_status"] != "ACTIVE" or state.get("pause"):
            if state["pilot_status"] != prior_status or state.get("pause") != prior_pause:
                atomic_write_json(paths(root)["state"], state)
                generate_due_reports(root, pilot, backlog, state, now)
                render_status(root, pilot, backlog, state, now)
            raise PausedError(f"pilot is {state['pilot_status']}")
        budgets = pilot["budgets"]
        if state["rounds_started"] >= budgets["max_rounds_total"]:
            raise BudgetError("total round budget exhausted")
        counter = _today_counter(state, now)
        if counter["round_starts"] >= budgets["max_rounds_per_day"]:
            raise BudgetError("daily round budget exhausted")
        if counter["worker_starts"] >= budgets["max_worker_starts_per_day"]:
            raise BudgetError("daily worker-start budget exhausted")
        if reconcile_prior_push:
            reconciliation = reconcile_push(root, pilot, state, now)
        elif state.get("pending_effect"):
            raise LeaseError("an external effect is unresolved; reconciliation is required")
        recovery = _recover_expired_round(backlog, state, now)
        active = state.get("active_round")
        if active:
            raise LeaseError(f"round {active['round_id']} holds the lease until {active['expires_at']}")
        runtime_availability = _synchronize_disposable_runtime_availability(
            backlog, state, now
        )
        ready = sorted(
            (
                item
                for item in backlog["work_items"]
                if item["status"] == "READY"
                and _channel_is_active(state, item["channel_code"])
            ),
            key=lambda item: (-item["priority"], item["task_id"]),
        )
        synthesized = None
        if not ready:
            synthesized = synthesize_next_work(root, backlog, state, pilot, now)
            if synthesized is not None:
                ready = [synthesized]
        if not ready:
            if recovery or reconciliation or runtime_availability["changes"]:
                atomic_write_json(paths(root)["backlog"], backlog)
                atomic_write_json(paths(root)["state"], state)
                render_status(root, pilot, backlog, state, now)
            raise NoWorkError("no executable ready work item")
        task = ready[0]
        round_id = f"AEG-R-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        expires = now + timedelta(seconds=budgets["max_round_seconds"])
        source_sha, charter_sha = current_source_identity(root, pilot) if check_git else (
            pilot["source"]["bootstrap_sha"],
            sha256_bytes(paths(root)["charter"].read_bytes()),
        )
        claim = {
            "round_id": round_id,
            "claimed_at": format_time(now),
            "expires_at": format_time(expires),
        }
        task["status"] = "IN_PROGRESS"
        task["claim"] = claim
        task["attempts"] += 1
        state["active_round"] = {
            **claim,
            "task_id": task["task_id"],
            "channel_code": task["channel_code"],
            "source_remote": pilot["source"]["remote"],
            "source_ref": pilot["source"]["remote_ref"],
            "source_ref_sha": source_sha,
            "source_ref_verified_at": format_time(now) if not check_git else None,
            "charter_sha256": charter_sha,
            "candidate_count_at_start": len(backlog["candidates"]),
            "qualified_count_at_start": sum(
                item.get("qualification") == "QUALIFIED" for item in backlog["candidates"]
            ),
            "runtime_environment_ids": [],
            "scheduled_worker_start_counted": True,
            "acquisition_strategy_version_at_start": backlog["discovery"].get(
                "acquisition_strategy_version", 1
            ),
        }
        state["last_remote_ref_sha"] = source_sha
        state["last_charter_sha256"] = charter_sha
        state["rounds_started"] += 1
        counter["round_starts"] += 1
        counter["worker_starts"] += 1
        atomic_write_json(paths(root)["backlog"], backlog)
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return {
            "round_id": round_id,
            "task_id": task["task_id"],
            "channel_code": task["channel_code"],
            "stage": task["stage"],
            "oracle_kind": task["oracle_kind"],
            "expires_at": format_time(expires),
            "source_remote": pilot["source"]["remote"],
            "source_ref": pilot["source"]["remote_ref"],
            "source_ref_sha": source_sha,
            "source_ref_verified_at": state["active_round"]["source_ref_verified_at"],
            "charter_sha256": charter_sha,
            "recovery": recovery,
            "push_reconciliation": reconciliation,
            "runtime_availability": runtime_availability,
            "synthesized_work_item": synthesized is not None,
        }


def _bind_disposable_runtime(
    state: dict[str, Any],
    active: dict[str, Any],
    environment_id: str | None,
    now: datetime,
) -> None:
    if active.get("channel_code") != "DISPOSABLE_RUNTIME":
        raise ConfigError("untrusted execution effect requires a DISPOSABLE_RUNTIME round")
    channel = _channel(state, "DISPOSABLE_RUNTIME")
    if channel.get("status") != "ACTIVE":
        raise ConfigError("disposable runtime channel is not ACTIVE")
    if not isinstance(environment_id, str) or not RUNTIME_ENVIRONMENT_ID_RE.fullmatch(
        environment_id
    ):
        raise ConfigError("untrusted execution effect requires a verified environment ID")
    environments = state.get("runtime_environments", [])
    environment = next(
        (
            item
            for item in environments
            if isinstance(item, dict) and item.get("environment_id") == environment_id
        ),
        None,
    )
    if environment is None or environment.get(
        "qualification_status"
    ) != "VERIFIED_DISPOSABLE_RUNTIME":
        raise ConfigError("disposable runtime lacks a verified qualification receipt")
    if not (
        parse_time(environment["qualified_at"])
        <= now
        < parse_time(environment["expires_at"])
    ):
        raise ConfigError("disposable runtime qualification is not currently valid")
    bound_environment_ids = active.get("runtime_environment_ids")
    if not isinstance(bound_environment_ids, list):
        raise ConfigError("active round has an invalid disposable runtime binding list")
    claims = state.setdefault("runtime_environment_claims", [])
    existing = [
        claim
        for claim in claims
        if isinstance(claim, dict) and claim.get("environment_id") == environment_id
    ]
    if existing and any(claim.get("round_id") != active.get("round_id") for claim in existing):
        raise ConfigError("disposable runtime environment was already consumed by another round")
    if not existing:
        claims.append(
            {
                "claim_id": f"AEG-EC-{uuid.uuid4().hex.upper()}",
                "claimed_at": format_time(now),
                "environment_id": environment_id,
                "round_id": active["round_id"],
            }
        )
    if environment_id not in bound_environment_ids:
        bound_environment_ids.append(environment_id)


def record_intent(
    root: Path,
    round_id: str,
    effect_type: str,
    target_code: str,
    environment_id: str | None = None,
    target_revision: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, _, _ = load_all(root)
    if pilot != PILOT_CONTRACT:
        raise ConfigError("fixed pilot control contract changed")
    with control_lock(root, pilot):
        validate(root, check_git=False)
        _, backlog, state = load_all(root)
        active = state.get("active_round")
        if not active or active["round_id"] != round_id:
            raise LeaseError("intent round does not own the active lease")
        if state.get("pending_effect"):
            raise LeaseError("another external effect is unresolved")
        if effect_type not in EFFECT_TYPES or effect_type == "PUSH_PILOT_BRANCH":
            raise ConfigError("invalid stage effect type")
        if not isinstance(target_code, str) or not CODE_VALUE_RE.fullmatch(target_code):
            raise ConfigError("invalid external effect target code")
        if effect_type in UNTRUSTED_EXECUTION_EFFECT_TYPES:
            if effect_type == "RUN_FROZEN_ORACLE" and (
                not isinstance(target_revision, str) or not SHA_RE.fullmatch(target_revision)
            ):
                raise ConfigError("frozen oracle effect requires an immutable target revision")
            if effect_type != "RUN_FROZEN_ORACLE" and target_revision is not None:
                raise ConfigError("target revision is valid only for frozen-oracle effects")
            _bind_disposable_runtime(state, active, environment_id, now)
        elif environment_id is not None or target_revision is not None:
            raise ConfigError(
                "environment ID and target revision are valid only for untrusted execution effects"
            )
        effect = {
            "effect_id": f"AEG-I-{uuid.uuid4().hex}",
            "effect_type": effect_type,
            "recorded_at": format_time(now),
            "round_id": round_id,
            "target_code": target_code,
        }
        if environment_id is not None:
            effect["environment_id"] = environment_id
        if effect_type == "RUN_FROZEN_ORACLE":
            task = next(
                item for item in backlog["work_items"] if item["task_id"] == active["task_id"]
            )
            effect.update(
                {
                    "oracle_kind": task["oracle_kind"],
                    "target_revision": target_revision,
                }
            )
        state["pending_effect"] = effect
        atomic_write_json(paths(root)["state"], state)
        return effect


def record_maintenance_intent(
    root: Path, effect_type: str, target_code: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, _, _ = load_all(root)
    if pilot != PILOT_CONTRACT:
        raise ConfigError("fixed pilot control contract changed")
    with control_lock(root, pilot):
        validate(root, check_git=False)
        _, _, state = load_all(root)
        if state.get("active_round") or state.get("pending_effect"):
            raise LeaseError("maintenance intent requires no active or unresolved work")
        if effect_type not in EFFECT_TYPES or effect_type == "PUSH_PILOT_BRANCH":
            raise ConfigError("invalid maintenance effect type")
        if effect_type in UNTRUSTED_EXECUTION_EFFECT_TYPES:
            raise ConfigError("untrusted execution effects require an active disposable-runtime round")
        if not isinstance(target_code, str) or not CODE_VALUE_RE.fullmatch(target_code):
            raise ConfigError("invalid external effect target code")
        effect = {
            "effect_id": f"AEG-I-{uuid.uuid4().hex}",
            "effect_type": effect_type,
            "recorded_at": format_time(now),
            "round_id": state.get("last_round_id"),
            "target_code": target_code,
        }
        state["pending_effect"] = effect
        atomic_write_json(paths(root)["state"], state)
        return effect


def resolve_intent(
    root: Path,
    effect_id: str,
    outcome: str,
    *,
    command_argv: list[str] | None = None,
    exit_code: int | None = None,
    oracle_observation: str | None = None,
    evidence_digest_sha256: str | None = None,
    evidence_summary_codes: list[str] | None = None,
    failure_code: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        pending = state.get("pending_effect")
        if not pending or pending.get("effect_id") != effect_id:
            raise LeaseError("effect intent is not the current unresolved effect")
        if pending.get("effect_type") == "PUSH_PILOT_BRANCH":
            raise ConfigError("push effects are resolved only by remote reconciliation")
        if outcome not in {"COMPLETED", "FAILED", "NOT_PERFORMED"}:
            raise ConfigError("invalid effect outcome")
        oracle_evidence = (
            command_argv,
            exit_code,
            oracle_observation,
            evidence_digest_sha256,
            evidence_summary_codes,
            failure_code,
        )
        is_frozen_oracle = pending.get("effect_type") == "RUN_FROZEN_ORACLE"
        if not is_frozen_oracle and any(value is not None for value in oracle_evidence):
            raise ConfigError("oracle evidence is valid only for frozen-oracle effects")
        result = {**pending, "outcome": outcome, "resolved_at": format_time(now)}
        if is_frozen_oracle:
            if outcome == "COMPLETED":
                if (
                    not isinstance(command_argv, list)
                    or not command_argv
                    or any(not isinstance(item, str) or not item for item in command_argv)
                ):
                    raise ConfigError("completed frozen oracle requires command argv")
                if type(exit_code) is not int:
                    raise ConfigError("completed frozen oracle requires an integer exit code")
                if oracle_observation not in {"SUCCESS", "FAILURE"}:
                    raise ConfigError("completed frozen oracle requires an actual observation")
                if (
                    not isinstance(evidence_digest_sha256, str)
                    or not SHA256_RE.fullmatch(evidence_digest_sha256)
                ):
                    raise ConfigError("completed frozen oracle requires a SHA-256 evidence digest")
                if (
                    not isinstance(evidence_summary_codes, list)
                    or not evidence_summary_codes
                    or any(
                        not isinstance(item, str) or not CODE_VALUE_RE.fullmatch(item)
                        for item in evidence_summary_codes
                    )
                    or len(set(evidence_summary_codes)) != len(evidence_summary_codes)
                ):
                    raise ConfigError("completed frozen oracle requires unique evidence summary codes")
                if failure_code is not None:
                    raise ConfigError("completed frozen oracle cannot carry a failure code")
                result.update(
                    {
                        "command_argv": command_argv,
                        "evidence_digest_sha256": evidence_digest_sha256,
                        "evidence_summary_codes": evidence_summary_codes,
                        "exit_code": exit_code,
                        "oracle_observation": oracle_observation,
                    }
                )
            elif outcome == "FAILED":
                if any(value is not None for value in oracle_evidence[:-1]):
                    raise ConfigError("failed frozen oracle cannot carry completion evidence")
                if not isinstance(failure_code, str) or not CODE_VALUE_RE.fullmatch(failure_code):
                    raise ConfigError("failed frozen oracle requires a failure code")
                result["failure_code"] = failure_code
            elif any(value is not None for value in oracle_evidence):
                raise ConfigError("unperformed frozen oracle cannot carry execution evidence")
        state.setdefault("effect_events", []).append(result)
        state["pending_effect"] = None
        atomic_write_json(paths(root)["state"], state)
        return result


def _require_stage_success_evidence(
    backlog: dict[str, Any],
    state: dict[str, Any],
    active: dict[str, Any],
    task: dict[str, Any],
) -> None:
    def arm_environment_codes(
        record: dict[str, Any] | None, arm_names: tuple[str, str]
    ) -> list[str]:
        if not isinstance(record, dict):
            return []
        arms = [record.get(name) for name in arm_names]
        if any(not isinstance(arm, dict) for arm in arms):
            return []
        return [arm.get("environment_code") for arm in arms]

    stage = task["stage"]
    bound_environment_ids = active.get("runtime_environment_ids", [])
    bound_environment_id_set = (
        set(bound_environment_ids)
        if isinstance(bound_environment_ids, list)
        and all(isinstance(item, str) for item in bound_environment_ids)
        else set()
    )
    if stage in {"REPRODUCTION", "REPAIR"}:
        required_observation = "FAILURE" if stage == "REPRODUCTION" else "SUCCESS"
        matching_receipts = [
            effect
            for effect in state.get("effect_events", [])
            if isinstance(effect, dict)
            and effect.get("effect_type") == "RUN_FROZEN_ORACLE"
            and effect.get("round_id") == active["round_id"]
            and effect.get("outcome") == "COMPLETED"
            and effect.get("oracle_kind") == task["oracle_kind"]
            and effect.get("oracle_observation") == required_observation
            and effect.get("environment_id") in bound_environment_id_set
        ]
        if not matching_receipts:
            raise ConfigError(
                f"{stage} SUCCESS requires a current-round frozen-oracle "
                f"{required_observation} receipt"
            )
    elif stage == "VERIFICATION":
        verification = next(
            (
                item
                for item in backlog.get("behavior_verifications", [])
                if isinstance(item, dict)
                and item.get("task_id") == task["task_id"]
                and item.get("status") == "COMPLETED"
                and item.get("outcome") == "VERIFIED_REPAIR"
            ),
            None,
        )
        environments = arm_environment_codes(verification, ("baseline", "repaired"))
        if (
            verification is None
            or len(environments) != 2
            or any(not isinstance(item, str) for item in environments)
            or len(set(environments)) != 2
            or not set(environments).issubset(bound_environment_id_set)
        ):
            raise ConfigError(
                "VERIFICATION SUCCESS requires isolated behavior evidence in two "
                "runtime environments claimed by the current round"
            )
    elif stage == "TRANSFER_EVALUATION":
        transfer = next(
            (
                item
                for item in backlog.get("transfer_evaluations", [])
                if isinstance(item, dict)
                and item.get("task_id") == task["task_id"]
                and item.get("status") == "COMPLETED"
                and item.get("outcome") in {"POSITIVE", "NEUTRAL", "HARMFUL"}
            ),
            None,
        )
        environments = arm_environment_codes(transfer, ("baseline", "assisted"))
        if (
            transfer is None
            or len(environments) != 2
            or any(not isinstance(item, str) for item in environments)
            or len(set(environments)) != 2
            or not set(environments).issubset(bound_environment_id_set)
        ):
            raise ConfigError(
                "TRANSFER_EVALUATION SUCCESS requires a terminal transfer in two "
                "runtime environments claimed by the current round"
            )
    elif stage == "RELEASE_MATERIAL" and not any(
        isinstance(experience, dict)
        and isinstance(experience.get("builder_task_ids"), list)
        and task["task_id"] in experience["builder_task_ids"]
        for experience in backlog.get("experiences", [])
    ):
        raise ConfigError("RELEASE_MATERIAL SUCCESS requires an Experience built by this task")


def observe_source_ref(
    root: Path,
    round_id: str,
    effect_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve a recorded source-read intent against the current remote branch tip."""

    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        active = state.get("active_round")
        if not active or active.get("round_id") != round_id:
            raise LeaseError("source observation round does not own the active lease")
        pending = state.get("pending_effect")
        if not pending or pending.get("effect_id") != effect_id:
            raise LeaseError("source observation intent is not the current unresolved effect")
        if pending.get("effect_type") != "READ_PUBLIC_SOURCE":
            raise ConfigError("source observation requires a READ_PUBLIC_SOURCE intent")
        if pending.get("target_code") != "CURRENT_SOURCE_REMOTE_REF":
            raise ConfigError("source observation intent has the wrong target code")
        remote = pilot["source"]["remote"]
        head_ref = source_remote_head_ref(pilot)
        result = run_git(root, "ls-remote", "--heads", remote, head_ref, check=False)
        if result.returncode != 0:
            receipt = {
                **pending,
                "failure_code": "SOURCE_REMOTE_READ_FAILED",
                "outcome": "FAILED",
                "resolved_at": format_time(now),
            }
            state.setdefault("effect_events", []).append(receipt)
            state["pending_effect"] = None
            atomic_write_json(paths(root)["state"], state)
            render_status(root, pilot, backlog, state, now)
            raise UnsafeRepositoryError("current source remote/ref could not be read")
        lines = [line.split() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) != 1 or len(lines[0]) < 2 or lines[0][1] != head_ref:
            raise UnsafeRepositoryError("current source remote/ref did not resolve uniquely")
        remote_sha = lines[0][0]
        if not SHA_RE.fullmatch(remote_sha):
            raise UnsafeRepositoryError("current source remote/ref returned an invalid commit")
        observed_at = format_time(now)
        active["source_ref_sha"] = remote_sha
        active["source_ref_verified_at"] = observed_at
        state["last_remote_ref_sha"] = remote_sha
        receipt = {
            **pending,
            "outcome": "COMPLETED",
            "resolved_at": observed_at,
            "source_ref_sha": remote_sha,
        }
        state.setdefault("effect_events", []).append(receipt)
        state["pending_effect"] = None
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return receipt


def finish_round(
    root: Path,
    round_id: str,
    outcome: str,
    oracle_status: str,
    next_step_code: str,
    *,
    task_status: str | None = None,
    failure_code: str | None = None,
    failure_class: str = "NONE",
    founder_hours: str = "UNKNOWN",
    compute_usd: str = "UNKNOWN",
    model: str = "UNKNOWN",
    configured_model: str = "UNKNOWN",
    model_attestation: str = "UNKNOWN",
    call_method: str = "UNKNOWN",
    input_tokens: str = "UNKNOWN",
    output_tokens: str = "UNKNOWN",
    total_tokens: str = "UNKNOWN",
    retry_count: int = 0,
    compute_cost_basis_code: str = "UNKNOWN",
    market_estimate_usd: str = "UNKNOWN",
    market_estimate_source_code: str = "UNKNOWN",
    quota_observation_code: str = "UNKNOWN",
    worker_starts: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        active = state.get("active_round")
        if not active or active["round_id"] != round_id:
            raise LeaseError("round does not own the active lease")
        task = next(item for item in backlog["work_items"] if item["task_id"] == active["task_id"])
        if state.get("pending_effect"):
            raise LeaseError("resolve or verify the pending effect before finishing")
        if not active.get("source_ref_verified_at"):
            raise ConfigError("current source remote/ref must be observed before finishing")
        if outcome not in OUTCOMES or oracle_status not in ORACLE_STATUSES:
            raise ConfigError("invalid outcome or oracle status")
        if outcome == "SUCCESS" and oracle_status != "PASSED":
            raise ConfigError("SUCCESS requires a PASSED deterministic oracle")
        if outcome == "SUCCESS" and failure_class != "NONE":
            raise ConfigError("SUCCESS cannot carry a failure class")
        if outcome in {"FAILURE", "BLOCKED"} and failure_class == "NONE":
            raise ConfigError(f"{outcome} requires an explicit failure class")
        if outcome == "SUCCESS":
            _require_stage_success_evidence(backlog, state, active, task)
        for field, value in (
            ("founder_hours", founder_hours),
            ("compute_usd", compute_usd),
            ("market_estimate_usd", market_estimate_usd),
        ):
            if not valid_decimal_measurement(value):
                raise ConfigError(f"invalid non-negative measurement: {field}")
        for field, value in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
            ("total_tokens", total_tokens),
        ):
            if not valid_token_measurement(value):
                raise ConfigError(f"invalid token measurement: {field}")
        if all(value != "UNKNOWN" for value in (input_tokens, output_tokens, total_tokens)) and (
            int(input_tokens) + int(output_tokens) != int(total_tokens)
        ):
            raise ConfigError("input and output tokens do not equal total tokens")
        if not isinstance(retry_count, int) or retry_count < 0:
            raise ConfigError("retry count must be a non-negative integer")
        if not isinstance(model, str) or not model or not isinstance(configured_model, str) or not configured_model:
            raise ConfigError("actual and configured model fields must be non-empty")
        for field, value in (
            ("model_attestation", model_attestation),
            ("call_method", call_method),
            ("compute_cost_basis_code", compute_cost_basis_code),
            ("market_estimate_source_code", market_estimate_source_code),
            ("quota_observation_code", quota_observation_code),
        ):
            if not isinstance(value, str) or not CODE_VALUE_RE.fullmatch(value):
                raise ConfigError(f"invalid resource evidence code: {field}")
        if compute_usd != "UNKNOWN" and compute_cost_basis_code == "UNKNOWN":
            raise ConfigError("known compute USD requires a cost basis code")
        if market_estimate_usd != "UNKNOWN" and market_estimate_source_code == "UNKNOWN":
            raise ConfigError("known market estimate requires a source code")
        counter = _today_counter(state, now)
        linked_worker_starts = sum(
            event.get("round_id") == round_id for event in state.get("worker_events", [])
        )
        inferred_worker_starts = 1 + linked_worker_starts
        if worker_starts is not None and worker_starts != inferred_worker_starts:
            raise ConfigError("round worker starts disagree with registered worker events")
        worker_starts = inferred_worker_starts
        scheduled_start_already_counted = active.get("scheduled_worker_start_counted") is True
        if not scheduled_start_already_counted:
            if counter["worker_starts"] >= pilot["budgets"]["max_worker_starts_per_day"]:
                raise BudgetError("worker-start accounting would exceed the daily budget")
            counter["worker_starts"] += 1
        channel_code = task["channel_code"]
        if task["oracle_kind"] == "CANDIDATE_BATCH_SCHEMA_DEDUP_AND_SOURCE_CHECK":
            candidate_gain = len(backlog["candidates"]) - active["candidate_count_at_start"]
            target_candidate_count = task.get("target_candidate_count")
            qualified_now = sum(
                item.get("qualification") == "QUALIFIED" for item in backlog["candidates"]
            )
            qualified_gain = qualified_now - active["qualified_count_at_start"]
            if outcome == "SUCCESS" and candidate_gain <= 0:
                raise ConfigError("candidate-batch SUCCESS requires at least one new deduplicated candidate")
            if (
                outcome == "SUCCESS"
                and isinstance(target_candidate_count, int)
                and len(backlog["candidates"]) < target_candidate_count
            ):
                raise ConfigError(
                    "candidate-batch SUCCESS requires reaching its frozen candidate-count target"
                )
            if oracle_status == "PASSED" and qualified_gain <= 0:
                state["discovery_no_qualified_streak"] = state.get(
                    "discovery_no_qualified_streak", 0
                ) + 1
            elif qualified_gain > 0:
                state["discovery_no_qualified_streak"] = 0
        elif task["oracle_kind"] == "ONE_ACQUISITION_STRATEGY_VERSION_INCREMENT":
            previous_version = active["acquisition_strategy_version_at_start"]
            current_version = backlog["discovery"].get("acquisition_strategy_version")
            if outcome == "SUCCESS" and current_version != previous_version + 1:
                raise ConfigError("strategy-change SUCCESS requires exactly one version increment")
            if outcome == "SUCCESS":
                state["discovery_no_qualified_streak"] = 0
        elif task["oracle_kind"] == "WEEKLY_REPORT_SCHEMA_AND_WINDOW_CHECK":
            report_week = task.get("report_week")
            if not isinstance(report_week, int) or not 1 <= report_week <= 6:
                raise ConfigError("reporting task has an invalid week number")
            expected_report = paths(root)["reports"] / f"week-{report_week:02d}.md"
            if outcome == "SUCCESS":
                generate_due_reports(root, pilot, backlog, state, now)
                report_errors = _weekly_report_schema_errors(
                    expected_report,
                    report_week,
                    parse_time(pilot["activation"]["starts_at"]),
                )
                if report_errors:
                    raise ConfigError(
                        "reporting SUCCESS requires a valid due weekly report: "
                        + "; ".join(report_errors)
                    )
        if task_status is None:
            task_status = "COMPLETED" if outcome == "SUCCESS" else "FAILED"
        if task_status not in TASK_STATUSES or task_status in {"READY", "IN_PROGRESS"}:
            raise ConfigError("invalid terminal/checkpoint task status")
        if outcome == "SUCCESS" and task_status != "COMPLETED":
            raise ConfigError("SUCCESS requires a COMPLETED task status")
        if outcome != "SUCCESS" and task_status == "COMPLETED":
            raise ConfigError("non-success outcome cannot complete a task")
        task["status"] = task_status
        task["claim"] = None
        task["failure_code"] = failure_code
        task["next_step_code"] = next_step_code
        if outcome == "SUCCESS":
            if task["stage"] == "DISCOVERY":
                _ensure_qualified_candidate_reproduction_tasks(backlog)
            else:
                _append_stage_successor(backlog, task)
        channel = _record_channel_result(
            state,
            channel_code,
            failure_class,
            failure_code,
            now,
        )
        elapsed = max(0, int((now - parse_time(active["claimed_at"])).total_seconds()))
        record = {
            "channel_code": channel_code,
            "channel_status_after": channel["status"],
            "charter_sha256": active["charter_sha256"],
            "call_method": call_method,
            "completed_at": format_time(now),
            "compute_cost_basis_code": compute_cost_basis_code,
            "compute_usd": compute_usd,
            "configured_model": configured_model,
            "elapsed_seconds": elapsed,
            "failure_code": failure_code,
            "failure_class": failure_class,
            "founder_hours": founder_hours,
            "input_tokens": input_tokens,
            "market_estimate_source_code": market_estimate_source_code,
            "market_estimate_usd": market_estimate_usd,
            "model": model,
            "model_attestation": model_attestation,
            "next_step_code": next_step_code,
            "oracle_status": oracle_status,
            "outcome": outcome,
            "output_tokens": output_tokens,
            "quota_observation_code": quota_observation_code,
            "record_schema_version": 2,
            "retry_count": retry_count,
            "round_id": round_id,
            "source_ref": active["source_ref"],
            "source_ref_sha": active["source_ref_sha"],
            "source_ref_verified_at": active["source_ref_verified_at"],
            "stage": task["stage"],
            "started_at": active["claimed_at"],
            "task_id": task["task_id"],
            "total_tokens": total_tokens,
            "worker_starts": worker_starts,
        }
        append_jsonl(paths(root)["rounds"], record)
        state["active_round"] = None
        state["last_round_id"] = round_id
        state["rounds_completed"] += 1
        _synchronize_disposable_runtime_availability(backlog, state, now)
        _expire_if_needed(state, pilot, now)
        atomic_write_json(paths(root)["backlog"], backlog)
        atomic_write_json(paths(root)["state"], state)
        generate_due_reports(root, pilot, backlog, state, now)
        render_status(root, pilot, backlog, state, now)
        validate(root, check_git=False)
        return record


def register_worker(
    root: Path,
    kind: str,
    model: str,
    channel_code: str = "MODEL_WORKER",
    configured_model: str = "UNKNOWN",
    call_method: str = "UNKNOWN",
    round_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        if not _channel_is_active(state, channel_code):
            raise PausedError(f"execution channel {channel_code} is not ACTIVE")
        if round_id is not None:
            active = state.get("active_round")
            if not active or active.get("round_id") != round_id:
                raise LeaseError("worker event must reference the active round")
        counter = _today_counter(state, now)
        if counter["worker_starts"] >= pilot["budgets"]["max_worker_starts_per_day"]:
            raise BudgetError("daily worker-start budget exhausted")
        if not isinstance(model, str) or not model or not isinstance(configured_model, str) or not configured_model:
            raise ConfigError("actual and configured worker model fields must be non-empty")
        if not isinstance(call_method, str) or not CODE_VALUE_RE.fullmatch(call_method):
            raise ConfigError("invalid worker call method")
        event = {
            "call_method": call_method,
            "channel_code": channel_code,
            "configured_model": configured_model,
            "event_id": f"AEG-M-{uuid.uuid4().hex}",
            "kind": kind,
            "model": model,
            "record_schema_version": 2,
            "round_id": round_id,
            "started_at": format_time(now),
            "status": "STARTED",
        }
        counter["worker_starts"] += 1
        state.setdefault("worker_events", []).append(event)
        atomic_write_json(paths(root)["state"], state)
        return event


def finish_worker(
    root: Path,
    event_id: str,
    status: str,
    *,
    failure_code: str | None = None,
    input_tokens: str = "UNKNOWN",
    output_tokens: str = "UNKNOWN",
    total_tokens: str = "UNKNOWN",
    compute_usd: str = "UNKNOWN",
    model_attestation: str = "UNKNOWN",
    retry_count: int = 0,
    compute_cost_basis_code: str = "UNKNOWN",
    market_estimate_usd: str = "UNKNOWN",
    market_estimate_source_code: str = "UNKNOWN",
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        event = next((item for item in state.get("worker_events", []) if item["event_id"] == event_id), None)
        if event is None or event["status"] != "STARTED":
            raise ConfigError("worker event is absent or already terminal")
        if status not in {
            "PASSED",
            "FAILED",
            "INFRASTRUCTURE_FAILED",
            "AUTH_FAILED",
            "QUOTA_FAILED",
        }:
            raise ConfigError("invalid worker status")
        for field, value in (
            ("compute_usd", compute_usd),
            ("market_estimate_usd", market_estimate_usd),
        ):
            if not valid_decimal_measurement(value):
                raise ConfigError(f"invalid worker measurement: {field}")
        for field, value in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
            ("total_tokens", total_tokens),
        ):
            if not valid_token_measurement(value):
                raise ConfigError(f"invalid worker token measurement: {field}")
        if all(value != "UNKNOWN" for value in (input_tokens, output_tokens, total_tokens)) and (
            int(input_tokens) + int(output_tokens) != int(total_tokens)
        ):
            raise ConfigError("worker input and output tokens do not equal total tokens")
        if not isinstance(retry_count, int) or retry_count < 0:
            raise ConfigError("worker retry count must be non-negative")
        for field, value in (
            ("model_attestation", model_attestation),
            ("compute_cost_basis_code", compute_cost_basis_code),
            ("market_estimate_source_code", market_estimate_source_code),
        ):
            if not isinstance(value, str) or not CODE_VALUE_RE.fullmatch(value):
                raise ConfigError(f"invalid worker evidence code: {field}")
        if compute_usd != "UNKNOWN" and compute_cost_basis_code == "UNKNOWN":
            raise ConfigError("known worker compute USD requires a cost basis code")
        if market_estimate_usd != "UNKNOWN" and market_estimate_source_code == "UNKNOWN":
            raise ConfigError("known worker market estimate requires a source code")
        event.update(
            {
                "completed_at": format_time(now),
                "compute_cost_basis_code": compute_cost_basis_code,
                "compute_usd": compute_usd,
                "input_tokens": input_tokens,
                "market_estimate_source_code": market_estimate_source_code,
                "market_estimate_usd": market_estimate_usd,
                "model_attestation": model_attestation,
                "output_tokens": output_tokens,
                "retry_count": retry_count,
                "total_tokens": total_tokens,
                "status": status,
            }
        )
        failure_class = {
            "PASSED": "NONE",
            "FAILED": "TASK",
            "INFRASTRUCTURE_FAILED": "INFRASTRUCTURE",
            "AUTH_FAILED": "AUTH",
            "QUOTA_FAILED": "QUOTA",
        }[status]
        resolved_failure_code = failure_code or (
            status if status in {"AUTH_FAILED", "QUOTA_FAILED"} else None
        )
        channel = _record_channel_result(
            state,
            event.get("channel_code", "MODEL_WORKER"),
            failure_class,
            resolved_failure_code,
            now,
        )
        event["channel_status_after"] = channel["status"]
        event["failure_code"] = resolved_failure_code
        atomic_write_json(paths(root)["state"], state)
        return event


def pause(root: Path, reason_code: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        state["pilot_status"] = "PAUSED"
        state["pause"] = {"reason_code": reason_code, "recorded_at": format_time(now)}
        if state.get("active_round"):
            state["active_round"]["stop_requested"] = True
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return state["pause"]


def resume(root: Path, now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        if now >= parse_time(pilot["activation"]["ends_at"]):
            raise BudgetError("fixed pilot term ended and cannot be extended")
        if state.get("active_round"):
            raise LeaseError("cannot resume while a round is active")
        state["pilot_status"] = "ACTIVE"
        state["pause"] = None
        atomic_write_json(paths(root)["state"], state)
        render_status(root, pilot, backlog, state, now)
        return {"pilot_status": "ACTIVE", "resumed_at": format_time(now)}


def pause_and_persist(root: Path, reason_code: str) -> dict[str, Any]:
    _, _, state = load_all(root)
    reconciliation: dict[str, Any] | None = None
    if state.get("pending_effect"):
        try:
            reconciliation = reconcile_push_command(root)
        except FoundryError as error:
            pause_result = pause(root, reason_code)
            return {
                "pause": pause_result,
                "persistence": "DEFERRED_PENDING_EFFECT",
                "reconciliation_error": str(error),
            }
    pause_result = pause(root, reason_code)
    _, _, paused_state = load_all(root)
    if paused_state.get("active_round"):
        return {
            "pause": pause_result,
            "persistence": "DEFERRED_ACTIVE_ROUND_SAFE_CHECKPOINT_REQUIRED",
            "reconciliation": reconciliation,
        }
    return {
        "pause": pause_result,
        "persistence": persist(root, paused_state["last_round_id"], push=True),
        "reconciliation": reconciliation,
    }


def _counts(backlog: dict[str, Any]) -> dict[str, int]:
    candidates = backlog["candidates"]
    work = backlog["work_items"]
    verifications = backlog.get("behavior_verifications", [])
    experiences = backlog.get("experiences", [])
    transfers = backlog.get("transfer_evaluations", [])
    return {
        "candidates": len(candidates),
        "qualified": sum(item["qualification"] == "QUALIFIED" for item in candidates),
        "behavior_verified": len(
            {
                item.get("candidate_id")
                for item in verifications
                if item.get("status") == "COMPLETED"
                and item.get("outcome") == "VERIFIED_REPAIR"
            }
        ),
        "release_review_experiences": len(
            {
                item.get("experience_id")
                for item in experiences
                if item.get("release_review_status") == "READY"
            }
        ),
        "held_out_positive_transfers": sum(
            item.get("status") == "COMPLETED" and item.get("outcome") == "POSITIVE"
            for item in transfers
        ),
        "ready_work": sum(item["status"] == "READY" for item in work),
        "blocked_environment": sum(item["status"] == "BLOCKED_ENVIRONMENT" for item in work),
        "blocked_approval": sum(item["status"] == "BLOCKED_APPROVAL" for item in work),
    }


def render_status(
    root: Path,
    pilot: dict[str, Any] | None = None,
    backlog: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> str:
    now = now or utc_now()
    if pilot is None or backlog is None or state is None:
        pilot, backlog, state = load_all(root)
    counts = _counts(backlog)
    verified_users, strong_user_evidence = _external_user_evidence(state)
    verified_external_reuse = _verified_external_reuse_count(state)
    runtime_environments = state.get("runtime_environments", [])
    claimed_runtime_ids = {
        claim.get("environment_id")
        for claim in state.get("runtime_environment_claims", [])
        if isinstance(claim, dict)
    }
    available_runtime_count = sum(
        environment.get("qualification_status") == "VERIFIED_DISPOSABLE_RUNTIME"
        and environment.get("environment_id") not in claimed_runtime_ids
        and parse_time(environment["qualified_at"]) <= now < parse_time(environment["expires_at"])
        for environment in runtime_environments
        if isinstance(environment, dict)
    )
    active = state.get("active_round")
    next_items = sorted(
        (item for item in backlog["work_items"] if item["status"] != "COMPLETED"),
        key=lambda item: (-item["priority"], item["task_id"]),
    )
    next_code = next_items[0]["next_step_code"] if next_items else "NONE"
    blocked_code = next_items[0].get("failure_code") if next_items else None
    channel_lines = [
        "- "
        + f"`{channel_code}`: `{channel['status']}`"
        + f"; infra streak `{channel.get('consecutive_infrastructure_failures', 0)}`"
        + f"; reason `{channel.get('status_reason_code') or 'NONE'}`"
        for channel_code, channel in sorted(state["channels"].items())
    ]
    lines = [
        "# AEG Experience Foundry Pilot status",
        "",
        f"Generated: `{format_time(now)}`",
        "",
        f"- Pilot: `{state['pilot_status']}`",
        f"- Automation: `{state['automation']['status']}`",
        f"- Automation ID: `{state['automation'].get('id') or 'NONE'}`",
        f"- Automation model: `{state['automation'].get('model') or pilot['model_policy']['automation_model']}` / `{state['automation'].get('reasoning_effort') or pilot['model_policy']['automation_reasoning_effort']}`",
        f"- Next scheduled run: `{state['automation'].get('next_run_at') or 'NOT_SCHEDULED'}`",
        f"- Required branch: `{pilot['execution']['required_branch']}`",
        f"- Source: `{pilot['source']['remote']}` / `{pilot['source']['remote_ref']}` / `{state.get('last_remote_ref_sha') or 'NOT_OBSERVED'}`",
        f"- Charter SHA-256: `{state.get('last_charter_sha256') or 'NOT_OBSERVED'}`",
        f"- Fixed expiry: `{pilot['activation']['ends_at']}`",
        f"- Active round: `{active['round_id'] if active else 'NONE'}`",
        "",
        "## Progress",
        "",
        f"- Deduplicated external candidates: `{counts['candidates']} / {pilot['targets']['deduplicated_external_candidates']}`",
        f"- Qualified tasks: `{counts['qualified']} / {pilot['targets']['qualified_tasks']}`",
        f"- Independently behavior-verified tasks: `{counts['behavior_verified']} / {pilot['targets']['independently_behavior_verified_tasks']}`",
        f"- Release-review Experiences: `{counts['release_review_experiences']} / {pilot['targets']['release_review_experiences_min']}-{pilot['targets']['release_review_experiences_max']}`",
        f"- Held-out positive transfers: `{counts['held_out_positive_transfers']} / {pilot['targets']['held_out_positive_transfers']}`",
        f"- Verified external users: `{verified_users} / {pilot['targets']['verified_external_users']}`",
        f"- External users with strong evidence: `{strong_user_evidence} / {pilot['targets']['external_users_with_strong_evidence']}`",
        f"- Independently verified external successful reuses: `{verified_external_reuse}`",
        f"- Integrity incident counts: `{json.dumps(_integrity_incident_counts(state), sort_keys=True, separators=(',', ':'))}`",
        f"- Rounds: `{state['rounds_completed']} completed / {state['rounds_started']} started / {pilot['budgets']['max_rounds_total']} max`",
        "",
        "## Current focus and bottleneck",
        "",
        f"- Selected family: `{backlog['discovery']['selected_family']}`",
        f"- Ready work: `{counts['ready_work']}`",
        f"- Environment-blocked work: `{counts['blocked_environment']}`",
        f"- Approval-blocked work: `{counts['blocked_approval']}`",
        f"- Verified disposable-runtime receipts: `{len(runtime_environments)}`",
        f"- Available unclaimed disposable runtimes: `{available_runtime_count}`",
        f"- Primary block code: `{blocked_code or 'NONE'}`",
        f"- Next step code: `{next_code}`",
        "",
        "## Execution channels",
        "",
        *channel_lines,
        "",
        "Founder hours and compute dollars are reported separately. Unobservable values remain `UNKNOWN`.",
    ]
    content = "\n".join(lines) + "\n"
    atomic_write(paths(root)["status"], content)
    return content


def _round_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in paths(root)["rounds"].read_text(encoding="utf-8").splitlines():
        if line:
            records.append(json.loads(line))
    return records


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def _known_total(records: list[dict[str, Any]], field: str) -> str:
    if not records:
        return "0"
    total = Decimal("0")
    for record in records:
        raw = record.get(field, "UNKNOWN")
        try:
            parsed = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return "UNKNOWN"
        if parsed < 0:
            return "UNKNOWN"
        total += parsed
    return _decimal_text(total)


def _ratio(numerator: int, denominator: str) -> str:
    if denominator == "UNKNOWN":
        return "UNKNOWN"
    parsed = Decimal(denominator)
    if parsed == 0:
        return "UNDEFINED_ZERO_DENOMINATOR"
    return _decimal_text(Decimal(numerator) / parsed)


def _cost_per_unit(total: str, units: int) -> str:
    if total == "UNKNOWN":
        return "UNKNOWN"
    if units == 0:
        return "UNDEFINED_ZERO_QUALIFIED"
    return _decimal_text(Decimal(total) / Decimal(units))


def _qualification_rate(counts: dict[str, int]) -> str:
    if not counts["candidates"]:
        return "UNDEFINED_NO_CANDIDATES"
    rate = Decimal(counts["qualified"]) * Decimal("100") / Decimal(counts["candidates"])
    return _decimal_text(rate) + "%"


def _active_decision_codes(state: dict[str, Any]) -> str:
    decisions = [
        item.get("decision_code", "INVALID_DECISION_RECORD")
        for item in state["human_decision_queue"]
        if item.get("status") == "PENDING"
    ]
    return ",".join(sorted(decisions)) if decisions else "NONE"


def _external_user_evidence(state: dict[str, Any]) -> tuple[int, int]:
    verified = [
        item
        for item in state["external_users"]
        if item.get("status") == "VERIFIED_EXTERNAL_USER"
    ]
    stronger = sum(
        item.get("evidence_kind") in {"RECEIPT", "REPEAT_USE", "NEW_TASK"}
        for item in verified
    )
    return len(verified), stronger


def _verified_external_reuse_count(state: dict[str, Any]) -> int:
    return len(
        {
            item.get("reuse_id")
            for item in state.get("external_reuse_events", [])
            if item.get("status") == "VERIFIED" and item.get("outcome") == "SUCCESS"
        }
    )


def _integrity_incident_counts(state: dict[str, Any]) -> dict[str, int]:
    return {
        status: sum(
            item.get("status") == status for item in state.get("integrity_incidents", [])
        )
        for status in ("CONTROLLED", "UNCONTROLLED")
    }


def _continuation_gates(
    pilot: dict[str, Any],
    counts: dict[str, int],
    state: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, bool]:
    discovery_records = [record for record in records if record.get("stage") == "DISCOVERY"]
    founder_hours = _known_total(discovery_records, "founder_hours")
    compute_usd = _known_total(discovery_records, "compute_usd")
    verified_users, strong_user_evidence = _external_user_evidence(state)
    uncontrolled_incidents = sum(
        item.get("status") == "UNCONTROLLED" for item in state["integrity_incidents"]
    )
    return {
        "TASK_SUPPLY_AND_ACQUISITION_COST": (
            counts["candidates"] >= pilot["targets"]["deduplicated_external_candidates"]
            and counts["qualified"] >= pilot["targets"]["qualified_tasks"]
            and (founder_hours != "UNKNOWN" or compute_usd != "UNKNOWN")
        ),
        "BEHAVIOR_VERIFIED_TARGET": (
            counts["behavior_verified"]
            >= pilot["targets"]["independently_behavior_verified_tasks"]
        ),
        "RELEASE_REVIEW_EXPERIENCE_TARGET": (
            pilot["targets"]["release_review_experiences_min"]
            <= counts["release_review_experiences"]
            <= pilot["targets"]["release_review_experiences_max"]
        ),
        "HELD_OUT_POSITIVE_TRANSFERS": (
            counts["held_out_positive_transfers"]
            >= pilot["targets"]["held_out_positive_transfers"]
        ),
        "NO_UNCONTROLLED_INCIDENTS": (
            uncontrolled_incidents <= pilot["targets"]["max_uncontrolled_incidents"]
        ),
        "THREE_VERIFIED_EXTERNAL_USERS": (
            verified_users >= pilot["targets"]["verified_external_users"]
        ),
        "EXTERNAL_USER_STRONG_EVIDENCE": (
            strong_user_evidence
            >= pilot["targets"]["external_users_with_strong_evidence"]
        ),
    }


def _recommendation(gates: dict[str, bool], counts: dict[str, int]) -> str:
    if all(gates.values()):
        return "CONTINUE"
    if gates["NO_UNCONTROLLED_INCIDENTS"] and (
        counts["qualified"] >= 5
        or counts["behavior_verified"] > 0
        or counts["held_out_positive_transfers"] > 0
    ):
        return "NARROW"
    return "STOP"


def generate_due_reports(
    root: Path,
    pilot: dict[str, Any],
    backlog: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
) -> list[str]:
    reports = paths(root)["reports"]
    reports.mkdir(parents=True, exist_ok=True)
    start = parse_time(pilot["activation"]["starts_at"])
    completed_weeks = min(6, max(0, int((now - start).total_seconds() // (7 * 86400))))
    counts = _counts(backlog)
    records = _round_records(root)
    worker_events = state.get("worker_events", [])
    cumulative_founder_hours = _known_total(records, "founder_hours")
    cumulative_compute_usd = _known_total([*records, *worker_events], "compute_usd")
    discovery_records = [record for record in records if record.get("stage") == "DISCOVERY"]
    acquisition_founder_hours = _known_total(discovery_records, "founder_hours")
    acquisition_compute_usd = _known_total(discovery_records, "compute_usd")
    created: list[str] = []
    for week in range(1, completed_weeks + 1):
        report = reports / f"week-{week:02d}.md"
        if report.exists() and not _weekly_report_schema_errors(report, week, start):
            continue
        window_start = start + timedelta(days=7 * (week - 1))
        window_end = start + timedelta(days=7 * week)
        week_records = [
            record
            for record in records
            if window_start <= parse_time(record["completed_at"]) < window_end
        ]
        week_worker_events = [
            event
            for event in worker_events
            if window_start <= parse_time(event["started_at"]) < window_end
        ]
        priority = {"HARMFUL": 6, "SUCCESS": 5, "NEUTRAL": 4, "FAILURE": 3, "INVALID": 2, "BLOCKED": 1}
        important = max(
            week_records,
            key=lambda item: (priority.get(item.get("outcome"), 0), item.get("completed_at", "")),
            default=None,
        )
        highlight = (
            f"{important['outcome']}:{important['task_id']}:{important['oracle_status']}"
            if important
            else "NO_ROUND_RECORDED"
        )
        outcome_counts = {
            outcome: sum(record.get("outcome") == outcome for record in week_records)
            for outcome in ("SUCCESS", "NEUTRAL", "HARMFUL", "FAILURE", "INVALID", "BLOCKED")
        }
        week_worker_starts = sum(
            int(record.get("worker_starts", 0)) for record in week_records
        ) + len(week_worker_events)
        verified_users, strong_user_evidence = _external_user_evidence(state)
        verified_external_reuse = _verified_external_reuse_count(state)
        weekly_founder_hours = _known_total(week_records, "founder_hours")
        weekly_compute_usd = _known_total(
            [*week_records, *week_worker_events], "compute_usd"
        )
        model_usage = [
            {
                "call_method": event.get("call_method", "UNKNOWN"),
                "compute_usd": event.get("compute_usd", "UNKNOWN"),
                "configured_model": event.get("configured_model", "UNKNOWN"),
                "kind": event.get("kind", "UNKNOWN"),
                "model": event.get("model", "UNKNOWN"),
                "model_attestation": event.get("model_attestation", "UNKNOWN"),
                "retry_count": event.get("retry_count", "UNKNOWN"),
                "status": event.get("status", "UNKNOWN"),
                "total_tokens": event.get("total_tokens", "UNKNOWN"),
            }
            for event in week_worker_events
        ]
        content = "\n".join(
            [
                f"# AEG Foundry week {week}",
                "",
                f"- Window start: `{format_time(window_start)}`",
                f"- Window end: `{format_time(window_end)}`",
                f"- Candidates: `{counts['candidates']} / {pilot['targets']['deduplicated_external_candidates']}`",
                f"- Qualified: `{counts['qualified']} / {pilot['targets']['qualified_tasks']}`",
                f"- Qualification rate: `{_qualification_rate(counts)}`",
                f"- Behavior verified: `{counts['behavior_verified']} / {pilot['targets']['independently_behavior_verified_tasks']}`",
                f"- Release-review Experiences: `{counts['release_review_experiences']} / {pilot['targets']['release_review_experiences_min']}-{pilot['targets']['release_review_experiences_max']}`",
                f"- Positive held-out transfers: `{counts['held_out_positive_transfers']} / {pilot['targets']['held_out_positive_transfers']}`",
                f"- Verified external users: `{verified_users} / {pilot['targets']['verified_external_users']}`",
                f"- External users with strong evidence: `{strong_user_evidence} / {pilot['targets']['external_users_with_strong_evidence']}`",
                f"- Independently verified external successful reuses: `{verified_external_reuse}`",
                f"- Most important recorded outcome: `{highlight}`",
                f"- Weekly outcome counts: `{json.dumps(outcome_counts, sort_keys=True, separators=(',', ':'))}`",
                f"- Weekly founder hours: `{weekly_founder_hours}`",
                f"- Weekly compute USD: `{weekly_compute_usd}`",
                f"- Acquisition founder hours per qualified task: `{_cost_per_unit(acquisition_founder_hours, counts['qualified'])}`",
                f"- Acquisition compute USD per qualified task: `{_cost_per_unit(acquisition_compute_usd, counts['qualified'])}`",
                f"- Verified external reuse per founder hour: `{_ratio(verified_external_reuse, cumulative_founder_hours)}`",
                f"- Verified external reuse per compute USD: `{_ratio(verified_external_reuse, cumulative_compute_usd)}`",
                f"- Weekly worker starts: `{week_worker_starts}`",
                f"- Weekly model usage events: `{json.dumps(model_usage, sort_keys=True, separators=(',', ':')) if model_usage else 'NONE'}`",
                f"- Founder interventions: `{state['founder_interventions']}`",
                f"- Integrity incident counts: `{json.dumps(_integrity_incident_counts(state), sort_keys=True, separators=(',', ':'))}`",
                f"- Account quota observation: `UNKNOWN_NOT_PUBLICLY_RECORDED`",
                f"- Bottleneck: `{'BLOCKED_ENVIRONMENT' if counts['blocked_environment'] else 'NONE'}`",
                f"- Next focus: `{backlog['work_items'][-1]['next_step_code']}`",
                f"- Human decision queue: `{_active_decision_codes(state)}`",
                "",
                "`SUCCESS` above is a round outcome, not a held-out positive transfer.",
                "No milestone classification is inferred from missing evidence.",
            ]
        ) + "\n"
        atomic_write(report, content)
        created.append(str(report.relative_to(root)))
    if now >= parse_time(pilot["activation"]["ends_at"]):
        final = reports / "final.md"
        if not final.exists():
            gates = _continuation_gates(pilot, counts, state, records)
            recommendation = _recommendation(gates, counts)
            gate_lines = [
                f"- Gate {name}: `{'PASS' if passed else 'FAIL'}`"
                for name, passed in gates.items()
            ]
            verified_users, strong_user_evidence = _external_user_evidence(state)
            verified_reuse = _verified_external_reuse_count(state)
            atomic_write(
                final,
                "\n".join(
                    [
                        "# AEG Experience Foundry Pilot final",
                        "",
                        f"- Recommendation: `{recommendation}`",
                        f"- Candidates: `{counts['candidates']}`",
                        f"- Qualified: `{counts['qualified']}`",
                        f"- Qualification rate: `{_qualification_rate(counts)}`",
                        f"- Behavior verified: `{counts['behavior_verified']}`",
                        f"- Positive held-out transfers: `{counts['held_out_positive_transfers']}`",
                        f"- Release-review Experiences: `{counts['release_review_experiences']}`",
                        f"- Verified external users: `{verified_users}`",
                        f"- External users with receipt, repeat use, or new task: `{strong_user_evidence}`",
                        f"- Independently verified external successful reuses: `{verified_reuse}`",
                        f"- Founder hours: `{cumulative_founder_hours}`",
                        f"- Compute USD: `{cumulative_compute_usd}`",
                        f"- Acquisition founder hours per qualified task: `{_cost_per_unit(acquisition_founder_hours, counts['qualified'])}`",
                        f"- Acquisition compute USD per qualified task: `{_cost_per_unit(acquisition_compute_usd, counts['qualified'])}`",
                        f"- Verified external reuse per founder hour: `{_ratio(verified_reuse, cumulative_founder_hours)}`",
                        f"- Verified external reuse per compute USD: `{_ratio(verified_reuse, cumulative_compute_usd)}`",
                        f"- Human decision queue: `{_active_decision_codes(state)}`",
                        f"- Integrity incident counts: `{json.dumps(_integrity_incident_counts(state), sort_keys=True, separators=(',', ':'))}`",
                        "",
                        *gate_lines,
                        "",
                        "The fixed term ended; no new experiment may start.",
                    ]
                ) + "\n",
            )
            created.append(str(final.relative_to(root)))
    return created


def _changed_paths(root: Path) -> set[str]:
    lines = run_git(root, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
    result: set[str] = set()
    for line in lines:
        raw = line[3:]
        if " -> " in raw:
            before, after = raw.split(" -> ", 1)
            result.update((before, after))
        else:
            result.add(raw)
    return result


def _allowed_with_reports(path: str, bootstrap: bool) -> bool:
    allowed = BOOTSTRAP_PATHS if bootstrap else PUBLIC_RUNTIME_PATHS
    return (
        path in allowed
        or path.startswith("foundry/reports/")
        or path.startswith("foundry/experiences/")
    )


def persist(root: Path, run_id: str, push: bool, bootstrap: bool = False) -> dict[str, Any]:
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        repository_preflight(root, pilot)
        if state.get("active_round"):
            raise LeaseError("finish or checkpoint the active round before persistence")
        if state.get("pending_effect"):
            raise LeaseError("reconcile the prior external effect before persistence")
        if state.get("last_round_id") != run_id:
            raise ConfigError("persist run ID is not the last completed round")
        validate(root, check_git=False)
        scan = audit_public(root)
        if not scan["ok"]:
            raise ConfigError("public audit failed: " + "; ".join(scan["errors"]))
        initial_changed = _changed_paths(root)
        unsafe = sorted(path for path in initial_changed if not _allowed_with_reports(path, bootstrap))
        if unsafe:
            raise UnsafeRepositoryError(f"unexpected changed paths: {unsafe}")
        if not push:
            raise ConfigError("pilot persistence requires explicit --push")
        effect = {
            "effect_id": f"AEG-I-{uuid.uuid4().hex}",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": format_time(utc_now()),
            "round_id": run_id,
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        state["pending_effect"] = effect
        atomic_write_json(paths(root)["state"], state)
        render_status(root)
        changed = _changed_paths(root)
        unsafe = sorted(path for path in changed if not _allowed_with_reports(path, bootstrap))
        if unsafe:
            raise UnsafeRepositoryError(f"unexpected changed paths after intent: {unsafe}")
        if not changed:
            raise ConfigError("no checkpoint changes to persist")
        run_git(root, "add", "--", *sorted(changed))
        staged = set(run_git(root, "diff", "--cached", "--name-only").stdout.splitlines())
        if staged != changed:
            raise UnsafeRepositoryError("staged checkpoint set does not match changed-path allowlist")
        subject = f"chore(foundry): checkpoint {run_id}"
        run_git(
            root,
            "-c",
            "user.name=AEG Foundry Automation",
            "-c",
            "user.email=aeg-foundry@users.noreply.github.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--no-verify",
            "-m",
            subject,
        )
        commit = git_value(root, "rev-parse", "HEAD")
        branch = pilot["execution"]["required_branch"]
        result = run_git(root, "push", pilot["source"]["remote"], f"HEAD:refs/heads/{branch}", check=False)
        if result.returncode != 0:
            raise UnsafeRepositoryError(
                "push did not report success; intent remains unresolved and must be verified before retry"
            )
        if _changed_paths(root):
            raise UnsafeRepositoryError("worktree is not clean after checkpoint push")
        return {
            "commit": commit,
            "effect_id": effect["effect_id"],
            "push_reported_success": True,
            "remote_branch": branch,
            "reconciliation_required_next_round": True,
        }


def output(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=ROOT)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("status")
    begin = commands.add_parser("begin-round")
    begin.add_argument("--reconcile-push", action="store_true")
    intent = commands.add_parser("record-intent")
    intent.add_argument("--round-id", required=True)
    intent.add_argument("--effect-type", required=True, choices=sorted(EFFECT_TYPES - {"PUSH_PILOT_BRANCH"}))
    intent.add_argument("--target-code", required=True)
    intent.add_argument("--environment-id")
    intent.add_argument("--target-revision")
    observe_source = commands.add_parser("observe-source-ref")
    observe_source.add_argument("--round-id", required=True)
    observe_source.add_argument("--effect-id", required=True)
    maintenance_intent = commands.add_parser("record-maintenance-intent")
    maintenance_intent.add_argument(
        "--effect-type", required=True, choices=sorted(EFFECT_TYPES - {"PUSH_PILOT_BRANCH"})
    )
    maintenance_intent.add_argument("--target-code", required=True)
    resolve = commands.add_parser("resolve-intent")
    resolve.add_argument("--effect-id", required=True)
    resolve.add_argument("--outcome", required=True, choices=("COMPLETED", "FAILED", "NOT_PERFORMED"))
    resolve.add_argument("--command-argv-json")
    resolve.add_argument("--exit-code", type=int)
    resolve.add_argument("--oracle-observation", choices=("SUCCESS", "FAILURE"))
    resolve.add_argument("--evidence-digest-sha256")
    resolve.add_argument("--evidence-summary-code", action="append")
    resolve.add_argument("--failure-code")
    finish = commands.add_parser("finish-round")
    finish.add_argument("--round-id", required=True)
    finish.add_argument("--outcome", required=True, choices=sorted(OUTCOMES))
    finish.add_argument("--oracle-status", required=True, choices=sorted(ORACLE_STATUSES))
    finish.add_argument("--next-step-code", required=True)
    finish.add_argument("--task-status", choices=sorted(TASK_STATUSES - {"READY", "IN_PROGRESS"}))
    finish.add_argument("--failure-code")
    finish.add_argument("--failure-class", default="NONE", choices=sorted(FAILURE_CLASSES))
    finish.add_argument("--founder-hours", default="UNKNOWN")
    finish.add_argument("--compute-usd", default="UNKNOWN")
    finish.add_argument("--model", default="UNKNOWN")
    finish.add_argument("--configured-model", default="UNKNOWN")
    finish.add_argument("--model-attestation", default="UNKNOWN")
    finish.add_argument("--call-method", default="UNKNOWN")
    finish.add_argument("--input-tokens", default="UNKNOWN")
    finish.add_argument("--output-tokens", default="UNKNOWN")
    finish.add_argument("--total-tokens", default="UNKNOWN")
    finish.add_argument("--retry-count", type=int, default=0)
    finish.add_argument("--compute-cost-basis-code", default="UNKNOWN")
    finish.add_argument("--market-estimate-usd", default="UNKNOWN")
    finish.add_argument("--market-estimate-source-code", default="UNKNOWN")
    finish.add_argument("--quota-observation-code", default="UNKNOWN")
    finish.add_argument("--worker-starts", type=int)
    worker = commands.add_parser("register-worker")
    worker.add_argument("--kind", required=True)
    worker.add_argument("--model", required=True)
    worker.add_argument("--channel", default="MODEL_WORKER")
    worker.add_argument("--configured-model", default="UNKNOWN")
    worker.add_argument("--call-method", default="UNKNOWN")
    worker.add_argument("--round-id")
    worker_finish = commands.add_parser("finish-worker")
    worker_finish.add_argument("--event-id", required=True)
    worker_finish.add_argument(
        "--status",
        required=True,
        choices=(
            "PASSED",
            "FAILED",
            "INFRASTRUCTURE_FAILED",
            "AUTH_FAILED",
            "QUOTA_FAILED",
        ),
    )
    worker_finish.add_argument("--failure-code")
    worker_finish.add_argument("--input-tokens", default="UNKNOWN")
    worker_finish.add_argument("--output-tokens", default="UNKNOWN")
    worker_finish.add_argument("--total-tokens", default="UNKNOWN")
    worker_finish.add_argument("--compute-usd", default="UNKNOWN")
    worker_finish.add_argument("--model-attestation", default="UNKNOWN")
    worker_finish.add_argument("--retry-count", type=int, default=0)
    worker_finish.add_argument("--compute-cost-basis-code", default="UNKNOWN")
    worker_finish.add_argument("--market-estimate-usd", default="UNKNOWN")
    worker_finish.add_argument("--market-estimate-source-code", default="UNKNOWN")
    pause_command = commands.add_parser("pause")
    pause_command.add_argument("--reason-code", required=True)
    pause_command.add_argument("--push", action="store_true")
    commands.add_parser("resume")
    commands.add_parser("reconcile-push")
    automation = commands.add_parser("set-automation")
    automation.add_argument("--id", required=True)
    automation.add_argument("--status", required=True, choices=("ACTIVE", "PAUSED", "DELETED"))
    automation.add_argument("--next-run-at", required=True)
    automation.add_argument("--project-id", required=True)
    automation.add_argument("--location-code", required=True)
    commands.add_parser("audit-public")
    persistence = commands.add_parser("persist")
    persistence.add_argument("--run-id", required=True)
    persistence.add_argument("--push", action="store_true")
    persistence.add_argument("--bootstrap", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    root = arguments.root.resolve()
    try:
        if arguments.command == "validate":
            output(validate(root))
        elif arguments.command == "status":
            pilot, backlog, state = load_all(root)
            render_status(root, pilot, backlog, state)
            output({"ok": True, "status_path": "foundry/STATUS.md", "counts": _counts(backlog)})
        elif arguments.command == "begin-round":
            output(begin_round(root, reconcile_prior_push=arguments.reconcile_push))
        elif arguments.command == "record-intent":
            output(
                record_intent(
                    root,
                    arguments.round_id,
                    arguments.effect_type,
                    arguments.target_code,
                    environment_id=arguments.environment_id,
                    target_revision=arguments.target_revision,
                )
            )
        elif arguments.command == "observe-source-ref":
            output(observe_source_ref(root, arguments.round_id, arguments.effect_id))
        elif arguments.command == "record-maintenance-intent":
            output(record_maintenance_intent(root, arguments.effect_type, arguments.target_code))
        elif arguments.command == "resolve-intent":
            command_argv = None
            if arguments.command_argv_json is not None:
                try:
                    command_argv = json.loads(arguments.command_argv_json)
                except json.JSONDecodeError as error:
                    raise ConfigError("command argv JSON is invalid") from error
                if not isinstance(command_argv, list):
                    raise ConfigError("command argv JSON must encode a list")
            output(
                resolve_intent(
                    root,
                    arguments.effect_id,
                    arguments.outcome,
                    command_argv=command_argv,
                    exit_code=arguments.exit_code,
                    oracle_observation=arguments.oracle_observation,
                    evidence_digest_sha256=arguments.evidence_digest_sha256,
                    evidence_summary_codes=arguments.evidence_summary_code,
                    failure_code=arguments.failure_code,
                )
            )
        elif arguments.command == "finish-round":
            output(
                finish_round(
                    root,
                    arguments.round_id,
                    arguments.outcome,
                    arguments.oracle_status,
                    arguments.next_step_code,
                    task_status=arguments.task_status,
                    failure_code=arguments.failure_code,
                    failure_class=arguments.failure_class,
                    founder_hours=arguments.founder_hours,
                    compute_usd=arguments.compute_usd,
                    model=arguments.model,
                    configured_model=arguments.configured_model,
                    model_attestation=arguments.model_attestation,
                    call_method=arguments.call_method,
                    input_tokens=arguments.input_tokens,
                    output_tokens=arguments.output_tokens,
                    total_tokens=arguments.total_tokens,
                    retry_count=arguments.retry_count,
                    compute_cost_basis_code=arguments.compute_cost_basis_code,
                    market_estimate_usd=arguments.market_estimate_usd,
                    market_estimate_source_code=arguments.market_estimate_source_code,
                    quota_observation_code=arguments.quota_observation_code,
                    worker_starts=arguments.worker_starts,
                )
            )
        elif arguments.command == "register-worker":
            output(
                register_worker(
                    root,
                    arguments.kind,
                    arguments.model,
                    arguments.channel,
                    configured_model=arguments.configured_model,
                    call_method=arguments.call_method,
                    round_id=arguments.round_id,
                )
            )
        elif arguments.command == "finish-worker":
            output(
                finish_worker(
                    root,
                    arguments.event_id,
                    arguments.status,
                    failure_code=arguments.failure_code,
                    input_tokens=arguments.input_tokens,
                    output_tokens=arguments.output_tokens,
                    total_tokens=arguments.total_tokens,
                    compute_usd=arguments.compute_usd,
                    model_attestation=arguments.model_attestation,
                    retry_count=arguments.retry_count,
                    compute_cost_basis_code=arguments.compute_cost_basis_code,
                    market_estimate_usd=arguments.market_estimate_usd,
                    market_estimate_source_code=arguments.market_estimate_source_code,
                )
            )
        elif arguments.command == "pause":
            if arguments.push:
                output(pause_and_persist(root, arguments.reason_code))
            else:
                output(pause(root, arguments.reason_code))
        elif arguments.command == "resume":
            output(resume(root))
        elif arguments.command == "reconcile-push":
            output(reconcile_push_command(root))
        elif arguments.command == "set-automation":
            output(
                set_automation(
                    root,
                    arguments.id,
                    arguments.status,
                    arguments.next_run_at,
                    arguments.project_id,
                    arguments.location_code,
                )
            )
        elif arguments.command == "audit-public":
            result = audit_public(root)
            output(result)
            if not result["ok"]:
                return 11
        elif arguments.command == "persist":
            output(persist(root, arguments.run_id, arguments.push, arguments.bootstrap))
        else:
            raise ConfigError("unknown command")
        return 0
    except FoundryError as error:
        output({"ok": False, "error": str(error), "exit_code": error.exit_code})
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main())
