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
TASK_STATUSES = {
    "READY",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "BLOCKED_ENVIRONMENT",
    "BLOCKED_APPROVAL",
    "BLOCKED_UNCERTAIN_EFFECT",
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
GITHUB_ISSUE_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/issues/[1-9][0-9]*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CHANNEL_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
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
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigError(f"invalid UTC timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ConfigError(f"timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
    }


def load_all(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    located = paths(root)
    return load_json(located["pilot"]), load_json(located["backlog"]), load_json(located["state"])


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
    return {"ok": not errors, "errors": errors, "scanned_private_directory": False}


def validate(root: Path, check_git: bool = True) -> dict[str, Any]:
    pilot, backlog, state = load_all(root)
    errors: list[str] = []
    if pilot.get("schema_version") != 1 or pilot.get("config_version") != "0.1.0":
        errors.append("unsupported pilot schema or config version")
    try:
        starts = parse_time(pilot["activation"]["starts_at"])
        ends = parse_time(pilot["activation"]["ends_at"])
        if ends - starts != timedelta(days=42):
            errors.append("pilot duration must remain exactly 42 days")
    except (KeyError, ConfigError) as error:
        errors.append(str(error))
    budgets = pilot.get("budgets", {})
    expected_budgets = {
        "max_round_seconds": 2700,
        "max_rounds_per_day": 2,
        "max_rounds_total": 84,
        "max_worker_starts_per_day": 6,
    }
    if budgets != expected_budgets:
        errors.append("fixed budget values changed")
    if pilot.get("authorization", {}).get("new_paid_api_usd") != 0:
        errors.append("new paid API budget must remain zero")
    try:
        source_remote_head_ref(pilot)
    except (KeyError, ConfigError) as error:
        errors.append(str(error))
    if backlog.get("schema_version") != 1 or state.get("schema_version") != 1:
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

    candidate_ids: set[str] = set()
    dedupe: set[tuple[str, int]] = set()
    for candidate in backlog.get("candidates", []):
        candidate_id = candidate.get("candidate_id")
        repository = candidate.get("repository")
        number = candidate.get("issue_number")
        if not isinstance(candidate_id, str) or candidate_id in candidate_ids:
            errors.append("candidate IDs must be unique strings")
        else:
            candidate_ids.add(candidate_id)
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

    task_ids: set[str] = set()
    in_progress: list[dict[str, Any]] = []
    for task in backlog.get("work_items", []):
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task_id in task_ids:
            errors.append("task IDs must be unique strings")
        else:
            task_ids.add(task_id)
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"invalid status for {task_id}")
        channel_code = task.get("channel_code")
        if channel_code not in channels:
            errors.append(f"unknown execution channel for {task_id}")
        if not set(task.get("candidate_ids", [])).issubset(candidate_ids):
            errors.append(f"unknown candidate reference for {task_id}")
        if task.get("status") == "IN_PROGRESS":
            in_progress.append(task)
            if not isinstance(task.get("claim"), dict):
                errors.append(f"in-progress task {task_id} has no claim")
    active = state.get("active_round")
    if active is None and in_progress:
        errors.append("in-progress task exists without active round")
    if active is not None:
        if len(in_progress) != 1 or in_progress[0].get("task_id") != active.get("task_id"):
            errors.append("active round and claimed task disagree")
    if state.get("rounds_completed", 0) > state.get("rounds_started", 0):
        errors.append("completed round count exceeds started round count")
    if state.get("pilot_status") not in {"ACTIVE", "PAUSED", "EXPIRED"}:
        errors.append("invalid pilot status")
    if not isinstance(state.get("founder_interventions"), int) or state.get(
        "founder_interventions", -1
    ) < 0:
        errors.append("founder interventions must be a non-negative integer")
    for state_list in ("external_users", "human_decision_queue", "integrity_incidents"):
        if not isinstance(state.get(state_list), list):
            errors.append(f"{state_list} must be a list")

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
        if round_id in seen_rounds:
            errors.append(f"duplicate completed round ID {round_id}")
        seen_rounds.add(round_id)
        if record.get("outcome") == "SUCCESS":
            successful += 1
            if record.get("oracle_status") != "PASSED":
                errors.append(f"successful round {round_id} lacks a passed oracle")
    if len(seen_rounds) != state.get("rounds_completed"):
        errors.append("round ledger count does not equal completed counter")

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


def synthesize_next_work(
    backlog: dict[str, Any], state: dict[str, Any], pilot: dict[str, Any]
) -> dict[str, Any] | None:
    """Create one bounded continuation unit when the queue is empty but a target is unmet."""

    candidates = backlog["candidates"]
    if len(candidates) >= pilot["targets"]["deduplicated_external_candidates"]:
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
            "target_candidate_count": min(
                len(candidates) + 10,
                pilot["targets"]["deduplicated_external_candidates"],
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
        if reconcile_prior_push:
            reconciliation = reconcile_push(root, pilot, state, now)
        elif state.get("pending_effect"):
            raise LeaseError("an external effect is unresolved; reconciliation is required")
        recovery = _recover_expired_round(backlog, state, now)
        active = state.get("active_round")
        if active:
            raise LeaseError(f"round {active['round_id']} holds the lease until {active['expires_at']}")
        budgets = pilot["budgets"]
        if state["rounds_started"] >= budgets["max_rounds_total"]:
            raise BudgetError("total round budget exhausted")
        counter = _today_counter(state, now)
        if counter["round_starts"] >= budgets["max_rounds_per_day"]:
            raise BudgetError("daily round budget exhausted")
        if counter["worker_starts"] >= budgets["max_worker_starts_per_day"]:
            raise BudgetError("daily worker-start budget exhausted")
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
            synthesized = synthesize_next_work(backlog, state, pilot)
            if synthesized is not None:
                ready = [synthesized]
        if not ready:
            if recovery or reconciliation:
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
            "acquisition_strategy_version_at_start": backlog["discovery"].get(
                "acquisition_strategy_version", 1
            ),
        }
        state["last_remote_ref_sha"] = source_sha
        state["last_charter_sha256"] = charter_sha
        state["rounds_started"] += 1
        counter["round_starts"] += 1
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
            "synthesized_work_item": synthesized is not None,
        }


def record_intent(
    root: Path, round_id: str, effect_type: str, target_code: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        active = state.get("active_round")
        if not active or active["round_id"] != round_id:
            raise LeaseError("intent round does not own the active lease")
        if state.get("pending_effect"):
            raise LeaseError("another external effect is unresolved")
        if effect_type not in EFFECT_TYPES or effect_type == "PUSH_PILOT_BRANCH":
            raise ConfigError("invalid stage effect type")
        effect = {
            "effect_id": f"AEG-I-{uuid.uuid4().hex}",
            "effect_type": effect_type,
            "recorded_at": format_time(now),
            "round_id": round_id,
            "target_code": target_code,
        }
        state["pending_effect"] = effect
        atomic_write_json(paths(root)["state"], state)
        return effect


def record_maintenance_intent(
    root: Path, effect_type: str, target_code: str, now: datetime | None = None
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        if state.get("active_round") or state.get("pending_effect"):
            raise LeaseError("maintenance intent requires no active or unresolved work")
        if effect_type not in EFFECT_TYPES or effect_type == "PUSH_PILOT_BRANCH":
            raise ConfigError("invalid maintenance effect type")
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
    root: Path, effect_id: str, outcome: str, now: datetime | None = None
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
        result = {**pending, "outcome": outcome, "resolved_at": format_time(now)}
        state.setdefault("effect_events", []).append(result)
        state["pending_effect"] = None
        atomic_write_json(paths(root)["state"], state)
        return result


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
    input_tokens: str = "UNKNOWN",
    output_tokens: str = "UNKNOWN",
    worker_starts: int = 1,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    with control_lock(root, pilot):
        active = state.get("active_round")
        if not active or active["round_id"] != round_id:
            raise LeaseError("round does not own the active lease")
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
        counter = _today_counter(state, now)
        if worker_starts < 1:
            raise ConfigError("a round must count its scheduled task worker start")
        if counter["worker_starts"] + worker_starts > pilot["budgets"]["max_worker_starts_per_day"]:
            raise BudgetError("worker-start accounting would exceed the daily budget")
        task = next(item for item in backlog["work_items"] if item["task_id"] == active["task_id"])
        channel_code = task["channel_code"]
        if task["oracle_kind"] == "CANDIDATE_BATCH_SCHEMA_DEDUP_AND_SOURCE_CHECK":
            candidate_gain = len(backlog["candidates"]) - active["candidate_count_at_start"]
            qualified_now = sum(
                item.get("qualification") == "QUALIFIED" for item in backlog["candidates"]
            )
            qualified_gain = qualified_now - active["qualified_count_at_start"]
            if outcome == "SUCCESS" and candidate_gain <= 0:
                raise ConfigError("candidate-batch SUCCESS requires at least one new deduplicated candidate")
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
        if task_status is None:
            task_status = "COMPLETED" if outcome == "SUCCESS" else "FAILED"
        if task_status not in TASK_STATUSES or task_status in {"READY", "IN_PROGRESS"}:
            raise ConfigError("invalid terminal/checkpoint task status")
        task["status"] = task_status
        task["claim"] = None
        task["failure_code"] = failure_code
        task["next_step_code"] = next_step_code
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
            "completed_at": format_time(now),
            "compute_usd": compute_usd,
            "elapsed_seconds": elapsed,
            "failure_code": failure_code,
            "failure_class": failure_class,
            "founder_hours": founder_hours,
            "input_tokens": input_tokens,
            "model": model,
            "next_step_code": next_step_code,
            "oracle_status": oracle_status,
            "outcome": outcome,
            "output_tokens": output_tokens,
            "round_id": round_id,
            "source_ref": active["source_ref"],
            "source_ref_sha": active["source_ref_sha"],
            "source_ref_verified_at": active["source_ref_verified_at"],
            "stage": task["stage"],
            "started_at": active["claimed_at"],
            "task_id": task["task_id"],
            "worker_starts": worker_starts,
        }
        append_jsonl(paths(root)["rounds"], record)
        state["active_round"] = None
        state["last_round_id"] = round_id
        state["rounds_completed"] += 1
        counter["worker_starts"] += worker_starts
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
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    pilot, backlog, state = load_all(root)
    del backlog
    with control_lock(root, pilot):
        if not _channel_is_active(state, channel_code):
            raise PausedError(f"execution channel {channel_code} is not ACTIVE")
        counter = _today_counter(state, now)
        if counter["worker_starts"] >= pilot["budgets"]["max_worker_starts_per_day"]:
            raise BudgetError("daily worker-start budget exhausted")
        event = {
            "channel_code": channel_code,
            "event_id": f"AEG-M-{uuid.uuid4().hex}",
            "kind": kind,
            "model": model,
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
        event.update(
            {
                "completed_at": format_time(now),
                "compute_usd": compute_usd,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
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


def _counts(backlog: dict[str, Any]) -> dict[str, int]:
    candidates = backlog["candidates"]
    work = backlog["work_items"]
    return {
        "candidates": len(candidates),
        "qualified": sum(item["qualification"] == "QUALIFIED" for item in candidates),
        "behavior_verified": sum(item.get("behavior_verification") == "PASSED" for item in candidates),
        "release_review_experiences": sum(item.get("release_review") == "READY" for item in candidates),
        "held_out_positive_transfers": sum(
            item.get("category") == "HELD_OUT_TRANSFER" and item.get("transfer_outcome") == "POSITIVE"
            for item in candidates
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
        f"- Held-out positive transfers: `{counts['held_out_positive_transfers']} / 3`",
        f"- Rounds: `{state['rounds_completed']} completed / {state['rounds_started']} started / {pilot['budgets']['max_rounds_total']} max`",
        "",
        "## Current focus and bottleneck",
        "",
        f"- Selected family: `{backlog['discovery']['selected_family']}`",
        f"- Ready work: `{counts['ready_work']}`",
        f"- Environment-blocked work: `{counts['blocked_environment']}`",
        f"- Approval-blocked work: `{counts['blocked_approval']}`",
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


def _continuation_gates(
    pilot: dict[str, Any],
    counts: dict[str, int],
    state: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, bool]:
    founder_hours = _known_total(records, "founder_hours")
    compute_usd = _known_total(records, "compute_usd")
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
        "HELD_OUT_POSITIVE_TRANSFERS": counts["held_out_positive_transfers"] >= 3,
        "NO_UNCONTROLLED_INCIDENTS": uncontrolled_incidents == 0,
        "THREE_VERIFIED_EXTERNAL_USERS": verified_users >= 3,
        "EXTERNAL_USER_STRONG_EVIDENCE": strong_user_evidence >= 1,
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
    cumulative_founder_hours = _known_total(records, "founder_hours")
    cumulative_compute_usd = _known_total(records, "compute_usd")
    created: list[str] = []
    for week in range(1, completed_weeks + 1):
        report = reports / f"week-{week:02d}.md"
        if report.exists():
            continue
        window_start = start + timedelta(days=7 * (week - 1))
        window_end = start + timedelta(days=7 * week)
        week_records = [
            record
            for record in records
            if window_start <= parse_time(record["completed_at"]) < window_end
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
        week_worker_starts = sum(int(record.get("worker_starts", 0)) for record in week_records)
        content = "\n".join(
            [
                f"# AEG Foundry week {week}",
                "",
                f"- Candidates: `{counts['candidates']} / {pilot['targets']['deduplicated_external_candidates']}`",
                f"- Qualified: `{counts['qualified']} / {pilot['targets']['qualified_tasks']}`",
                f"- Qualification rate: `{_qualification_rate(counts)}`",
                f"- Behavior verified: `{counts['behavior_verified']} / {pilot['targets']['independently_behavior_verified_tasks']}`",
                f"- Positive held-out transfers: `{counts['held_out_positive_transfers']} / 3`",
                f"- Most important recorded outcome: `{highlight}`",
                f"- Weekly outcome counts: `{json.dumps(outcome_counts, sort_keys=True, separators=(',', ':'))}`",
                f"- Weekly founder hours: `{_known_total(week_records, 'founder_hours')}`",
                f"- Weekly compute USD: `{_known_total(week_records, 'compute_usd')}`",
                f"- Weekly worker starts: `{week_worker_starts}`",
                f"- Founder interventions: `{state['founder_interventions']}`",
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
            verified_reuse = counts["behavior_verified"]
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
                        f"- Founder hours: `{cumulative_founder_hours}`",
                        f"- Compute USD: `{cumulative_compute_usd}`",
                        f"- Verified external reuse per founder hour: `{_ratio(verified_reuse, cumulative_founder_hours)}`",
                        f"- Verified external reuse per compute USD: `{_ratio(verified_reuse, cumulative_compute_usd)}`",
                        f"- Human decision queue: `{_active_decision_codes(state)}`",
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
    return path in allowed or path.startswith("foundry/reports/")


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
    finish.add_argument("--input-tokens", default="UNKNOWN")
    finish.add_argument("--output-tokens", default="UNKNOWN")
    finish.add_argument("--worker-starts", type=int, default=1)
    worker = commands.add_parser("register-worker")
    worker.add_argument("--kind", required=True)
    worker.add_argument("--model", required=True)
    worker.add_argument("--channel", default="MODEL_WORKER")
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
            output(record_intent(root, arguments.round_id, arguments.effect_type, arguments.target_code))
        elif arguments.command == "observe-source-ref":
            output(observe_source_ref(root, arguments.round_id, arguments.effect_id))
        elif arguments.command == "record-maintenance-intent":
            output(record_maintenance_intent(root, arguments.effect_type, arguments.target_code))
        elif arguments.command == "resolve-intent":
            output(resolve_intent(root, arguments.effect_id, arguments.outcome))
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
                    input_tokens=arguments.input_tokens,
                    output_tokens=arguments.output_tokens,
                    worker_starts=arguments.worker_starts,
                )
            )
        elif arguments.command == "register-worker":
            output(register_worker(root, arguments.kind, arguments.model, arguments.channel))
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
                )
            )
        elif arguments.command == "pause":
            pause_result = pause(root, arguments.reason_code)
            if arguments.push:
                _, _, paused_state = load_all(root)
                output(
                    {
                        "pause": pause_result,
                        "persistence": persist(
                            root,
                            paused_state["last_round_id"],
                            push=True,
                        ),
                    }
                )
            else:
                output(pause_result)
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
