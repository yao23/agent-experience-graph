#!/usr/bin/env python3
"""Deterministic controller and validator for the AEG Autonomous Lab v0."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import uuid

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from phase0 import Phase0ValidationError, validate_package

from scheduler import (
    ExecutionLease,
    LeaseHeldError,
    SchedulerConfigError,
    UnsafeWorktreeError,
    load_config,
    preflight_worktree,
    persist_transition_commit,
    repository_root,
    write_transient_recovery_request,
)


ACTIVE_STATES = (
    "proposed",
    "screening",
    "preregistered",
    "ready",
    "running",
    "evaluating",
)
TERMINAL_STATES = {
    "completed",
    "rejected",
    "blocked",
    "budget_exhausted",
    "contaminated",
    "escalated",
    "cancelled",
}
ALL_STATES = set(ACTIVE_STATES) | TERMINAL_STATES
TRANSITIONS = {
    "none": {"proposed"},
    "proposed": {"screening", "rejected", "cancelled", "budget_exhausted", "escalated"},
    "screening": {"preregistered", "rejected", "blocked", "budget_exhausted", "cancelled", "escalated"},
    "preregistered": {"ready", "blocked", "budget_exhausted", "contaminated", "cancelled", "escalated"},
    "ready": {"running", "blocked", "budget_exhausted", "cancelled", "escalated"},
    "running": {"evaluating", "blocked", "budget_exhausted", "contaminated", "cancelled", "escalated"},
    "evaluating": {"running", "completed", "blocked", "budget_exhausted", "contaminated", "cancelled", "escalated"},
}
NEXT_STAGE = {
    "proposed": "screening",
    "screening": "preregistered",
    "preregistered": "ready",
    "ready": "running",
    "running": "evaluating",
    "evaluating": "completed",
}
REQUIRED_APPROVAL_ACTIONS = {
    "begin_experiment",
    "model_or_agent_execution",
    "paid_execution",
    "external_project_write",
    "contact_external_user",
    "open_or_merge_pull_request",
    "candidate_promotion",
    "verified_library_change",
    "release_publication",
    "secret_creation_or_use",
}
EVENT_FIELDS = {
    "sequence",
    "event_type",
    "experiment_id",
    "previous_event_sha256",
    "previous_state",
    "new_state",
    "timestamp",
    "actor",
    "command",
    "evidence",
    "acceptance_test_results",
    "budget_status",
    "action",
    "event_sha256",
}
EXTENDED_EVENT_FIELDS = {
    "budget_before",
    "budget_after",
    "oracle_result",
    "actor_type",
    "artifact_sha256",
}
EXIT_OK = 0
EXIT_APPROVAL_REQUIRED = 10
EXIT_VALIDATION_FAILED = 11
EXIT_BUDGET_EXHAUSTED = 12
EXIT_LEASE_HELD = 13
EXIT_UNSAFE_WORKTREE = 14
EXIT_SCHEDULER_CONFIG = 15
CONTINUATION_COMMAND = "python3 autonomous-lab/scripts/lab.py run-one-step"
SCHEDULED_COMMAND = "python3 autonomous-lab/scripts/lab.py scheduled-step --persist-commit"
NO_ELIGIBLE_MESSAGE = "No scheduler-eligible experiment is currently approved."


class LabValidationError(Exception):
    """Raised when a control-plane invariant fails."""


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def canonical_hash(record: dict[str, Any]) -> str:
    unhashed = {key: value for key, value in record.items() if key != "event_sha256"}
    payload = json.dumps(unhashed, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_timestamp_after(value: str, minutes: int = 1) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed + timedelta(minutes=minutes)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class Lab:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        self.repo_root = self.root.parent
        self.schemas = {
            name: load_json(self.root / "schemas" / f"{name}.schema.json")
            for name in ("goal", "state", "scorecard", "escalation")
        }
        self.registry = load_yaml(self.root / "experiments" / "registry.yaml")

    def current_entry(self, experiment_id: str | None = None) -> dict[str, Any]:
        selected = experiment_id or self.registry.get("current_experiment_id")
        if selected is None:
            eligible = self.scheduler_entries()
            if not eligible:
                raise SchedulerConfigError(NO_ELIGIBLE_MESSAGE)
            selected = eligible[0]["experiment_id"]
        entries = [
            entry
            for entry in self.registry["experiments"]
            if entry.get("experiment_id") == selected
            and "goal_path" in entry
            and "state_path" in entry
        ]
        if len(entries) != 1:
            raise LabValidationError(f"expected exactly one matching controlled experiment, found {len(entries)}")
        return entries[0]

    def scheduler_entries(self) -> list[dict[str, Any]]:
        entries = [
            entry
            for entry in self.registry.get("experiments", [])
            if entry.get("scheduler_eligible") is True
            and entry.get("operational_status") == "active"
            and "goal_path" in entry
            and "state_path" in entry
        ]
        if len(entries) > 1:
            raise SchedulerConfigError(
                f"expected at most one scheduler-eligible experiment, found {len(entries)}"
            )
        return entries

    def scheduler_entry(self) -> dict[str, Any] | None:
        entries = self.scheduler_entries()
        return entries[0] if entries else None

    def resolve(self, repository_path: str) -> Path:
        path = (self.repo_root / repository_path).resolve()
        if self.repo_root not in path.parents:
            raise LabValidationError(f"path escapes repository: {repository_path}")
        return path

    def records(self, experiment_id: str | None = None) -> tuple[dict[str, Any], ...]:
        entry = self.current_entry(experiment_id)
        goal = load_yaml(self.resolve(entry["goal_path"]))
        state = load_json(self.resolve(entry["state_path"]))
        scorecard = load_json(self.resolve(entry["scorecard_path"]))
        escalation = load_json(self.resolve(entry["escalation_path"]))
        return entry, goal, state, scorecard, escalation

    def schema_validate(self, instance: Any, schema_name: str, label: str) -> None:
        validator = Draft202012Validator(
            self.schemas[schema_name], format_checker=FormatChecker()
        )
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            detail = "; ".join(
                f"{label}:{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
                for error in errors
            )
            raise LabValidationError(detail)

    @staticmethod
    def gate_satisfied(goal: dict[str, Any], state: dict[str, Any], gate: str) -> bool:
        requirement = goal["approval_gates"].get(gate)
        recorded = state["approvals"].get(gate)
        return requirement == "not_required" and recorded == "not_required" or recorded == "approved"

    def read_ledger(self) -> list[dict[str, Any]]:
        events_path = self.root / "ledger" / "events.jsonl"
        events: list[dict[str, Any]] = []
        for line_number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise LabValidationError(f"ledger line {line_number}: {error}") from error
        if not events:
            raise LabValidationError("ledger must contain at least one event")
        return events

    def validate_ledger(self, goal: dict[str, Any], state: dict[str, Any]) -> None:
        previous_hash: str | None = None
        experiment_states: dict[str, str] = {}
        experiment_history: dict[str, list[str]] = {}
        matching: list[dict[str, Any]] = []
        for index, event in enumerate(self.read_ledger(), 1):
            fields = set(event)
            if not EVENT_FIELDS.issubset(fields) or fields - EVENT_FIELDS - EXTENDED_EVENT_FIELDS:
                missing = sorted(EVENT_FIELDS - set(event))
                extra = sorted(set(event) - EVENT_FIELDS - EXTENDED_EVENT_FIELDS)
                raise LabValidationError(f"ledger event {index} fields invalid; missing={missing}, extra={extra}")
            if event["event_type"] == "state_transition" and not EXTENDED_EVENT_FIELDS.issubset(fields):
                raise LabValidationError(f"ledger event {index} omits extended transition evidence")
            if event["sequence"] != index:
                raise LabValidationError(f"ledger sequence {event['sequence']} should be {index}")
            if event["previous_event_sha256"] != previous_hash:
                raise LabValidationError(f"ledger event {index} breaks previous hash chain")
            if event["event_sha256"] != canonical_hash(event):
                raise LabValidationError(f"ledger event {index} content hash mismatch (possible overwrite)")
            experiment_id = event["experiment_id"]
            previous_state = experiment_states.get(experiment_id, "none")
            if event["previous_state"] != previous_state:
                raise LabValidationError(f"ledger event {index} does not name the actual previous state")
            if previous_state in TERMINAL_STATES:
                raise LabValidationError(f"ledger continues experiment {experiment_id} after a terminal state")
            if event["new_state"] not in TRANSITIONS.get(previous_state, set()):
                raise LabValidationError(
                    f"invalid or skipped transition {previous_state} -> {event['new_state']}"
                )
            if not event["evidence"]:
                raise LabValidationError(f"ledger event {index} has no evidence")
            if event["new_state"] == "running":
                prior_states = set(experiment_history.get(experiment_id, []))
                if not {"preregistered", "ready"}.issubset(prior_states):
                    raise LabValidationError("execution attempted before preregistration and readiness")
            if event["new_state"] == "evaluating" and not goal.get("objective_oracle"):
                if experiment_id == goal["experiment_id"]:
                    raise LabValidationError("evaluation attempted without an objective oracle")
            if experiment_id == goal["experiment_id"]:
                matching.append(event)
            previous_hash = event["event_sha256"]
            experiment_states[experiment_id] = event["new_state"]
            experiment_history.setdefault(experiment_id, []).append(event["new_state"])

        if len(matching) != state["ledger_event_count"]:
            raise LabValidationError("state ledger event count does not match the append-only ledger")
        if not matching or matching[-1]["event_sha256"] != state["ledger_head_sha256"]:
            raise LabValidationError("state ledger head does not match the append-only ledger")
        if matching[-1]["new_state"] != state["state"]:
            raise LabValidationError("state does not match the ledger's final transition")

    def validate_append_only(self, previous_ledger_text: str) -> None:
        """Require every previously committed ledger line to remain byte-identical."""
        previous = previous_ledger_text.splitlines()
        current = (self.root / "ledger" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if len(current) < len(previous) or current[: len(previous)] != previous:
            raise LabValidationError("append-only ledger history was removed or overwritten")

    def validate_git_history(self, base_ref: str) -> None:
        relative = self.root.relative_to(self.repo_root) / "ledger" / "events.jsonl"
        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if commit.returncode != 0:
            raise LabValidationError(f"append-only base ref is not a commit: {base_ref}")
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{base_ref}:{relative.as_posix()}"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if exists.returncode != 0:
            return
        result = subprocess.run(
            ["git", "show", f"{base_ref}:{relative.as_posix()}"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise LabValidationError(f"could not read prior ledger from {base_ref}")
        self.validate_append_only(result.stdout)
        for entry in self.registry.get("experiments", []):
            approval_path = entry.get("approval_record_path")
            if not approval_path:
                continue
            exists = subprocess.run(
                ["git", "cat-file", "-e", f"{base_ref}:{approval_path}"],
                cwd=self.repo_root, capture_output=True, check=False,
            )
            if exists.returncode != 0:
                continue
            previous = subprocess.run(
                ["git", "show", f"{base_ref}:{approval_path}"],
                cwd=self.repo_root, text=True, capture_output=True, check=True,
            ).stdout.splitlines()
            current = self.resolve(approval_path).read_text(encoding="utf-8").splitlines()
            if len(current) < len(previous) or current[:len(previous)] != previous:
                raise LabValidationError("append-only approval history was removed or overwritten")

    def validate_semantics(
        self,
        entry: dict[str, Any],
        goal: dict[str, Any],
        state: dict[str, Any],
        scorecard: dict[str, Any],
        escalation: dict[str, Any],
    ) -> None:
        experiment_id = goal["experiment_id"]
        for label, record in (("registry", entry), ("state", state), ("scorecard", scorecard), ("escalation", escalation)):
            if record["experiment_id"] != experiment_id:
                raise LabValidationError(f"{label} experiment_id does not match goal")
        if entry["state"] != state["state"]:
            raise LabValidationError("registry and state disagree")
        missing_gates = REQUIRED_APPROVAL_ACTIONS - set(goal["approval_gates"])
        if missing_gates:
            raise LabValidationError(f"required approval gates absent: {sorted(missing_gates)}")
        for gate, requirement in goal["approval_gates"].items():
            if gate not in state["approvals"]:
                raise LabValidationError(f"state omits approval gate {gate}")
            if requirement == "required" and state["approvals"][gate] == "not_required":
                raise LabValidationError(f"required gate {gate} cannot be marked not_required")
        overlap = set(goal["allowed_actions"]) & set(goal["forbidden_actions"])
        if overlap:
            raise LabValidationError(f"actions are both allowed and forbidden: {sorted(overlap)}")
        for key, used_key in (
            ("max_iterations", "iterations"),
            ("max_commands", "commands"),
            ("max_tests", "tests"),
            ("max_model_calls", "model_calls"),
            ("max_tokens", "tokens"),
            ("max_model_cost_usd", "cost_usd"),
        ):
            if state["budget_used"][used_key] > goal["budgets"][key]:
                raise LabValidationError(f"{used_key} budget is exhausted")
        if state["budget_used"]["wall_minutes"] > goal["budgets"]["max_wall_clock_hours"] * 60:
            raise LabValidationError("wall-clock budget is exhausted")
        if state["retry_count"] > goal["budgets"]["max_same_failure_repeats"]:
            raise LabValidationError("retry budget is exhausted")
        verified_library = self.repo_root / "experiences" / "verified.json"
        actual_library_hash = hashlib.sha256(verified_library.read_bytes()).hexdigest()
        if state["verified_library_sha256"] != actual_library_hash:
            raise LabValidationError("experiences/verified.json differs from the recorded immutable baseline")
        if state["state"] in TERMINAL_STATES and state["blocker"] is None and state["state"] != "completed":
            raise LabValidationError("interrupt terminal state must explain its blocker")
        if escalation["status"] == "open" and not state["blocker"]:
            raise LabValidationError("open escalation is not visible as a state blocker")
        if state["state"] == "proposed" and scorecard["status"] != "not_started":
            raise LabValidationError("proposed experiment cannot have evaluated scorecard evidence")
        progressed_states = {"screening", "preregistered", "ready", "running", "evaluating", "completed"}
        if state["state"] in progressed_states and not self.gate_satisfied(goal, state, "begin_experiment"):
            raise LabValidationError("experiment progressed without begin_experiment approval")
        execution_states = {"running", "evaluating", "completed"}
        if state["state"] in execution_states and not self.gate_satisfied(goal, state, "model_or_agent_execution"):
            raise LabValidationError("execution progressed without model_or_agent_execution approval")

    def validate_registry(self) -> None:
        if self.registry.get("schema_version") != 2:
            raise LabValidationError("registry schema_version must be 2")
        entries = self.registry.get("experiments")
        if not isinstance(entries, list) or not entries:
            raise LabValidationError("registry experiments must be a non-empty list")
        ids: set[str] = set()
        for entry in entries:
            experiment_id = entry.get("experiment_id")
            if not experiment_id or experiment_id in ids:
                raise LabValidationError("registry experiment IDs must be unique and non-empty")
            ids.add(experiment_id)
            if entry.get("state") not in ALL_STATES:
                raise LabValidationError(f"registry state invalid for {experiment_id}")
            if entry.get("experiment_kind") not in {"production", "commercial", "shakedown", "regression_fixture"}:
                raise LabValidationError(f"registry experiment_kind invalid for {experiment_id}")
            if entry.get("operational_status") not in {"active", "proposed", "archived", "disabled"}:
                raise LabValidationError(f"registry operational_status invalid for {experiment_id}")
            if not isinstance(entry.get("scheduler_eligible"), bool):
                raise LabValidationError(f"registry scheduler_eligible must be boolean for {experiment_id}")
            if entry["scheduler_eligible"] and entry["operational_status"] != "active":
                raise LabValidationError(f"scheduler-eligible experiment is not active: {experiment_id}")
            if entry["scheduler_eligible"] and "goal_path" not in entry:
                raise LabValidationError(f"scheduler-eligible experiment is not controlled: {experiment_id}")
            for key in ("evidence_path", "goal_path", "state_path", "scorecard_path", "escalation_path", "request_path", "input_path", "artifact_schema_path"):
                if key in entry and not self.resolve(entry[key]).is_file():
                    raise LabValidationError(f"registry path does not exist: {entry[key]}")
        current_id = self.registry.get("current_experiment_id")
        if current_id is not None and current_id not in ids:
            raise LabValidationError("registry current_experiment_id is absent from experiments")
        if current_id is not None:
            self.current_entry(current_id)
        self.scheduler_entries()

    def validate_templates(self) -> None:
        self.schema_validate(load_yaml(self.root / "templates" / "goal.yaml"), "goal", "goal template")
        self.schema_validate(load_json(self.root / "templates" / "state.json"), "state", "state template")
        self.schema_validate(load_json(self.root / "templates" / "scorecard.json"), "scorecard", "scorecard template")
        run_record = load_json(self.root / "templates" / "run-record.json")
        required = {"schema_version", "experiment_id", "run_id", "baseline_or_treatment", "budget_used", "external_writes"}
        if not required.issubset(run_record):
            raise LabValidationError("run-record template omits required fields")

    def validate(self, base_ref: str | None = None) -> dict[str, Any]:
        load_config(self.root)
        for name, schema in self.schemas.items():
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as error:
                raise LabValidationError(f"{name} schema is invalid: {error}") from error
        self.validate_registry()
        self.validate_templates()
        controlled = [entry for entry in self.registry["experiments"] if "goal_path" in entry]
        for entry in controlled:
            goal = load_yaml(self.resolve(entry["goal_path"]))
            state = load_json(self.resolve(entry["state_path"]))
            scorecard = load_json(self.resolve(entry["scorecard_path"]))
            escalation = load_json(self.resolve(entry["escalation_path"]))
            label = entry["experiment_id"]
            self.schema_validate(goal, "goal", f"{label} goal")
            self.schema_validate(state, "state", f"{label} state")
            self.schema_validate(scorecard, "scorecard", f"{label} scorecard")
            self.schema_validate(escalation, "escalation", f"{label} escalation")
            self.validate_semantics(entry, goal, state, scorecard, escalation)
            self.validate_ledger(goal, state)
            if entry.get("runner_kind") == "phase0-preparation":
                try:
                    validate_package(self.repo_root, entry, state)
                except Phase0ValidationError as error:
                    raise LabValidationError(str(error)) from error
        if base_ref:
            self.validate_git_history(base_ref)
        selected = self.scheduler_entry()
        return {
            "schemas": len(self.schemas),
            "registry_experiments": len(self.registry["experiments"]),
            "controlled_experiments": len(controlled),
            "current_experiment": selected["experiment_id"] if selected else None,
            "state": load_json(self.resolve(selected["state_path"]))["state"] if selected else None,
            "scheduler_eligible_experiments": 1 if selected else 0,
            "ledger_events": len(self.read_ledger()),
            "result": "valid",
        }

    def budget_exhaustion(self, goal: dict[str, Any], state: dict[str, Any]) -> str | None:
        checks = (
            ("iterations", "max_iterations"),
            ("commands", "max_commands"),
            ("tests", "max_tests"),
            ("model_calls", "max_model_calls"),
            ("tokens", "max_tokens"),
            ("cost_usd", "max_model_cost_usd"),
        )
        for used, maximum in checks:
            limit = goal["budgets"][maximum]
            if limit > 0 and state["budget_used"][used] >= limit:
                return used
        wall_limit = goal["budgets"]["max_wall_clock_hours"] * 60
        if state["budget_used"]["wall_minutes"] >= wall_limit:
            return "wall_minutes"
        if state["retry_count"] >= goal["budgets"]["max_same_failure_repeats"]:
            return "retries"
        return None

    def approval_decision(self, action: str, experiment_id: str | None = None) -> dict[str, Any]:
        """Return a fail-closed decision for sensitive product/external actions."""
        _, goal, state, _, _ = self.records(experiment_id)
        action_to_gate = {
            "external_write": "external_project_write",
            "promotion": "candidate_promotion",
            "verified_library_change": "verified_library_change",
            "release": "release_publication",
            "paid_execution": "paid_execution",
            "model_execution": "model_or_agent_execution",
        }
        gate = action_to_gate.get(action)
        if gate is None:
            return {"kind": "escalate", "reason": "unrecognized action is not authorized"}
        if goal["approval_gates"].get(gate) != "required":
            return {"kind": "deny", "reason": f"goal does not define required gate {gate}"}
        if state["approvals"].get(gate) != "approved":
            return {"kind": "escalate", "reason": f"{gate} approval is required"}
        return {"kind": "permitted", "reason": f"{gate} approval is recorded"}

    def next_action(self, experiment_id: str | None = None) -> dict[str, Any]:
        if experiment_id is None and self.registry.get("current_experiment_id") is None and self.scheduler_entry() is None:
            return {"kind": "no_work", "reason": NO_ELIGIBLE_MESSAGE, "transition": None}
        entry, goal, state, _, escalation = self.records(experiment_id)
        current = state["state"]
        if current in TERMINAL_STATES:
            if escalation["status"] == "open":
                return {
                    "kind": "human_approval",
                    "reason": escalation["summary"],
                    "transition": None,
                    "escalation_id": escalation["escalation_id"],
                }
            return {"kind": "stop", "reason": f"{current} is terminal", "transition": None}
        exhausted = self.budget_exhaustion(goal, state)
        if exhausted:
            transition = "escalated" if exhausted == "retries" else "budget_exhausted"
            return {"kind": "escalate", "reason": f"{exhausted} budget reached", "transition": transition, "budget": exhausted}
        if escalation["status"] == "open":
            return {
                "kind": "human_approval",
                "reason": escalation["summary"],
                "transition": None,
                "escalation_id": escalation["escalation_id"],
            }
        if entry.get("runner_kind") == "external-action-escalation" and current == "screening":
            return {
                "kind": "external_action",
                "reason": "the fixture requests an approval-gated external write",
                "transition": "escalated",
                "requested_action": entry.get("requested_action", "external_write"),
            }
        transition = NEXT_STAGE.get(current)
        if not transition:
            return {"kind": "human_review", "reason": "evaluation decision required", "transition": None}
        required_gate = "begin_experiment" if current == "proposed" else None
        if transition == "running":
            required_gate = "model_or_agent_execution"
        if required_gate and not self.gate_satisfied(goal, state, required_gate):
            return {"kind": "human_approval", "reason": f"{required_gate} approval is not recorded", "transition": None}
        return {"kind": "transition", "reason": "next lifecycle evidence may be recorded", "transition": transition}

    def status(self, experiment_id: str | None = None) -> dict[str, Any]:
        if experiment_id is None and self.registry.get("current_experiment_id") is None and self.scheduler_entry() is None:
            return {
                "experiment_id": None,
                "experiment_kind": None,
                "state": None,
                "next_action": self.next_action(),
                "scheduler_useful": False,
                "human_approval_required": False,
                "continuation_command": SCHEDULED_COMMAND,
            }
        entry, goal, state, scorecard, escalation = self.records(experiment_id)
        next_action = self.next_action(experiment_id)
        return {
            "experiment_id": goal["experiment_id"],
            "experiment_kind": entry["experiment_kind"],
            "registry_state": entry["state"],
            "state": state["state"],
            "milestone": state["milestone"],
            "blocker": state["blocker"],
            "budget_used": state["budget_used"],
            "scorecard_status": scorecard["status"],
            "ledger_event_count": state["ledger_event_count"],
            "ledger_head_sha256": state["ledger_head_sha256"],
            "open_escalation": escalation["escalation_id"] if escalation["status"] == "open" else None,
            "next_action": next_action,
            "continuation_command": CONTINUATION_COMMAND,
        }

    def _event_for_transition(
        self,
        goal: dict[str, Any],
        state: dict[str, Any],
        new_state: str,
        evidence: list[str],
        timestamp: str,
        actor: str,
        command: str,
        acceptance_results: list[dict[str, Any]] | None = None,
        budget_before: dict[str, Any] | None = None,
        budget_after: dict[str, Any] | None = None,
        oracle_result: dict[str, Any] | None = None,
        artifact_sha256: str | None = None,
        actor_type: str = "deterministic_local_controller",
    ) -> dict[str, Any]:
        if new_state not in TRANSITIONS.get(state["state"], set()):
            raise LabValidationError(f"transition {state['state']} -> {new_state} is not allowed")
        if state["state"] in TERMINAL_STATES:
            raise LabValidationError("cannot continue after a terminal state")
        if not evidence:
            raise LabValidationError("a transition requires evidence")
        if state["state"] == "proposed" and new_state == "screening":
            if not self.gate_satisfied(goal, state, "begin_experiment"):
                raise LabValidationError("screening requires begin_experiment approval")
        if new_state == "running" and not self.gate_satisfied(goal, state, "model_or_agent_execution"):
            raise LabValidationError("execution requires model_or_agent_execution approval")
        if new_state == "evaluating" and not goal.get("objective_oracle"):
            raise LabValidationError("evaluation requires an objective oracle")
        event = {
            "sequence": len(self.read_ledger()) + 1,
            "event_type": "state_transition",
            "experiment_id": goal["experiment_id"],
            "previous_event_sha256": self.read_ledger()[-1]["event_sha256"],
            "previous_state": state["state"],
            "new_state": new_state,
            "timestamp": timestamp,
            "actor": actor,
            "command": command,
            "evidence": evidence,
            "acceptance_test_results": acceptance_results or [],
            "budget_status": copy.deepcopy(state["budget_used"]),
            "budget_before": copy.deepcopy(budget_before or state["budget_used"]),
            "budget_after": copy.deepcopy(budget_after or state["budget_used"]),
            "oracle_result": oracle_result or {"passed": True, "summary": "transition evidence recorded"},
            "actor_type": actor_type,
            "artifact_sha256": artifact_sha256,
            "action": f"Recorded one transition to {new_state}.",
        }
        event["event_sha256"] = canonical_hash(event)
        return event

    def perform_transition(
        self,
        new_state: str,
        evidence: list[str],
        timestamp: str,
        actor: str = "lab-controller",
        command: str = "run-one-step",
        acceptance_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        entry, goal, state, _, _ = self.records()
        action = self.next_action()
        if action["kind"] != "transition" or action["transition"] != new_state:
            raise LabValidationError(f"controller refuses transition: {action['reason']}")
        event = self._event_for_transition(
            goal, state, new_state, evidence, timestamp, actor, command, acceptance_results
        )
        self._persist_event(entry, state, event)
        return event

    def _persist_event(
        self,
        entry: dict[str, Any],
        state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        """Append one event and make the state/registry pointers match its head."""
        ledger_path = self.root / "ledger" / "events.jsonl"
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        state["state"] = event["new_state"]
        state["milestone"] = f"entered {event['new_state']}"
        state["blocker"] = None
        state["updated_at"] = event["timestamp"]
        state["ledger_event_count"] += 1
        state["ledger_head_sha256"] = event["event_sha256"]
        state_path = self.resolve(entry["state_path"])
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        entry["state"] = event["new_state"]
        (self.root / "experiments" / "registry.yaml").write_text(
            yaml.safe_dump(self.registry, sort_keys=False), encoding="utf-8"
        )

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _repository_relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo_root).as_posix()

    @staticmethod
    def _increment_budget(state: dict[str, Any], **increments: int | float) -> None:
        for key, amount in increments.items():
            state["budget_used"][key] += amount

    @staticmethod
    def _normalize_records(source: dict[str, Any]) -> dict[str, Any]:
        normalized = []
        for record in source.get("records", []):
            raw_enabled = record.get("enabled")
            enabled = raw_enabled if isinstance(raw_enabled, bool) else str(raw_enabled).lower() in {"1", "true", "yes"}
            normalized.append(
                {
                    "id": str(record["id"]).strip().lower(),
                    "enabled": enabled,
                    "tags": sorted({str(tag).strip().lower() for tag in record.get("tags", [])}),
                }
            )
        return {"schema_version": 1, "records": sorted(normalized, key=lambda item: item["id"])}

    def _run_normalization_step(
        self,
        entry: dict[str, Any],
        goal: dict[str, Any],
        state: dict[str, Any],
        scorecard: dict[str, Any],
        transition: str,
        timestamp: str,
    ) -> dict[str, Any]:
        experiment_dir = self.resolve(entry["state_path"]).parent
        input_path = self.resolve(entry["input_path"])
        schema_path = self.resolve(entry["artifact_schema_path"])
        artifact_path = experiment_dir / "normalized-artifact.json"
        schema = load_json(schema_path)
        source = load_json(input_path)
        budget_before = copy.deepcopy(state["budget_used"])
        evidence: list[str] = []
        acceptance: list[dict[str, Any]] = []
        artifact_hash: str | None = sha256_file(artifact_path) if artifact_path.exists() else None
        oracle = {"passed": True, "summary": "lifecycle evidence recorded"}

        if transition == "screening":
            errors = list(Draft202012Validator(schema).iter_errors(source))
            evidence_path = experiment_dir / "screening-result.json"
            result = {
                "schema_version": 1,
                "experiment_id": goal["experiment_id"],
                "timestamp": timestamp,
                "input_sha256": sha256_file(input_path),
                "objective_precondition": "input fixture is invalid under normalized-artifact.schema.json",
                "precondition_valid": not errors,
                "observed_error_count": len(errors),
                "passed": bool(errors),
                "network_access": False,
                "model_calls": 0,
                "external_writes": 0,
            }
            self._write_json(evidence_path, result)
            self._increment_budget(state, commands=1, tests=1)
            evidence = [self._repository_relative(evidence_path), entry["input_path"], entry["artifact_schema_path"]]
            acceptance = [{"test_id": "invalid-precondition", "passed": bool(errors), "evidence": self._repository_relative(evidence_path)}]
            oracle = {"passed": bool(errors), "summary": f"normalized schema rejected the fixture with {len(errors)} errors"}
            artifact_hash = sha256_file(input_path)
        elif transition == "preregistered":
            evidence_path = experiment_dir / "preregistration.json"
            result = {
                "schema_version": 1,
                "experiment_id": goal["experiment_id"],
                "timestamp": timestamp,
                "goal_sha256": sha256_file(self.resolve(entry["goal_path"])),
                "input_sha256": sha256_file(input_path),
                "schema_sha256": sha256_file(schema_path),
                "oracle": goal["objective_oracle"],
                "transformation": "trim and lowercase IDs; coerce booleans; lowercase, deduplicate, and sort tags; sort records by ID",
                "frozen_before_execution": True,
            }
            self._write_json(evidence_path, result)
            self._increment_budget(state, commands=1)
            evidence = [self._repository_relative(evidence_path)]
            acceptance = [{"test_id": "preregistration-frozen", "passed": True, "evidence": self._repository_relative(evidence_path)}]
            oracle = {"passed": True, "summary": "goal, input, schema, oracle, and transformation hashes were frozen"}
            artifact_hash = sha256_file(input_path)
        elif transition == "ready":
            preregistration = experiment_dir / "preregistration.json"
            ready = preregistration.exists() and load_json(preregistration).get("frozen_before_execution") is True
            evidence_path = experiment_dir / "readiness-result.json"
            result = {
                "schema_version": 1,
                "experiment_id": goal["experiment_id"],
                "timestamp": timestamp,
                "preregistration_present": preregistration.exists(),
                "input_hash_matches": preregistration.exists() and load_json(preregistration)["input_sha256"] == sha256_file(input_path),
                "schema_hash_matches": preregistration.exists() and load_json(preregistration)["schema_sha256"] == sha256_file(schema_path),
                "passed": ready,
            }
            result["passed"] = all((result["preregistration_present"], result["input_hash_matches"], result["schema_hash_matches"]))
            self._write_json(evidence_path, result)
            self._increment_budget(state, commands=1, tests=1)
            evidence = [self._repository_relative(evidence_path), self._repository_relative(preregistration)]
            acceptance = [{"test_id": "ready-to-run", "passed": result["passed"], "evidence": self._repository_relative(evidence_path)}]
            oracle = {"passed": result["passed"], "summary": "preregistered input and schema hashes match current repository files"}
            artifact_hash = sha256_file(input_path)
        elif transition == "running":
            normalized = self._normalize_records(source)
            self._write_json(artifact_path, normalized)
            artifact_hash = sha256_file(artifact_path)
            run_path = experiment_dir / "run-record.json"
            run_record = {
                "schema_version": 1,
                "experiment_id": goal["experiment_id"],
                "run_id": "repository-state-recovery-01-run-01",
                "started_at": timestamp,
                "finished_at": timestamp,
                "baseline_or_treatment": "deterministic-local-fixture",
                "commands": [CONTINUATION_COMMAND],
                "acceptance_results": [],
                "budget_used": {},
                "external_writes": False,
                "model_calls": 0,
                "paid_cost_usd": 0,
                "input_sha256": sha256_file(input_path),
                "artifact_sha256": artifact_hash,
                "notes": "Deterministic orchestration fixture; not AEG effectiveness evidence.",
            }
            self._increment_budget(state, iterations=1, commands=1)
            run_record["budget_used"] = copy.deepcopy(state["budget_used"])
            self._write_json(run_path, run_record)
            evidence = [self._repository_relative(run_path), self._repository_relative(artifact_path)]
            acceptance = [{"test_id": "artifact-produced", "passed": artifact_path.is_file(), "evidence": self._repository_relative(artifact_path)}]
            oracle = {"passed": artifact_path.is_file(), "summary": "normalized artifact was produced locally"}
        elif transition == "evaluating":
            normalized = load_json(artifact_path)
            errors = list(Draft202012Validator(schema).iter_errors(normalized))
            expected = self._normalize_records(source)
            passed = not errors and normalized == expected
            results_path = experiment_dir / "acceptance-results.json"
            results = [
                {"test_id": "normalized-schema", "passed": not errors, "evidence": self._repository_relative(artifact_path)},
                {"test_id": "deterministic-normalization", "passed": normalized == expected, "evidence": self._repository_relative(results_path)},
            ]
            self._write_json(
                results_path,
                {
                    "schema_version": 1,
                    "experiment_id": goal["experiment_id"],
                    "timestamp": timestamp,
                    "passed": passed,
                    "schema_error_count": len(errors),
                    "artifact_sha256": sha256_file(artifact_path),
                    "results": results,
                },
            )
            artifact_hash = sha256_file(artifact_path)
            self._increment_budget(state, commands=1, tests=2)
            scorecard["status"] = "incomplete"
            scorecard["comparison_pairs"] = 1
            scorecard["acceptance_results"] = results
            scorecard["metrics"].update({"precondition_failed_as_expected": 1, "postcondition_passed": int(passed), "model_calls": 0, "cost_usd": 0})
            scorecard["decision"] = "continue" if passed else "stop"
            self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
            evidence = [self._repository_relative(results_path), entry["scorecard_path"]]
            acceptance = results
            oracle = {"passed": passed, "summary": "artifact matches the schema and deterministic expected normalization"}
        elif transition == "completed":
            results_path = experiment_dir / "acceptance-results.json"
            results_record = load_json(results_path)
            if not results_record.get("passed"):
                raise LabValidationError("completion refused because the objective oracle did not pass")
            artifact_hash = sha256_file(artifact_path)
            scorecard["status"] = "evaluated"
            scorecard["decision"] = "complete"
            scorecard["limitations"] = [
                "This validates orchestration and repository-state reconstruction only.",
                "It is not evidence of AEG retrieval benefit, coding-agent intelligence, commercial demand, generalized effectiveness, or PMF.",
            ]
            self._increment_budget(state, commands=1, tests=1)
            self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
            evidence = [self._repository_relative(results_path), entry["scorecard_path"], self._repository_relative(artifact_path)]
            acceptance = results_record["results"]
            oracle = {"passed": True, "summary": "all preregistered deterministic acceptance checks passed"}
        else:
            raise LabValidationError(f"normalization runner does not implement transition {transition}")

        if not oracle["passed"]:
            raise LabValidationError(f"objective evidence failed for transition {transition}: {oracle['summary']}")
        budget_after = copy.deepcopy(state["budget_used"])
        exhausted = self.budget_exhaustion(goal, state)
        if exhausted:
            raise LabValidationError(f"{exhausted} budget reached while preparing transition")
        event = self._event_for_transition(
            goal,
            state,
            transition,
            evidence,
            timestamp,
            "lab.py",
            CONTINUATION_COMMAND,
            acceptance,
            budget_before,
            budget_after,
            oracle,
            artifact_hash,
        )
        self._persist_event(entry, state, event)
        return event

    def _run_phase0_step(
        self,
        entry: dict[str, Any],
        goal: dict[str, Any],
        state: dict[str, Any],
        scorecard: dict[str, Any],
        escalation: dict[str, Any],
        transition: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """Validate the bounded package and record exactly one Phase 0 transition."""
        budget_before = copy.deepcopy(state["budget_used"])
        state["phase_run_count"] += 1
        self._increment_budget(state, iterations=1, commands=1, tests=1, model_calls=1)
        if state["phase_run_count"] > 8:
            raise LabValidationError("Phase 0 scheduled/model-assisted run limit reached")
        try:
            validation = validate_package(self.repo_root, entry, state)
        except Phase0ValidationError as error:
            raise LabValidationError(str(error)) from error
        validation.update({"validated_at": timestamp, "transition": transition})
        validation_path = self.resolve(entry["runtime_evidence_paths"][0])
        self._write_json(validation_path, validation)
        artifact_digest = hashlib.sha256()
        for path in entry["phase0_artifact_paths"]:
            artifact_digest.update(path.encode())
            artifact_digest.update(self.resolve(path).read_bytes())
        artifact_hash = artifact_digest.hexdigest()
        acceptance = [
            {"test_id": "phase0-artifact-package", "passed": True, "evidence": self._repository_relative(validation_path)},
            {"test_id": "phase0-boundary-oracle", "passed": True, "evidence": self._repository_relative(validation_path)},
        ]
        evidence = [self._repository_relative(validation_path), entry["approval_record_path"]]

        if transition == "ready":
            state["milestone"] = "Phase 0 package passed deterministic readiness validation"
        elif transition == "running":
            state["milestone"] = "Phase 0 repository-local package validation running"
        elif transition == "evaluating":
            state["milestone"] = "Phase 0 package passed its preregistered deterministic oracle"
            scorecard["acceptance_results"] = acceptance
            scorecard["metrics"]["phase0_artifacts_complete"] = 1
            scorecard["metrics"]["model_calls"] = state["budget_used"]["model_calls"]
            scorecard["decision"] = "continue"
            self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
        elif transition == "completed":
            phase_scorecard_path = self.resolve(entry["runtime_evidence_paths"][1])
            phase_scorecard = load_json(phase_scorecard_path)
            phase_scorecard.update(
                {
                    "status": "completed",
                    "artifact_checks_passed": True,
                    "internal_links_resolve": True,
                    "claims_match_batch_evidence": True,
                    "unsupported_claims_absent": True,
                    "private_or_proprietary_information_absent": True,
                    "sample_is_sanitized_and_reproducible": True,
                    "pricing_labeled_hypothesis": True,
                    "outreach_is_draft_only": True,
                    "scheduled_or_model_assisted_runs": state["phase_run_count"],
                    "model_calls": state["budget_used"]["model_calls"],
                    "decision": "Phase 0 complete; human approval required for any Phase 1 recruitment",
                }
            )
            self._write_json(phase_scorecard_path, phase_scorecard)
            scorecard["status"] = "evaluated"
            scorecard["acceptance_results"] = acceptance
            scorecard["metrics"]["phase0_artifacts_complete"] = 1
            scorecard["metrics"]["model_calls"] = state["budget_used"]["model_calls"]
            scorecard["decision"] = "complete"
            self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
            escalation.update(
                {
                    "escalation_id": "failure-recovery-v0-phase1-recruitment",
                    "created_at": timestamp,
                    "status": "open",
                    "reason_code": "approval_required",
                    "summary": "Phase 0 is complete; Phase 1 recruitment and every external action remain blocked.",
                    "evidence": [self._repository_relative(validation_path), self._repository_relative(phase_scorecard_path)],
                    "requested_decision": "whether to begin Phase 1 seed-user recruitment",
                    "allowed_resolutions": ["keep the service repository-local and stopped", "authorize a separately preregistered Phase 1 recruitment plan"],
                    "tradeoffs": ["Stopping preserves the zero-external-action boundary.", "Recruitment could test demand but requires new privacy, outreach, budget, and external-action approval."],
                    "recommended_choice": "Review Phase 0 evidence before deciding whether to authorize a separate Phase 1 plan.",
                    "resolved_at": None,
                    "resolution": None,
                }
            )
            self._write_json(self.resolve(entry["escalation_path"]), escalation)
            entry["scheduler_eligible"] = False
            entry["operational_status"] = "disabled"
            entry["conclusion"] = "Phase 0 package preparation completed with zero external actions; Phase 1 seed-user recruitment requires a separate human approval."
        else:
            raise LabValidationError(f"Phase 0 runner does not implement transition {transition}")

        budget_after = copy.deepcopy(state["budget_used"])
        event = self._event_for_transition(
            goal, state, transition, evidence, timestamp, "lab.py", SCHEDULED_COMMAND,
            acceptance, budget_before, budget_after,
            {"passed": True, "summary": "repository-local Phase 0 package validation passed"},
            artifact_hash, actor_type="bounded_phase0_controller",
        )
        self._persist_event(entry, state, event)
        if transition == "completed":
            state["milestone"] = "Phase 0 completed; awaiting a human decision on Phase 1 seed-user recruitment"
            state["blocker"] = "Phase 1 recruitment is not approved"
            self._write_json(self.resolve(entry["state_path"]), state)
        return event

    def _run_external_escalation_step(
        self,
        entry: dict[str, Any],
        goal: dict[str, Any],
        state: dict[str, Any],
        scorecard: dict[str, Any],
        escalation: dict[str, Any],
        action: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        experiment_dir = self.resolve(entry["state_path"]).parent
        budget_before = copy.deepcopy(state["budget_used"])
        if state["state"] == "proposed":
            request_path = self.resolve(entry["request_path"])
            evidence_path = experiment_dir / "screening-result.json"
            result = {
                "schema_version": 1,
                "experiment_id": goal["experiment_id"],
                "timestamp": timestamp,
                "request_sha256": sha256_file(request_path),
                "requested_action": entry["requested_action"],
                "network_access": False,
                "external_writes": 0,
                "passed": True,
            }
            self._write_json(evidence_path, result)
            self._increment_budget(state, commands=1, tests=1)
            event = self._event_for_transition(
                goal,
                state,
                "screening",
                [self._repository_relative(evidence_path), entry["request_path"]],
                timestamp,
                "lab.py",
                CONTINUATION_COMMAND,
                [{"test_id": "external-request-detected", "passed": True, "evidence": self._repository_relative(evidence_path)}],
                budget_before,
                copy.deepcopy(state["budget_used"]),
                {"passed": True, "summary": "external-action request was detected without performing it"},
                sha256_file(request_path),
            )
            self._persist_event(entry, state, event)
            return event
        if action["kind"] != "external_action":
            raise LabValidationError(f"external escalation runner cannot handle {action['kind']}")
        decision = self.approval_decision(action["requested_action"], goal["experiment_id"])
        if decision["kind"] != "escalate":
            raise LabValidationError("external fixture unexpectedly received action authority")
        request_path = self.resolve(entry["request_path"])
        self._increment_budget(state, commands=1)
        escalation.update(
            {
                "created_at": timestamp,
                "status": "open",
                "reason_code": "external_write",
                "summary": "The fixture requested an external write, but no external-action approval is recorded.",
                "evidence": [entry["request_path"], f"request_sha256={sha256_file(request_path)}", "state.approvals.external_project_write=pending"],
                "requested_decision": "Approve or reject the requested external write; no action will occur in this shakedown.",
                "allowed_resolutions": ["reject external write", "approve in a separately authorized future task"],
                "tradeoffs": [
                    "Rejecting preserves zero external writes and completes the safety demonstration.",
                    "Approving later would expand authority and require a separate scoped task; it is unnecessary for this orchestration test.",
                ],
                "recommended_choice": "Reject the external write because the safety behavior is already demonstrated locally.",
                "resolved_at": None,
                "resolution": None,
            }
        )
        self._write_json(self.resolve(entry["escalation_path"]), escalation)
        scorecard.update(
            {
                "status": "evaluated",
                "comparison_pairs": 1,
                "acceptance_results": [
                    {"test_id": "external-write-refused", "passed": True, "evidence": entry["escalation_path"]}
                ],
                "metrics": {"external_requests_detected": 1, "external_writes": 0, "model_calls": 0, "cost_usd": 0},
                "decision": "escalate",
                "limitations": ["Safety orchestration fixture only; no AEG effectiveness or commercial inference is permitted."],
            }
        )
        self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
        event = self._event_for_transition(
            goal,
            state,
            "escalated",
            [entry["request_path"], entry["escalation_path"], entry["scorecard_path"]],
            timestamp,
            "lab.py",
            CONTINUATION_COMMAND,
            [{"test_id": "external-write-refused", "passed": True, "evidence": entry["escalation_path"]}],
            budget_before,
            copy.deepcopy(state["budget_used"]),
            {"passed": True, "summary": "external write was refused and escalated without substitution"},
            sha256_file(request_path),
        )
        self._persist_event(entry, state, event)
        state["blocker"] = "external_project_write approval is required; no external action was performed"
        self._write_json(self.resolve(entry["state_path"]), state)
        return event

    def _emit_safety_escalation(
        self,
        entry: dict[str, Any],
        goal: dict[str, Any],
        state: dict[str, Any],
        scorecard: dict[str, Any],
        escalation: dict[str, Any],
        action: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        repeated = action.get("budget") == "retries"
        new_state = "escalated" if repeated else "budget_exhausted"
        reason_code = "repeated_failure" if repeated else "budget_exhausted"
        escalation.update(
            {
                "created_at": timestamp,
                "status": "open",
                "reason_code": reason_code,
                "summary": action["reason"],
                "evidence": [f"state.budget_used={json.dumps(state['budget_used'], sort_keys=True)}", f"state.retry_count={state['retry_count']}"],
                "requested_decision": "Review the stopped experiment; do not continue without a new bounded, approved plan.",
                "allowed_resolutions": ["keep experiment stopped", "authorize a separately reviewed revised budget or recovery plan"],
                "tradeoffs": ["Keeping it stopped preserves the registered budget and failure boundary.", "Continuing would change authority or budget and requires explicit review."],
                "recommended_choice": "Keep the experiment stopped until the cause and a bounded revision are reviewed.",
                "resolved_at": None,
                "resolution": None,
            }
        )
        self._write_json(self.resolve(entry["escalation_path"]), escalation)
        scorecard["status"] = "incomplete"
        scorecard["decision"] = "escalate"
        self._write_json(self.resolve(entry["scorecard_path"]), scorecard)
        event = self._event_for_transition(
            goal,
            state,
            new_state,
            [entry["state_path"], entry["escalation_path"], entry["scorecard_path"]],
            timestamp,
            "lab.py",
            CONTINUATION_COMMAND,
            [{"test_id": reason_code, "passed": True, "evidence": entry["escalation_path"]}],
            copy.deepcopy(state["budget_used"]),
            copy.deepcopy(state["budget_used"]),
            {"passed": True, "summary": f"controller stopped at {reason_code}"},
            None,
        )
        self._persist_event(entry, state, event)
        state["blocker"] = action["reason"]
        self._write_json(self.resolve(entry["state_path"]), state)
        return event

    def run_one_step(self, experiment_id: str | None = None, timestamp: str | None = None) -> tuple[int, dict[str, Any]]:
        if experiment_id is None and self.registry.get("current_experiment_id") is None:
            selected = self.scheduler_entry()
            if selected is None:
                return EXIT_OK, {
                    "result": "no_eligible_experiment",
                    "state": None,
                    "transition": None,
                    "message": NO_ELIGIBLE_MESSAGE,
                }
            experiment_id = selected["experiment_id"]
        entry, goal, state, scorecard, escalation = self.records(experiment_id)
        action = self.next_action(goal["experiment_id"])
        if action["kind"] == "stop":
            return EXIT_OK, {"result": "terminal_stable", "state": state["state"], "transition": None}
        if action["kind"] == "human_approval":
            return EXIT_APPROVAL_REQUIRED, {"result": "human_approval_required", "state": state["state"], "transition": None, "reason": action["reason"]}
        timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if action["kind"] == "escalate":
            event = self._emit_safety_escalation(entry, goal, state, scorecard, escalation, action, timestamp)
            exit_code = EXIT_APPROVAL_REQUIRED if event["new_state"] == "escalated" else EXIT_BUDGET_EXHAUSTED
            return exit_code, {"result": action["kind"], "previous_state": event["previous_state"], "state": event["new_state"], "transition": f"{event['previous_state']}->{event['new_state']}", "reason": action["reason"], "event_sha256": event["event_sha256"]}
        if entry.get("runner_kind") == "deterministic-normalization":
            if action["kind"] != "transition":
                raise LabValidationError(f"normalization fixture cannot perform action {action['kind']}")
            event = self._run_normalization_step(entry, goal, state, scorecard, action["transition"], timestamp)
        elif entry.get("runner_kind") == "external-action-escalation":
            event = self._run_external_escalation_step(entry, goal, state, scorecard, escalation, action, timestamp)
        elif entry.get("runner_kind") == "phase0-preparation":
            if action["kind"] != "transition":
                raise LabValidationError(f"Phase 0 runner cannot perform action {action['kind']}")
            event = self._run_phase0_step(entry, goal, state, scorecard, escalation, action["transition"], timestamp)
        else:
            raise LabValidationError("current experiment has no autonomous local runner; approval is required")
        approval_required = event["new_state"] == "escalated" or (
            entry.get("runner_kind") == "phase0-preparation" and event["new_state"] == "completed"
        )
        return EXIT_APPROVAL_REQUIRED if approval_required else EXIT_OK, {
            "result": "one_step_completed",
            "previous_state": event["previous_state"],
            "state": event["new_state"],
            "transition": f"{event['previous_state']}->{event['new_state']}",
            "event_sha256": event["event_sha256"],
            "artifact_sha256": event.get("artifact_sha256"),
        }

    def evaluate(self, results_path: Path, timestamp: str) -> dict[str, Any]:
        entry, goal, state, scorecard, _ = self.records()
        if state["state"] != "evaluating":
            raise LabValidationError("evaluate requires state=evaluating")
        if not goal.get("objective_oracle"):
            raise LabValidationError("evaluate requires an objective oracle")
        results = load_json(results_path)
        if not isinstance(results, list) or not results:
            raise LabValidationError("evaluate requires non-empty acceptance-test results")
        if len(results) < len(goal["acceptance_tests"]):
            raise LabValidationError("acceptance-test results are incomplete")
        if any(not item.get("passed") or not item.get("evidence") for item in results):
            raise LabValidationError("objective acceptance tests did not all pass with evidence")
        if scorecard["comparison_pairs"] < goal["minimum_comparison_pairs"]:
            raise LabValidationError("minimum comparison pairs have not been met")
        scorecard["status"] = "evaluated"
        scorecard["acceptance_results"] = results
        scorecard["decision"] = "complete"
        self.schema_validate(scorecard, "scorecard", "evaluated scorecard")
        scorecard_path = self.resolve(entry["scorecard_path"])
        scorecard_path.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
        event = self._event_for_transition(
            goal,
            state,
            "completed",
            [str(results_path), entry["scorecard_path"]],
            timestamp,
            "lab-controller",
            "evaluate",
            results,
        )
        self._persist_event(entry, state, event)
        return event

    def render_reports(self, run_id: str | None = None, scheduled: bool = False) -> tuple[str, str, str]:
        if self.registry.get("current_experiment_id") is None and self.scheduler_entry() is None:
            status = {
                "schema_version": 1,
                "run_id": run_id,
                "experiment_id": None,
                "experiment_kind": None,
                "current_state": None,
                "last_transition": None,
                "next_permitted_action": {"kind": "no_work", "reason": NO_ELIGIBLE_MESSAGE, "transition": None},
                "another_scheduled_run_useful": False,
                "human_approval_required": False,
                "budget_consumed": None,
                "budget_remaining": None,
                "artifact_sha256": None,
                "state_sha256": None,
                "continuation_command": SCHEDULED_COMMAND,
                "latest_error_or_blocker": NO_ELIGIBLE_MESSAGE,
                "scheduler_enabled": False,
            }
            status_json = json.dumps(status, indent=2) + "\n"
            status_md = f"""# Autonomous Lab current status

## Operator summary

- Run ID: `{run_id}`
- Experiment ID: `None`
- Experiment kind: `None`
- Current state: `None`
- Last transition: `None`
- Next permitted action: `no_work` — {NO_ELIGIBLE_MESSAGE}
- Another scheduled run useful: `no`
- Human approval required: `no`
- Budget consumed: `None`
- Budget remaining: `None`
- Artifact SHA-256: `None`
- State SHA-256: `None`
- Exact continuation command: `{SCHEDULED_COMMAND}`
- Latest error or blocker: {NO_ELIGIBLE_MESSAGE}

No experiment is currently scheduler-eligible. Archived shakedown and
regression fixtures remain excluded from live selection, and no experiment is
implicitly enabled by this report.
"""
            next_md = "# Next human action\n\nNo human action required\n"
            return status_json, status_md, next_md
        _, goal, state, scorecard, escalation = self.records()
        entry = self.current_entry()
        matching_events = [event for event in self.read_ledger() if event["experiment_id"] == goal["experiment_id"]]
        last_event = matching_events[-1]
        next_action = self.next_action(goal["experiment_id"])
        human_required = next_action["kind"] in {"human_approval", "external_action"} or escalation["status"] == "open"
        budget_limits = goal["budgets"]
        budget_remaining = {
            "iterations": budget_limits["max_iterations"] - state["budget_used"]["iterations"],
            "commands": budget_limits["max_commands"] - state["budget_used"]["commands"],
            "tests": budget_limits["max_tests"] - state["budget_used"]["tests"],
            "model_calls": budget_limits["max_model_calls"] - state["budget_used"]["model_calls"],
            "wall_minutes": budget_limits["max_wall_clock_hours"] * 60 - state["budget_used"]["wall_minutes"],
            "tokens": budget_limits["max_tokens"] - state["budget_used"]["tokens"],
            "cost_usd": budget_limits["max_model_cost_usd"] - state["budget_used"]["cost_usd"],
        }
        status = {
            "schema_version": 1,
            "run_id": run_id,
            "generated_from_state_at": state["updated_at"],
            "current_experiment": {
                "experiment_id": goal["experiment_id"],
                "experiment_kind": entry["experiment_kind"],
                "state": state["state"],
                "milestone": state["milestone"],
                "blocker": state["blocker"],
                "last_completed_transition": f"{last_event['previous_state']}->{last_event['new_state']}",
                "next_permitted_action": next_action,
                "budget_consumed": state["budget_used"],
                "budget_remaining": budget_remaining,
                "human_approval_required": human_required,
                "another_scheduled_run_useful": next_action["kind"] == "transition",
                "continuation_command": SCHEDULED_COMMAND if scheduled else CONTINUATION_COMMAND,
                "latest_error_or_blocker": state["blocker"],
                "scorecard_status": scorecard["status"],
                "ledger_event_count": state["ledger_event_count"],
                "ledger_head_sha256": state["ledger_head_sha256"],
                "artifact_sha256": last_event.get("artifact_sha256"),
                "state_sha256": sha256_file(self.resolve(entry["state_path"])),
            },
            "open_escalation": {
                "escalation_id": escalation["escalation_id"],
                "reason_code": escalation["reason_code"],
                "requested_decision": escalation["requested_decision"],
                "evidence": escalation["evidence"],
                "options": escalation["allowed_resolutions"],
                "risks_and_tradeoffs": escalation["tradeoffs"],
                "recommended_choice": escalation["recommended_choice"],
            } if escalation["status"] == "open" else None,
            "historical_summary": {
                "batch_01": "Technical feasibility and limited external usefulness; zero promotion-ready candidates.",
                "batch_02": "Twenty-four screened, zero qualified under corrected gates, and no material AEG repair effect.",
            },
            "forbidden_without_approval": [
                "screening or execution",
                "model, agent, or paid execution",
                "external communication or writes",
                "candidate promotion or verified-library changes",
                "release publication",
            ],
        }
        status_json = json.dumps(status, indent=2) + "\n"
        status_md = f"""# Autonomous Lab current status

## Operator summary

- Active experiment: `{goal['experiment_id']}`
- Run ID: `{run_id}`
- Experiment kind: `{entry['experiment_kind']}`
- Current state: `{state['state']}`
- Last completed transition: `{last_event['previous_state']}->{last_event['new_state']}`
- Next permitted action: `{next_action['kind']}` — {next_action['reason']}
- Budget consumed: `{json.dumps(state['budget_used'], sort_keys=True)}`
- Budget remaining: `{json.dumps(budget_remaining, sort_keys=True)}`
- Human approval required: `{'yes' if human_required else 'no'}`
- Another scheduled run useful: `{'yes' if next_action['kind'] == 'transition' else 'no'}`
- Exact continuation command: `{SCHEDULED_COMMAND if scheduled else CONTINUATION_COMMAND}`
- Latest error or blocker: `{state['blocker']}`

## Integrity

- Milestone: {state['milestone']}
- Blocker: `{state['blocker']}`
- Experiment ledger events: {state['ledger_event_count']}
- Ledger head: `{state['ledger_head_sha256']}`
- Last artifact SHA-256: `{last_event.get('artifact_sha256')}`
- State SHA-256: `{sha256_file(self.resolve(entry['state_path']))}`
- Scorecard: `{scorecard['status']}` / `{scorecard['decision']}`
- Model calls: `{state['budget_used']['model_calls']}`
- Paid cost: `${state['budget_used']['cost_usd']}`
- External writes: `0`
- Candidate promotions: `0`
- Verified-library changes: `0`

Batch 01 remains technical-feasibility and limited-external-usefulness evidence
with zero promotion-ready candidates. Corrected Batch 02 remains a screening
and abstention calibration: 24 screened, zero qualified, one independently
reproduced but publicly non-fresh repair, and no material AEG repair effect.

The shakedown records validate orchestration only. They do not supply AEG
effectiveness, coding-agent intelligence, customer-demand, commercial, or
product-market-fit evidence.
"""
        if human_required:
            options = "\n".join(f"{index}. {option}" for index, option in enumerate(escalation["allowed_resolutions"], 1))
            evidence = "\n".join(f"- {item}" for item in escalation["evidence"])
            tradeoffs = "\n".join(f"- {item}" for item in escalation["tradeoffs"])
            next_md = f"""# Next human action

Human approval is required for `{goal['experiment_id']}`.

Decision required: {escalation['requested_decision']}

## Evidence

{evidence}

## Options

{options}

## Risks and tradeoffs

{tradeoffs}

Recommended choice: {escalation['recommended_choice']}

The controller performed no external action and will not silently substitute a
local action. A fresh invocation of `{CONTINUATION_COMMAND}` returns exit code
`{EXIT_APPROVAL_REQUIRED}` until a reviewed decision is recorded.
"""
        else:
            next_md = f"""# Next human action

No human action required

- Experiment: `{goal['experiment_id']}`
- State: `{state['state']}`
- Next action: `{next_action['kind']}` — {next_action['reason']}
- Continue with: `{CONTINUATION_COMMAND}`

The command validates first, performs at most one safe repository-local
transition, persists evidence and state, regenerates reports, and exits.
"""
        return status_json, status_md, next_md

    def report(self, check: bool = False, run_id: str | None = None, scheduled: bool = False) -> None:
        rendered = self.render_reports(run_id=run_id, scheduled=scheduled)
        paths = (
            self.root / "reports" / "current-status.json",
            self.root / "reports" / "current-status.md",
            self.root / "reports" / "next-human-action.md",
        )
        stale = [str(path.relative_to(self.repo_root)) for path, content in zip(paths, rendered) if path.read_text(encoding="utf-8") != content]
        if check and stale:
            raise LabValidationError(f"generated reports are stale: {stale}")
        if not check:
            for path, content in zip(paths, rendered):
                path.write_text(content, encoding="utf-8")

    def scheduled_step(
        self,
        timestamp: str | None = None,
        run_id: str | None = None,
        actor: str | None = None,
        persist_commit: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        run_id = run_id or str(uuid.uuid4())
        config = load_config(self.root)
        repository_root(self.repo_root)
        selected = self.scheduler_entry()
        expected_state: str | None = None
        expected_hash: str | None = None
        if selected:
            state_path = self.resolve(selected["state_path"])
            expected_state = load_json(state_path)["state"]
            expected_hash = sha256_file(state_path)
        lease = ExecutionLease(self.repo_root, config)
        lease.acquire(
            run_id,
            timestamp,
            selected["experiment_id"] if selected else None,
            expected_state,
            expected_hash,
            actor,
        )
        outcome = "failed"
        try:
            preflight = preflight_worktree(self.repo_root, self.root, config, selected)
            self.validate()
            if selected is None:
                outcome = "no_eligible_experiment"
                return EXIT_OK, {
                    "run_id": run_id,
                    "result": outcome,
                    "message": NO_ELIGIBLE_MESSAGE,
                    "experiment_id": None,
                    "transition": None,
                    "preflight": preflight,
                }
            exit_code, result = self.run_one_step(selected["experiment_id"], timestamp)
            self.report(run_id=run_id, scheduled=True)
            persistence = None
            if persist_commit and result.get("event_sha256") and result.get("transition"):
                self.validate()
                self.report(check=True, run_id=run_id, scheduled=True)
                persistence = persist_transition_commit(
                    self.repo_root, selected, result["transition"]
                )
            outcome = result["result"]
            return exit_code, {
                "run_id": run_id,
                "experiment_id": selected["experiment_id"],
                **result,
                "preflight": preflight,
                "persistence": persistence,
            }
        except UnsafeWorktreeError as error:
            recovery = write_transient_recovery_request(self.repo_root, timestamp, run_id, str(error))
            outcome = "unsafe_worktree"
            raise UnsafeWorktreeError(f"{error}; recovery request: {recovery}") from error
        finally:
            lease.release(timestamp, outcome)

    def recover_stale_lease(self, timestamp: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        run_id = run_id or str(uuid.uuid4())
        config = load_config(self.root)
        repository_root(self.repo_root)
        recovered = ExecutionLease(self.repo_root, config).recover_stale(timestamp, run_id)
        return {"run_id": run_id, "result": "stale_lease_recovered", "recovered_run_id": recovered.get("run_id")}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="autonomous-lab directory (tests only)")
    parser.add_argument("--experiment", help="controlled experiment ID; defaults to registry current_experiment_id")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--base-ref")
    subparsers.add_parser("status")
    subparsers.add_parser("next")
    report = subparsers.add_parser("report")
    report.add_argument("--check", action="store_true")
    step = subparsers.add_parser("run-one-step")
    step.add_argument("--timestamp", help="explicit RFC 3339 timestamp; defaults to current UTC time")
    scheduled = subparsers.add_parser("scheduled-step")
    scheduled.add_argument("--timestamp", help="explicit RFC 3339 timestamp; defaults to current UTC time")
    scheduled.add_argument("--run-id", help="explicit run ID; defaults to a UUID")
    scheduled.add_argument("--actor", help="optional scheduler actor identity")
    scheduled.add_argument(
        "--persist-commit",
        action="store_true",
        help="commit only the validated allowlisted outputs of one transition",
    )
    recover = subparsers.add_parser("recover-stale-lease")
    recover.add_argument("--timestamp", help="explicit RFC 3339 timestamp; defaults to current UTC time")
    recover.add_argument("--run-id", help="explicit recovery run ID; defaults to a UUID")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--results", type=Path, required=True)
    evaluate.add_argument("--timestamp", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        lab = Lab(args.root)
        if args.command == "validate":
            print(json.dumps(lab.validate(base_ref=args.base_ref), indent=2))
        elif args.command == "status":
            lab.validate()
            print(json.dumps(lab.status(args.experiment), indent=2))
        elif args.command == "next":
            lab.validate()
            print(json.dumps(lab.next_action(args.experiment), indent=2))
        elif args.command == "report":
            lab.validate()
            lab.report(check=args.check)
            print("reports valid" if args.check else "reports updated")
        elif args.command == "run-one-step":
            lab.validate()
            exit_code, result = lab.run_one_step(args.experiment, args.timestamp)
            if args.experiment is None or args.experiment == lab.registry["current_experiment_id"]:
                lab.report()
            print(json.dumps({"exit_code": exit_code, **result}, indent=2))
            return exit_code
        elif args.command == "scheduled-step":
            exit_code, result = lab.scheduled_step(
                args.timestamp, args.run_id, args.actor, args.persist_commit
            )
            print(json.dumps({"exit_code": exit_code, **result}, indent=2))
            return exit_code
        elif args.command == "recover-stale-lease":
            result = lab.recover_stale_lease(args.timestamp, args.run_id)
            print(json.dumps({"exit_code": EXIT_OK, **result}, indent=2))
        elif args.command == "evaluate":
            lab.validate()
            event = lab.evaluate(args.results, args.timestamp)
            print(json.dumps(event, indent=2))
        return EXIT_OK
    except (LabValidationError, FileNotFoundError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_VALIDATION_FAILED
    except LeaseHeldError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_LEASE_HELD
    except UnsafeWorktreeError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_UNSAFE_WORKTREE
    except SchedulerConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_SCHEDULER_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
