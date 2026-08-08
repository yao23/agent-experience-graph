"""Fail-closed local scheduler protections for the Autonomous Lab."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
from typing import Any


class SchedulerError(Exception):
    """Base class for scheduler-specific failures."""


class LeaseHeldError(SchedulerError):
    """Raised when an execution lease exists or requires recovery."""


class UnsafeWorktreeError(SchedulerError):
    """Raised when local repository state is unsafe for unattended mutation."""


class SchedulerConfigError(SchedulerError):
    """Raised when scheduler selection or configuration is invalid."""


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_git(repo_root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise UnsafeWorktreeError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def repository_root(repo_root: Path) -> Path:
    discovered = Path(run_git(repo_root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if discovered != repo_root.resolve():
        raise UnsafeWorktreeError(
            f"repository root mismatch: expected {repo_root.resolve()}, found {discovered}"
        )
    return discovered


def git_common_dir(repo_root: Path) -> Path:
    raw = run_git(repo_root, "rev-parse", "--git-common-dir").stdout.strip()
    path = Path(raw)
    return (repo_root / path).resolve() if not path.is_absolute() else path.resolve()


def load_config(lab_root: Path) -> dict[str, Any]:
    path = lab_root / "scheduler" / "config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise SchedulerConfigError(f"scheduler configuration is unreadable: {path}") from error
    required = {
        "schema_version",
        "execution_mode",
        "allowed_branches",
        "lease_ttl_seconds",
        "verified_library_blob_oid",
        "verified_library_sha256",
    }
    if config.get("schema_version") != 1 or not required.issubset(config):
        raise SchedulerConfigError("scheduler configuration fields are incomplete")
    if config["execution_mode"] != "local_project":
        raise SchedulerConfigError("only fail-closed local_project execution is supported")
    if not isinstance(config["allowed_branches"], list) or not config["allowed_branches"]:
        raise SchedulerConfigError("allowed_branches must be a non-empty list")
    if not isinstance(config["lease_ttl_seconds"], int) or config["lease_ttl_seconds"] < 60:
        raise SchedulerConfigError("lease_ttl_seconds must be at least 60")
    return config


def operational_dir(repo_root: Path) -> Path:
    path = git_common_dir(repo_root) / "aeg-autonomous-lab"
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def _audit_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(
        {key: value for key, value in record.items() if key != "event_sha256"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def append_lease_audit(repo_root: Path, event_type: str, timestamp: str, run_id: str, **details: Any) -> None:
    """Append an operational lease event outside tracked repository content."""
    directory = operational_dir(repo_root)
    path = directory / "lease-audit.jsonl"
    lock_path = directory / "lease-audit.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prior_hash: str | None = None
        sequence = 1
        if path.is_file():
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
            if lines:
                previous = json.loads(lines[-1])
                prior_hash = previous["event_sha256"]
                sequence = previous["sequence"] + 1
        record = {
            "sequence": sequence,
            "event_type": event_type,
            "timestamp": timestamp,
            "run_id": run_id,
            "previous_event_sha256": prior_hash,
            **details,
        }
        record["event_sha256"] = _audit_hash(record)
        with path.open("a", encoding="utf-8") as audit:
            audit.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            audit.flush()
            os.fsync(audit.fileno())
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class ExecutionLease:
    """Atomic lease shared by every worktree that uses the same Git common directory."""

    def __init__(self, repo_root: Path, config: dict[str, Any]) -> None:
        self.repo_root = repo_root.resolve()
        self.config = config
        self.path = operational_dir(self.repo_root) / "execution-lease.json"
        self.run_id: str | None = None

    def acquire(
        self,
        run_id: str,
        acquired_at: str,
        experiment_id: str | None,
        expected_starting_state: str | None,
        expected_state_sha256: str | None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        expires = parse_timestamp(acquired_at) + timedelta(seconds=self.config["lease_ttl_seconds"])
        lease = {
            "schema_version": 1,
            "run_id": run_id,
            "actor_identity": actor or f"{socket.gethostname()}:{os.getpid()}",
            "acquired_at": acquired_at,
            "expires_at": format_timestamp(expires),
            "repository_root": str(self.repo_root),
            "experiment_id": experiment_id,
            "expected_starting_state": expected_starting_state,
            "expected_state_sha256": expected_state_sha256,
        }
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as error:
            existing = self.read()
            event = "lease_stale_detected" if parse_timestamp(existing["expires_at"]) <= parse_timestamp(acquired_at) else "lease_rejected"
            append_lease_audit(
                self.repo_root,
                event,
                acquired_at,
                run_id,
                holder_run_id=existing.get("run_id"),
                expires_at=existing.get("expires_at"),
            )
            if event == "lease_stale_detected":
                raise LeaseHeldError(
                    "stale execution lease detected; run `python3 autonomous-lab/scripts/lab.py recover-stale-lease`"
                ) from error
            raise LeaseHeldError(
                f"execution lease is held by run {existing.get('run_id')} until {existing.get('expires_at')}"
            ) from error
        try:
            os.write(descriptor, (json.dumps(lease, indent=2, sort_keys=True) + "\n").encode())
        finally:
            os.close(descriptor)
        self.run_id = run_id
        append_lease_audit(
            self.repo_root,
            "lease_acquired",
            acquired_at,
            run_id,
            experiment_id=experiment_id,
            expires_at=lease["expires_at"],
            repository_root=str(self.repo_root),
            expected_starting_state=expected_starting_state,
            expected_state_sha256=expected_state_sha256,
        )
        return lease

    def read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise LeaseHeldError("execution lease exists but is unreadable; manual inspection is required") from error

    def release(self, timestamp: str, outcome: str) -> None:
        if self.run_id is None:
            return
        existing = self.read()
        if existing.get("run_id") != self.run_id:
            raise LeaseHeldError("execution lease ownership changed; refusing to remove it")
        append_lease_audit(
            self.repo_root,
            "lease_released",
            timestamp,
            self.run_id,
            outcome=outcome,
        )
        self.path.unlink()
        self.run_id = None

    def recover_stale(self, timestamp: str, recovery_run_id: str) -> dict[str, Any]:
        existing = self.read()
        if parse_timestamp(existing["expires_at"]) > parse_timestamp(timestamp):
            append_lease_audit(
                self.repo_root,
                "lease_recovery_rejected",
                timestamp,
                recovery_run_id,
                holder_run_id=existing.get("run_id"),
                expires_at=existing.get("expires_at"),
            )
            raise LeaseHeldError("lease is not expired and must never be broken")
        self.path.unlink()
        append_lease_audit(
            self.repo_root,
            "lease_recovered",
            timestamp,
            recovery_run_id,
            recovered_run_id=existing.get("run_id"),
            expired_at=existing.get("expires_at"),
        )
        return existing


def _git_operation_in_progress(common: Path) -> str | None:
    markers = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_LOG",
        "rebase-merge",
        "rebase-apply",
    )
    return next((marker for marker in markers if (common / marker).exists()), None)


def _expected_mutation_paths(entry: dict[str, Any] | None) -> set[str]:
    paths = {
        "autonomous-lab/experiments/registry.yaml",
        "autonomous-lab/ledger/events.jsonl",
        "autonomous-lab/reports/current-status.json",
        "autonomous-lab/reports/current-status.md",
        "autonomous-lab/reports/next-human-action.md",
    }
    if entry:
        for key in ("state_path", "scorecard_path", "escalation_path"):
            if entry.get(key):
                paths.add(entry[key])
        paths.update(entry.get("runtime_evidence_paths", []))
    return paths


def preflight_worktree(
    repo_root: Path,
    lab_root: Path,
    config: dict[str, Any],
    selected_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    repository_root(repo_root)
    branch_result = run_git(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch_result.returncode != 0:
        raise UnsafeWorktreeError("detached HEAD is not allowed for scheduled local-project execution")
    branch = branch_result.stdout.strip()
    if branch not in config["allowed_branches"]:
        raise UnsafeWorktreeError(f"branch {branch!r} is not allowed for scheduled execution")
    marker = _git_operation_in_progress(git_common_dir(repo_root))
    if marker:
        raise UnsafeWorktreeError(f"Git operation is in progress: {marker}")

    allowed = _expected_mutation_paths(selected_entry)
    status = run_git(repo_root, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
    conflicts: list[str] = []
    for line in status:
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if code == "??":
            if path == "autonomous-lab" or path.startswith("autonomous-lab/"):
                conflicts.append(f"untracked Autonomous Lab artifact: {path}")
            continue
        if code[0] != " ":
            conflicts.append(f"staged or conflicted user change: {path}")
        elif path not in allowed:
            conflicts.append(f"unrelated tracked modification: {path}")
    if conflicts:
        raise UnsafeWorktreeError("; ".join(conflicts))

    verified = repo_root / "experiences" / "verified.json"
    actual_sha = hashlib.sha256(verified.read_bytes()).hexdigest()
    actual_blob = run_git(repo_root, "hash-object", "experiences/verified.json").stdout.strip()
    if actual_sha != config["verified_library_sha256"] or actual_blob != config["verified_library_blob_oid"]:
        raise UnsafeWorktreeError("experiences/verified.json differs from the scheduler baseline")
    return {
        "repository_root": str(repo_root.resolve()),
        "branch": branch,
        "tracked_modifications": [line for line in status if line[:2] != "??"],
        "verified_library_sha256": actual_sha,
        "verified_library_blob_oid": actual_blob,
    }


def write_transient_recovery_request(repo_root: Path, timestamp: str, run_id: str, reason: str) -> Path:
    path = operational_dir(repo_root) / "next-human-action.json"
    payload = {
        "schema_version": 1,
        "kind": "recovery_request",
        "run_id": run_id,
        "created_at": timestamp,
        "reason": reason,
        "requested_action": "Resolve the reported repository conflict manually; do not clean, reset, stash, or discard changes automatically.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
