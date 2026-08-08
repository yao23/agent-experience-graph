#!/usr/bin/env python3
"""Deterministic controller and validator for the AEG Autonomous Lab v0."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


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
    "proposed": {"screening", "rejected", "cancelled", "escalated"},
    "screening": {"preregistered", "rejected", "blocked", "cancelled", "escalated"},
    "preregistered": {"ready", "blocked", "contaminated", "cancelled", "escalated"},
    "ready": {"running", "blocked", "cancelled", "escalated"},
    "running": {"evaluating", "blocked", "budget_exhausted", "contaminated", "cancelled", "escalated"},
    "evaluating": {"running", "completed", "blocked", "budget_exhausted", "contaminated", "cancelled", "escalated"},
}
NEXT_STAGE = {
    "proposed": "screening",
    "screening": "preregistered",
    "preregistered": "ready",
    "ready": "running",
    "running": "evaluating",
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
        previous_state = "none"
        matching: list[dict[str, Any]] = []
        seen_terminal = False
        for index, event in enumerate(self.read_ledger(), 1):
            if set(event) != EVENT_FIELDS:
                missing = sorted(EVENT_FIELDS - set(event))
                extra = sorted(set(event) - EVENT_FIELDS)
                raise LabValidationError(f"ledger event {index} fields invalid; missing={missing}, extra={extra}")
            if event["sequence"] != index:
                raise LabValidationError(f"ledger sequence {event['sequence']} should be {index}")
            if event["previous_event_sha256"] != previous_hash:
                raise LabValidationError(f"ledger event {index} breaks previous hash chain")
            if event["event_sha256"] != canonical_hash(event):
                raise LabValidationError(f"ledger event {index} content hash mismatch (possible overwrite)")
            if event["previous_state"] != previous_state:
                raise LabValidationError(f"ledger event {index} does not name the actual previous state")
            if seen_terminal:
                raise LabValidationError("ledger continues after a terminal state")
            if event["new_state"] not in TRANSITIONS.get(previous_state, set()):
                raise LabValidationError(
                    f"invalid or skipped transition {previous_state} -> {event['new_state']}"
                )
            if not event["evidence"]:
                raise LabValidationError(f"ledger event {index} has no evidence")
            if event["new_state"] == "running":
                prior_states = {item["new_state"] for item in matching}
                if not {"preregistered", "ready"}.issubset(prior_states):
                    raise LabValidationError("execution attempted before preregistration and readiness")
            if event["new_state"] == "evaluating" and not goal.get("objective_oracle"):
                raise LabValidationError("evaluation attempted without an objective oracle")
            if event["experiment_id"] == goal["experiment_id"]:
                matching.append(event)
            previous_hash = event["event_sha256"]
            previous_state = event["new_state"]
            seen_terminal = event["new_state"] in TERMINAL_STATES

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
        if state["state"] in progressed_states and state["approvals"].get("begin_experiment") != "approved":
            raise LabValidationError("experiment progressed without begin_experiment approval")
        execution_states = {"running", "evaluating", "completed"}
        if state["state"] in execution_states and state["approvals"].get("model_or_agent_execution") != "approved":
            raise LabValidationError("execution progressed without model_or_agent_execution approval")

    def validate_registry(self) -> None:
        if self.registry.get("schema_version") != 1:
            raise LabValidationError("registry schema_version must be 1")
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
            for key in ("evidence_path", "goal_path", "state_path", "scorecard_path", "escalation_path"):
                if key in entry and not self.resolve(entry[key]).is_file():
                    raise LabValidationError(f"registry path does not exist: {entry[key]}")
        current_id = self.registry.get("current_experiment_id")
        if current_id not in ids:
            raise LabValidationError("registry current_experiment_id is absent from experiments")
        self.current_entry(current_id)

    def validate_templates(self) -> None:
        self.schema_validate(load_yaml(self.root / "templates" / "goal.yaml"), "goal", "goal template")
        self.schema_validate(load_json(self.root / "templates" / "state.json"), "state", "state template")
        self.schema_validate(load_json(self.root / "templates" / "scorecard.json"), "scorecard", "scorecard template")
        run_record = load_json(self.root / "templates" / "run-record.json")
        required = {"schema_version", "experiment_id", "run_id", "baseline_or_treatment", "budget_used", "external_writes"}
        if not required.issubset(run_record):
            raise LabValidationError("run-record template omits required fields")

    def validate(self, base_ref: str | None = None) -> dict[str, Any]:
        for name, schema in self.schemas.items():
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as error:
                raise LabValidationError(f"{name} schema is invalid: {error}") from error
        self.validate_registry()
        self.validate_templates()
        entry, goal, state, scorecard, escalation = self.records()
        self.schema_validate(goal, "goal", "current goal")
        self.schema_validate(state, "state", "current state")
        self.schema_validate(scorecard, "scorecard", "current scorecard")
        self.schema_validate(escalation, "escalation", "current escalation")
        self.validate_semantics(entry, goal, state, scorecard, escalation)
        self.validate_ledger(goal, state)
        if base_ref:
            self.validate_git_history(base_ref)
        return {
            "schemas": len(self.schemas),
            "registry_experiments": len(self.registry["experiments"]),
            "current_experiment": goal["experiment_id"],
            "state": state["state"],
            "ledger_events": state["ledger_event_count"],
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

    def approval_decision(self, action: str) -> dict[str, Any]:
        """Return a fail-closed decision for sensitive product/external actions."""
        _, goal, state, _, _ = self.records()
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
        _, goal, state, _, escalation = self.records(experiment_id)
        current = state["state"]
        if current in TERMINAL_STATES:
            return {"kind": "stop", "reason": f"{current} is terminal", "transition": None}
        exhausted = self.budget_exhaustion(goal, state)
        if exhausted:
            return {"kind": "escalate", "reason": f"{exhausted} budget reached", "transition": "budget_exhausted"}
        if escalation["status"] == "open":
            return {
                "kind": "human_approval",
                "reason": escalation["summary"],
                "transition": None,
                "escalation_id": escalation["escalation_id"],
            }
        transition = NEXT_STAGE.get(current)
        if not transition:
            return {"kind": "human_review", "reason": "evaluation decision required", "transition": None}
        required_gate = "begin_experiment" if current == "proposed" else None
        if transition == "running":
            required_gate = "model_or_agent_execution"
        if required_gate and state["approvals"].get(required_gate) != "approved":
            return {"kind": "human_approval", "reason": f"{required_gate} approval is not recorded", "transition": None}
        return {"kind": "transition", "reason": "next lifecycle evidence may be recorded", "transition": transition}

    def status(self) -> dict[str, Any]:
        entry, goal, state, scorecard, escalation = self.records()
        return {
            "experiment_id": goal["experiment_id"],
            "registry_state": entry["state"],
            "state": state["state"],
            "milestone": state["milestone"],
            "blocker": state["blocker"],
            "budget_used": state["budget_used"],
            "scorecard_status": scorecard["status"],
            "ledger_event_count": state["ledger_event_count"],
            "ledger_head_sha256": state["ledger_head_sha256"],
            "open_escalation": escalation["escalation_id"] if escalation["status"] == "open" else None,
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
    ) -> dict[str, Any]:
        if new_state not in TRANSITIONS.get(state["state"], set()):
            raise LabValidationError(f"transition {state['state']} -> {new_state} is not allowed")
        if state["state"] in TERMINAL_STATES:
            raise LabValidationError("cannot continue after a terminal state")
        if not evidence:
            raise LabValidationError("a transition requires evidence")
        if state["state"] == "proposed" and new_state == "screening":
            if state["approvals"].get("begin_experiment") != "approved":
                raise LabValidationError("screening requires begin_experiment approval")
        if new_state == "running" and state["approvals"].get("model_or_agent_execution") != "approved":
            raise LabValidationError("execution requires model_or_agent_execution approval")
        if new_state == "evaluating" and not goal.get("objective_oracle"):
            raise LabValidationError("evaluation requires an objective oracle")
        event = {
            "sequence": state["ledger_event_count"] + 1,
            "event_type": "state_transition",
            "experiment_id": goal["experiment_id"],
            "previous_event_sha256": state["ledger_head_sha256"],
            "previous_state": state["state"],
            "new_state": new_state,
            "timestamp": timestamp,
            "actor": actor,
            "command": command,
            "evidence": evidence,
            "acceptance_test_results": acceptance_results or [],
            "budget_status": copy.deepcopy(state["budget_used"]),
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

    def render_reports(self) -> tuple[str, str, str]:
        _, goal, state, _, escalation = self.records()
        status = {
            "schema_version": 1,
            "generated_from_state_at": state["updated_at"],
            "current_experiment": {
                "experiment_id": goal["experiment_id"],
                "state": state["state"],
                "milestone": state["milestone"],
                "blocker": state["blocker"],
                "ledger_event_count": state["ledger_event_count"],
                "ledger_head_sha256": state["ledger_head_sha256"],
            },
            "open_escalation": {
                "escalation_id": escalation["escalation_id"],
                "reason_code": escalation["reason_code"],
                "requested_decision": escalation["requested_decision"],
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

- Current experiment: `{goal['experiment_id']}`
- State: `{state['state']}`
- Milestone: {state['milestone']}
- Blocker: `{state['blocker']}`
- Ledger: {state['ledger_event_count']} event; head `{state['ledger_head_sha256']}`
- Execution: none
- External writes: none
- Candidate promotions: none
- Verified-library changes: none

Batch 01 remains technical-feasibility and limited-external-usefulness evidence
with zero promotion-ready candidates. Corrected Batch 02 remains a screening
and abstention calibration: 24 screened, zero qualified, one independently
reproduced but publicly non-fresh repair, and no material AEG repair effect.

The current proposal supplies no generalized-effectiveness, customer-demand,
commercial, or product-market-fit evidence.

## Open escalation

`{escalation['escalation_id']}` asks a human to approve screening only,
request a design revision, or reject the experiment. No decision is implied by
silence.
"""
        next_md = f"""# Next human action

Review the proposed “AEG-assisted Agent Failure Recovery Service” goal and
choose exactly one recorded resolution for escalation
`{escalation['escalation_id']}`:

1. approve screening only;
2. request a design revision; or
3. reject the experiment.

Approval to screen would not authorize model or agent execution, paid cost,
external contact or writes, pull requests, candidate promotion, verified-library
changes, secrets, or a release. Those gates remain separate and pending.

## Evidence and tradeoffs

The goal and state both record that the experiment has not started and that all
execution and external gates remain pending. Approving screening tests candidate
availability but does not authorize recruitment or execution. Requesting a
revision delays screening but can improve the causal and commercial design.
Rejecting preserves all budgets but leaves demand untested.

Recommended choice: request design review, then approve screening only if the
baseline, treatment, customer access, and external acceptance path are credible.
"""
        return status_json, status_md, next_md

    def report(self, check: bool = False) -> None:
        rendered = self.render_reports()
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


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="autonomous-lab directory (tests only)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--base-ref")
    subparsers.add_parser("status")
    subparsers.add_parser("next")
    report = subparsers.add_parser("report")
    report.add_argument("--check", action="store_true")
    step = subparsers.add_parser("run-one-step")
    step.add_argument("--evidence", action="append", default=[])
    step.add_argument("--timestamp", required=True)
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
            print(json.dumps(lab.status(), indent=2))
        elif args.command == "next":
            lab.validate()
            print(json.dumps(lab.next_action(), indent=2))
        elif args.command == "report":
            lab.validate()
            lab.report(check=args.check)
            print("reports valid" if args.check else "reports updated")
        elif args.command == "run-one-step":
            lab.validate()
            action = lab.next_action()
            if action["kind"] != "transition":
                raise LabValidationError(f"no autonomous transition permitted: {action['reason']}")
            event = lab.perform_transition(action["transition"], args.evidence, args.timestamp)
            print(json.dumps(event, indent=2))
        elif args.command == "evaluate":
            lab.validate()
            event = lab.evaluate(args.results, args.timestamp)
            print(json.dumps(event, indent=2))
        return 0
    except (LabValidationError, FileNotFoundError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
