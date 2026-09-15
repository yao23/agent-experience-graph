#!/usr/bin/env python3
"""Validate the non-executable Model-Strength Transfer v1 proposal.

The validator intentionally uses only the Python standard library. The JSON
Schema remains available for editors and CI environments that already provide
a Draft 2020-12 validator, but proposal validation must not require installing
a new package.
"""

import json
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent


class ProtocolError(RuntimeError):
    pass


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def require(condition, message):
    if not condition:
        raise ProtocolError(f"protocol schema invalid: {message}")


def require_unique_strings(value, minimum, field):
    require(isinstance(value, list), f"{field} must be an array")
    require(len(value) >= minimum, f"{field} must contain at least {minimum} items")
    require(all(isinstance(item, str) and item for item in value), f"{field} must contain non-empty strings")
    require(len(value) == len(set(value)), f"{field} must contain unique items")


def validate(protocol=None):
    protocol = protocol or load_json(HERE / "protocol.json")
    schema = load_json(HERE / "protocol.schema.json")
    required = set(schema["required"])
    allowed = set(schema["properties"])
    require(isinstance(protocol, dict), "root must be an object")
    require(set(protocol) == required == allowed, "root keys must exactly match the schema")
    require(protocol["schema_version"] == "1.0.0", "schema_version changed")
    require(protocol["experiment_id"] == "model-strength-transfer-v1", "experiment_id changed")
    require(protocol["status"] == "PROPOSED_NOT_AUTHORIZED", "proposal status changed")
    require(isinstance(protocol["research_question"], str) and len(protocol["research_question"]) >= 20, "research_question is missing")
    try:
        datetime.fromisoformat(protocol["astra_release_cutoff"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ProtocolError("protocol schema invalid: astra_release_cutoff must be an ISO date-time") from error
    require(protocol["selected_task"] is None, "selected_task must remain null")
    require(protocol["selected_experience"] is None, "selected_experience must remain null")

    authority = protocol["execution_authority"]
    require(isinstance(authority, dict), "execution_authority must be an object")
    require(set(authority) == {"authorized", "reason", "required_before_activation"}, "execution_authority keys changed")
    require(authority["authorized"] is False, "execution must remain unauthorized")
    require(isinstance(authority["reason"], str) and len(authority["reason"]) >= 20, "authorization reason is missing")
    require_unique_strings(authority["required_before_activation"], 6, "required_before_activation")

    eligibility = protocol["eligibility"]
    required_flags = {
        "experience_recorded_before_astra_release",
        "target_independently_originated",
        "public_and_license_compatible",
        "objective_local_oracle_required",
        "same_frozen_input_across_cells",
    }
    require(isinstance(eligibility, dict), "eligibility must be an object")
    require(set(eligibility) == required_flags | {"allowed_task_families", "excluded_task_families"}, "eligibility keys changed")
    require(all(eligibility[field] is True for field in required_flags), "eligibility safety flags must remain true")
    require_unique_strings(eligibility["allowed_task_families"], 1, "allowed_task_families")
    require_unique_strings(eligibility["excluded_task_families"], 1, "excluded_task_families")

    expected_models = {
        "frontier": ("openai", "gpt-6-astra"),
        "predecessor": ("openai", "gpt-5.6-sol"),
        "external": ("TBD_EXTERNAL_PROVIDER", "TBD_EXTERNAL_MODEL"),
    }
    require(isinstance(protocol["models"], list) and len(protocol["models"]) == 3, "models must contain exactly three slots")
    require(all(isinstance(item, dict) and set(item) == {"slot", "provider", "model", "availability"} for item in protocol["models"]), "model entry keys changed")
    actual_models = {item["slot"]: (item["provider"], item["model"]) for item in protocol["models"]}
    if actual_models != expected_models:
        raise ProtocolError("model slots changed before activation")
    allowed_availability = {"UNCONFIRMED_FOR_PROTOCOL_RUNNER", "NOT_SELECTED"}
    require(all(item["availability"] in allowed_availability for item in protocol["models"]), "model availability value is invalid")

    require(protocol["modes"] == ["control", "aeg-assisted"], "modes changed")
    require(isinstance(protocol["arm_matrix"], list) and len(protocol["arm_matrix"]) == 6, "arm_matrix must contain six cells")
    require(all(isinstance(item, dict) and set(item) == {"model_slot", "mode", "status"} for item in protocol["arm_matrix"]), "arm_matrix entry keys changed")
    require(all(item["status"] == "NOT_ATTEMPTED" for item in protocol["arm_matrix"]), "all arms must remain NOT_ATTEMPTED")

    expected_cells = {
        (slot, mode)
        for slot in expected_models
        for mode in protocol["modes"]
    }
    actual_cells = {
        (item["model_slot"], item["mode"])
        for item in protocol["arm_matrix"]
    }
    if actual_cells != expected_cells:
        raise ProtocolError("arm matrix must contain one control/treatment cell per model")

    require(isinstance(protocol["phases"], list) and len(protocol["phases"]) == 2, "phases must contain paired-smoke and confirmatory")
    require(all(isinstance(item, dict) and set(item) == {"phase", "replicates_per_cell", "planned_arm_runs", "interpretation_limit"} for item in protocol["phases"]), "phase entry keys changed")
    phases = {item["phase"]: item for item in protocol["phases"]}
    require(set(phases) == {"paired-smoke", "confirmatory"}, "phase names changed")
    if phases["paired-smoke"]["replicates_per_cell"] != 1:
        raise ProtocolError("paired smoke must remain one replicate per cell")
    if phases["paired-smoke"]["planned_arm_runs"] != 6:
        raise ProtocolError("paired smoke must remain six arm runs")
    if phases["confirmatory"]["replicates_per_cell"] != 3:
        raise ProtocolError("confirmatory phase must remain three replicates per cell")
    if phases["confirmatory"]["planned_arm_runs"] != 18:
        raise ProtocolError("confirmatory phase must remain eighteen arm runs")

    input_contract = protocol["input_contract"]
    require(isinstance(input_contract, dict) and set(input_contract) == {"shared", "control", "aeg_assisted"}, "input_contract keys changed")
    require_unique_strings(input_contract["shared"], 5, "input_contract.shared")
    require(all(isinstance(input_contract[field], str) and len(input_contract[field]) >= 10 for field in ("control", "aeg_assisted")), "mode input contracts are missing")
    require_unique_strings(protocol["measurements"], 10, "measurements")
    require_unique_strings(protocol["result_labels"], 7, "result_labels")
    require_unique_strings(protocol["stop_conditions"], 6, "stop_conditions")
    interpretation = protocol["interpretation_policy"]
    require(isinstance(interpretation, dict) and len(interpretation) >= 6, "interpretation_policy is incomplete")
    require(all(value is True for value in interpretation.values()), "interpretation_policy values must remain true")
    require_unique_strings(protocol["references"], 5, "references")

    return {
        "experiment_id": protocol["experiment_id"],
        "status": protocol["status"],
        "authorized": protocol["execution_authority"]["authorized"],
        "selected_task": protocol["selected_task"],
        "selected_experience": protocol["selected_experience"],
        "model_cells": len(actual_cells),
        "planned_smoke_arms": phases["paired-smoke"]["planned_arm_runs"],
        "planned_confirmatory_arms": phases["confirmatory"]["planned_arm_runs"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
