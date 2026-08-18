#!/usr/bin/env python3
"""Validate, package, and evaluate Situated Experience Benchmark v1 S1."""

import argparse
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "s1-manifest.json"
FREEZE = HERE / "freeze.json"
REGISTRY = HERE / "registry.json"
SCREENING = HERE / "candidate-screening.json"
DECISIONS = HERE / "decision-ledger.jsonl"
SCHEMAS = HERE / "schemas"
FIXTURES = HERE / "fixtures"
MODES = ("control", "aeg-assisted")
EXPERIENCE_FIELDS = (
    "context",
    "version_constraints",
    "failed_approach",
    "invalidating_evidence",
    "recovery_principle",
    "validated_outcome",
    "applicability_conditions",
    "known_invalidation_conditions",
)
EXPECTED_BUNDLE_ENTRIES = {"agent-result.schema.json", "arm.json", "arm_worker.py", "workspace"}
IGNORED_TREE_PARTS = {".git", "__pycache__", ".pytest_cache"}


class ProtocolError(RuntimeError):
    pass


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def canonical_sha256(value):
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def tree_sha256(root):
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in IGNORED_TREE_PARTS for part in relative.parts):
            continue
        name = relative.as_posix().encode()
        data = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def run(args, cwd=None, timeout=120, env=None, input_text=None):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def schema_validate(instance, schema_name, label):
    schema = load_json(SCHEMAS / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors)
        raise ProtocolError(f"{label} schema invalid: {rendered}")


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def expected_orders(manifest):
    rng = random.Random(manifest["protocol"]["randomization_seed"])
    return {
        pair["pair_id"]: [
            list(MODES) if rng.randrange(2) == 0 else list(reversed(MODES))
            for _ in range(manifest["protocol"]["replicates_per_arm"])
        ]
        for pair in manifest["pairs"]
    }


def fixture_root(pair):
    return FIXTURES / pair["pair_id"]


def resolve_relative(path_text):
    path = (HERE / path_text).resolve()
    if HERE not in path.parents:
        raise ProtocolError(f"path escapes benchmark directory: {path_text}")
    return path


def patch_added_lines(patch_text):
    return [line[1:] for line in patch_text.splitlines() if line.startswith("+") and not line.startswith("+++") and len(line[1:].strip()) >= 12]


def validate_decision_ledger():
    previous = None
    count = 0
    for raw in DECISIONS.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        count += 1
        if event.get("sequence") != count:
            raise ProtocolError("decision ledger sequence is not contiguous")
        if event.get("previous_event_sha256") != previous:
            raise ProtocolError("decision ledger previous hash is invalid")
        claimed = event.get("event_sha256")
        material = {key: value for key, value in event.items() if key != "event_sha256"}
        actual = canonical_sha256(material)
        if claimed != actual:
            raise ProtocolError(f"decision ledger hash invalid at sequence {count}")
        previous = claimed
    if count < 4:
        raise ProtocolError("decision ledger omits required design decisions")
    return {"events": count, "head_sha256": previous}


def validate_freeze(manifest):
    freeze = load_json(FREEZE)
    expected = {
        "manifest_sha256": sha256_file(MANIFEST),
        "registry_sha256": sha256_file(REGISTRY),
        "screening_sha256": sha256_file(SCREENING),
        "candidate_screening_contract_sha256": sha256_file(HERE / "CANDIDATE-SCREENING.md"),
        "decision_ledger_sha256": sha256_file(DECISIONS),
        "measurement_contract_sha256": sha256_file(HERE / "MEASUREMENT-CONTRACT.md"),
        "controller_sha256": sha256_file(HERE / "run_benchmark.py"),
        "worker_sha256": sha256_file(HERE / "arm_worker.py"),
        "schemas_tree_sha256": tree_sha256(SCHEMAS),
        "fixtures_tree_sha256": tree_sha256(FIXTURES),
    }
    if freeze.get("schema_version") != "1.0.0" or freeze.get("benchmark_id") != manifest["benchmark_id"]:
        raise ProtocolError("freeze record identity is invalid")
    if freeze.get("protected_inputs") != expected:
        raise ProtocolError("frozen controller input changed")
    if freeze.get("arms_executed_at_freeze") != 0:
        raise ProtocolError("freeze record must precede every arm")
    return freeze


def validate():
    manifest = load_json(MANIFEST)
    registry = load_json(REGISTRY)
    screening = load_json(SCREENING)
    schema_validate(registry, "benchmark-registry.schema.json", "benchmark registry")
    schema_validate(screening, "candidate-screening.schema.json", "candidate screening")
    schema_validate(manifest, "manifest.schema.json", "S1 manifest")
    if manifest["protocol"]["arm_orders"] != expected_orders(manifest):
        raise ProtocolError("frozen arm orders differ from the randomization seed")
    accepted = [item for item in screening["candidates"] if item["status"] == "accepted"]
    rejected = [item for item in screening["candidates"] if item["status"] == "rejected"]
    if len(accepted) != 2 or {item["pair_id"] for item in accepted} != {pair["pair_id"] for pair in manifest["pairs"]}:
        raise ProtocolError("S1 must contain exactly the two accepted screened pairs")
    if len(rejected) != 5:
        raise ProtocolError("the frozen S1 screening ledger must preserve all five rejected candidates")
    seen = set()
    for pair in manifest["pairs"]:
        pair_id = pair["pair_id"]
        if pair_id in seen:
            raise ProtocolError(f"duplicate pair: {pair_id}")
        seen.add(pair_id)
        if parse_time(pair["source"]["fixed_at"]) >= parse_time(pair["transfer"]["fixed_at"]):
            raise ProtocolError(f"{pair_id}: source fix must predate transfer fix")
        if pair["source"]["fixed_commit"] == pair["transfer"]["fixed_commit"]:
            raise ProtocolError(f"{pair_id}: source and transfer fixes must differ")
        root = fixture_root(pair)
        experience_path = resolve_relative(pair["experience_path"])
        experience = load_json(experience_path)
        schema_validate(experience, "experience.schema.json", f"{pair_id} experience")
        if tuple(experience) != EXPERIENCE_FIELDS:
            raise ProtocolError(f"{pair_id}: experience field order or allowlist changed")
        paths_and_hashes = (
            (root / "source" / "buggy", pair["source_fixture_sha256"], True),
            (root / "source" / "evaluator" / "human.patch", pair["source_human_patch_sha256"], False),
            (root / "source" / "evaluator" / "test_hidden.py", pair["source_hidden_tests_sha256"], False),
            (root / "transfer" / "agent", pair["agent_fixture_sha256"], True),
            (root / "transfer" / "evaluator" / "human.patch", pair["human_patch_sha256"], False),
            (root / "transfer" / "evaluator" / "test_hidden.py", pair["hidden_tests_sha256"], False),
            (experience_path, pair["experience_sha256"], False),
        )
        for path, expected, is_tree in paths_and_hashes:
            if not path.exists():
                raise ProtocolError(f"{pair_id}: missing frozen fixture {path}")
            actual = tree_sha256(path) if is_tree else sha256_file(path)
            if actual != expected:
                raise ProtocolError(f"{pair_id}: fixture hash changed for {path.relative_to(HERE)}")
        for pattern in (pair["source_initial_failure_pattern"], pair["initial_failure_pattern"]):
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
        for historical in pair["historical_failure_paths"]:
            re.compile(historical["pattern"], re.IGNORECASE | re.DOTALL)
        serialized = json.dumps(experience, sort_keys=True)
        transfer_patch = (root / "transfer" / "evaluator" / "human.patch").read_text(encoding="utf-8")
        forbidden = [pair["transfer"]["fixed_commit"], pair["human_patch_sha256"]] + patch_added_lines(transfer_patch)
        for needle in forbidden:
            if needle and needle in serialized:
                raise ProtocolError(f"{pair_id}: experience reveals transfer patch material")
    ledger = validate_decision_ledger()
    freeze = validate_freeze(manifest)
    return {
        "benchmark_id": manifest["benchmark_id"],
        "family": "S1",
        "accepted_pairs": 2,
        "rejected_candidates": len(rejected),
        "planned_arms": 12,
        "manifest_sha256": sha256_file(MANIFEST),
        "decision_ledger": ledger,
        "frozen_at": freeze["frozen_at"],
        "status": "valid-frozen-before-execution",
    }


def git_init(workspace):
    steps = (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.name=SEB Controller", "-c", "user.email=seb@example.invalid", "commit", "-qm", "frozen transfer seed"],
    )
    for step in steps:
        result = run(step, cwd=workspace)
        if result.returncode:
            raise ProtocolError(result.stderr)


def run_test(command_text, workspace):
    result = run(shlex.split(command_text), cwd=workspace, timeout=120)
    return {
        "command": command_text,
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout[-3000:],
        "stderr": result.stderr[-3000:],
    }


def apply_patch(workspace, patch_path):
    check = run(["git", "apply", "--check", str(patch_path)], cwd=workspace)
    if check.returncode:
        raise ProtocolError(f"human patch is not applicable: {check.stderr}")
    applied = run(["git", "apply", str(patch_path)], cwd=workspace)
    if applied.returncode:
        raise ProtocolError(f"human patch failed: {applied.stderr}")


def preflight_fixture(pair, stage):
    root = fixture_root(pair) / stage
    seed = root / ("buggy" if stage == "source" else "agent")
    pattern = pair["source_initial_failure_pattern"] if stage == "source" else pair["initial_failure_pattern"]
    command_text = pair["source_public_test_command"] if stage == "source" else pair["public_test_command"]
    with tempfile.TemporaryDirectory(prefix=f"seb-{pair['pair_id']}-{stage}-") as raw:
        workspace = Path(raw) / "workspace"
        shutil.copytree(seed, workspace)
        git_init(workspace)
        initial = run_test(command_text, workspace)
        if initial["passed"]:
            raise ProtocolError(f"{pair['pair_id']} {stage}: buggy seed unexpectedly passed")
        output = initial["stdout"] + "\n" + initial["stderr"]
        if not re.search(pattern, output, re.IGNORECASE | re.DOTALL):
            raise ProtocolError(f"{pair['pair_id']} {stage}: buggy seed failed for an unregistered reason")
        apply_patch(workspace, root / "evaluator" / "human.patch")
        changed = run(["git", "diff", "--name-only"], cwd=workspace).stdout.splitlines()
        if any(name.startswith("test") or "/test" in name or name == "ISSUE.md" for name in changed):
            raise ProtocolError(f"{pair['pair_id']} {stage}: human patch changes protected inputs")
        shutil.copyfile(root / "evaluator" / "test_hidden.py", workspace / "test_hidden.py")
        verified = run_test(pair["hidden_test_command"], workspace)
        if not verified["passed"]:
            raise ProtocolError(f"{pair['pair_id']} {stage}: human patch failed registered suites\n{verified['stdout']}\n{verified['stderr']}")
        return {"initial": initial, "human_patch": verified, "changed_files": changed}


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def task_prompt(pair):
    return (fixture_root(pair) / "transfer" / "agent" / "ISSUE.md").read_text(encoding="utf-8")


def find_pair(manifest, pair_id):
    for pair in manifest["pairs"]:
        if pair["pair_id"] == pair_id:
            return pair
    raise ProtocolError(f"unknown pair: {pair_id}")


def arm_id(pair_id, replicate, mode):
    return f"{pair_id}--r{replicate:02d}--{mode}"


def package_arm(manifest, pair, replicate, mode, output):
    if replicate not in (1, 2, 3) or mode not in MODES:
        raise ProtocolError("invalid arm coordinate")
    if output.exists():
        raise ProtocolError(f"output already exists: {output}")
    output.mkdir(parents=True)
    workspace = output / "workspace"
    shutil.copytree(fixture_root(pair) / "transfer" / "agent", workspace)
    git_init(workspace)
    prompt = task_prompt(pair)
    context_hash = sha256_bytes(b"")
    envelope = {
        "schema_version": "1.0.0",
        "benchmark_id": manifest["benchmark_id"],
        "family": "S1",
        "arm_id": arm_id(pair["pair_id"], replicate, mode),
        "pair_id": pair["pair_id"],
        "replicate": replicate,
        "mode": mode,
        "order": manifest["protocol"]["arm_orders"][pair["pair_id"]][replicate - 1],
        "model": manifest["protocol"]["model"],
        "budget": manifest["protocol"]["budget"],
        "task_prompt": prompt,
        "public_test_command": pair["public_test_command"],
        "allowed_experience_fields": list(EXPERIENCE_FIELDS),
        "input_hashes": {
            "manifest": sha256_file(MANIFEST),
            "agent_fixture": pair["agent_fixture_sha256"],
            "task_prompt": sha256_bytes(prompt.encode()),
            "mode_context": context_hash,
        },
    }
    if mode == "aeg-assisted":
        experience = load_json(resolve_relative(pair["experience_path"]))
        envelope["experience_id"] = f"{pair['pair_id']}-source-experience"
        envelope["experience"] = experience
        envelope["input_hashes"]["mode_context"] = pair["experience_sha256"]
    write_json(output / "arm.json", envelope)
    shutil.copyfile(HERE / "arm_worker.py", output / "arm_worker.py")
    shutil.copyfile(SCHEMAS / "agent-result.schema.json", output / "agent-result.schema.json")
    audit_bundle(manifest, pair, output)
    return envelope


def audit_bundle(manifest, pair, bundle):
    actual = {path.name for path in bundle.iterdir()}
    if actual != EXPECTED_BUNDLE_ENTRIES:
        raise ProtocolError(f"bundle entries differ from allowlist: {sorted(actual ^ EXPECTED_BUNDLE_ENTRIES)}")
    envelope = load_json(bundle / "arm.json")
    forbidden_keys = {"source", "transfer", "fixed_commit", "human_patch", "hidden_tests", "evaluator", "historical_failure_paths"}
    leaked_keys = forbidden_keys.intersection(walk_keys(envelope))
    if leaked_keys:
        raise ProtocolError(f"bundle exposes controller/evaluator keys: {sorted(leaked_keys)}")
    if envelope["mode"] == "control" and ("experience" in envelope or "experience_id" in envelope):
        raise ProtocolError("control bundle contains experience data")
    if envelope["mode"] == "aeg-assisted" and set(envelope.get("experience", {})) != set(EXPERIENCE_FIELDS):
        raise ProtocolError("assisted payload differs from compact experience allowlist")
    workspace = bundle / "workspace"
    if run(["git", "remote"], cwd=workspace).stdout.strip():
        raise ProtocolError("bundle workspace has a remote")
    if run(["git", "rev-list", "--all", "--count"], cwd=workspace).stdout.strip() != "1":
        raise ProtocolError("bundle workspace does not have exactly one commit")
    exposed_text = [(bundle / "arm.json").read_text(encoding="utf-8")]
    for path in workspace.rglob("*"):
        if path.is_file() and ".git" not in path.parts and path.stat().st_size <= 1_000_000:
            exposed_text.append(path.read_text(encoding="utf-8", errors="replace"))
    serialized = "\n".join(exposed_text)
    root = fixture_root(pair)
    transfer_patch = (root / "transfer" / "evaluator" / "human.patch").read_text(encoding="utf-8")
    hidden = (root / "transfer" / "evaluator" / "test_hidden.py").read_text(encoding="utf-8")
    forbidden_needles = [pair["transfer"]["fixed_commit"], pair["human_patch_sha256"], hidden] + patch_added_lines(transfer_patch)
    forbidden_needles.extend(other["pair_id"] for other in manifest["pairs"] if other["pair_id"] != pair["pair_id"])
    for needle in forbidden_needles:
        if needle and needle in serialized:
            raise ProtocolError(f"bundle leaks evaluator or other-pair material: {needle[:60]!r}")
    for forbidden_name in ("human.patch", "test_hidden.py", "evaluator.json", "prior-arm.patch", "prior-arm.log"):
        if any(path.name == forbidden_name for path in workspace.rglob("*")):
            raise ProtocolError(f"bundle workspace exposes {forbidden_name}")
    return {"arm_id": envelope["arm_id"], "status": "passed"}


def preflight():
    summary = validate()
    manifest = load_json(MANIFEST)
    fixtures = {}
    packaged = []
    for pair in manifest["pairs"]:
        fixtures[pair["pair_id"]] = {
            "source": preflight_fixture(pair, "source"),
            "transfer": preflight_fixture(pair, "transfer"),
        }
    with tempfile.TemporaryDirectory(prefix="seb-package-preflight-") as raw:
        root = Path(raw)
        for pair in manifest["pairs"]:
            for replicate in (1, 2, 3):
                for mode in MODES:
                    output = root / arm_id(pair["pair_id"], replicate, mode)
                    envelope = package_arm(manifest, pair, replicate, mode, output)
                    packaged.append(envelope["arm_id"])
    summary.update({
        "fixture_preflights": 4,
        "human_patches_verified": 4,
        "arm_bundles_audited": len(packaged),
        "checks": ["buggy-reason", "human-fix", "fixture-hash", "one-commit-arm", "control-separation", "experience-allowlist", "transfer-patch-leakage", "hidden-evaluator-access", "cross-pair-access"],
        "status": "ready-no-arms-executed",
    })
    return summary


def schedule_s1(output):
    manifest = load_json(MANIFEST)
    validate()
    if output.exists():
        raise ProtocolError(f"output already exists: {output}")
    output.mkdir(parents=True)
    arms = []
    for pair in manifest["pairs"]:
        for replicate, order in enumerate(manifest["protocol"]["arm_orders"][pair["pair_id"]], 1):
            for mode in order:
                target = output / "arms" / arm_id(pair["pair_id"], replicate, mode)
                envelope = package_arm(manifest, pair, replicate, mode, target)
                arms.append({"arm_id": envelope["arm_id"], "relative_bundle": str(target.relative_to(output)), "mode": mode})
    plan = {
        "benchmark_id": manifest["benchmark_id"],
        "family": "S1",
        "manifest_sha256": sha256_file(MANIFEST),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "arm_count": len(arms),
        "arms": arms,
        "execution_requirement": "Copy exactly one relative_bundle to each fresh disposable runner, set SEB_DISPOSABLE_RUNNER=1, run arm_worker.py execute with the envelope mode, and return artifacts only after the process exits.",
    }
    write_json(output / "execution-plan.json", plan)
    return plan


def evaluate_arm(pair, replicate, mode, arm_output, destination):
    manifest = load_json(MANIFEST)
    validate()
    record = load_json(arm_output / "arm-result.json")
    if (record.get("pair_id"), record.get("replicate"), record.get("mode")) != (pair["pair_id"], replicate, mode):
        raise ProtocolError("arm result coordinate differs from evaluator request")
    patch = (arm_output / "patch.diff").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="seb-hidden-evaluator-") as raw:
        workspace = Path(raw) / "workspace"
        shutil.copytree(fixture_root(pair) / "transfer" / "agent", workspace)
        git_init(workspace)
        applied = run(["git", "apply", "--whitespace=nowarn", "-"], cwd=workspace, input_text=patch)
        if applied.returncode:
            public = {"passed": False, "command": pair["public_test_command"]}
            hidden = {"passed": False, "command": pair["hidden_test_command"]}
            changed = []
            findings = ["agent patch did not apply to the frozen seed"]
        else:
            changed = run(["git", "diff", "--name-only"], cwd=workspace).stdout.splitlines()
            protected = any(path == "ISSUE.md" or path.startswith("test") or "/test" in path for path in changed)
            public = run_test(pair["public_test_command"], workspace)
            shutil.copyfile(fixture_root(pair) / "transfer" / "evaluator" / "test_hidden.py", workspace / "test_hidden.py")
            hidden = run_test(pair["hidden_test_command"], workspace)
            findings = [
                f"focused suite {'passed' if public['passed'] else 'failed'}",
                f"hidden regression suite {'passed' if hidden['passed'] else 'failed'}",
                f"protected inputs {'changed' if protected else 'unchanged'}",
            ]
        evidence = patch + "\n" + (arm_output / "events.jsonl").read_text(encoding="utf-8", errors="replace")
        repeated = [item["id"] for item in pair["historical_failure_paths"] if re.search(item["pattern"], evidence, re.IGNORECASE | re.DOTALL)]
        protected_changed = any(path == "ISSUE.md" or path.startswith("test") or "/test" in path for path in changed)
        record["evaluation_status"] = "evaluated"
        record["regression_free_success"] = bool(public["passed"] and hidden["passed"] and not protected_changed)
        record["tests_run"].extend([
            {"command": pair["public_test_command"], "scope": "evaluator", "passed": bool(public["passed"])},
            {"command": pair["hidden_test_command"], "scope": "hidden", "passed": bool(hidden["passed"])},
        ])
        record["failed_historical_paths_repeated"] = repeated
        reported_assumptions = {
            item.get("assumption"): item
            for item in record.get("environment_assumptions_checked", [])
            if isinstance(item, dict) and item.get("assumption")
        }
        record["environment_assumptions_checked"] = [
            reported_assumptions.get(
                assumption,
                {"assumption": assumption, "checked": False, "evidence": "not reported by the agent"},
            )
            for assumption in pair["environment_assumptions"]
        ]
        record["evaluator_findings"] = findings
    schema_validate(record, "arm-result.schema.json", "evaluated arm result")
    write_json(destination, record)
    return record


def compare_pair(control_path, treatment_path, output):
    control = load_json(control_path)
    treatment = load_json(treatment_path)
    if control["evaluation_status"] != "evaluated" or treatment["evaluation_status"] != "evaluated":
        raise ProtocolError("pair comparison requires two evaluated arms")
    if (control["pair_id"], control["replicate"]) != (treatment["pair_id"], treatment["replicate"]):
        raise ProtocolError("pair coordinates do not match")
    if control["mode"] != "control" or treatment["mode"] != "aeg-assisted":
        raise ProtocolError("pair modes are invalid")
    thresholds = load_json(MANIFEST)["protocol"]["evaluation_thresholds"]
    increase = 1 + thresholds["effort_change_fraction"]
    measures = [
        (control["attempts"], treatment["attempts"]),
        (control["completed_commands"], treatment["completed_commands"]),
        (len(control["tests_run"]), len(treatment["tests_run"])),
        (control["patch_size"]["added_lines"] + control["patch_size"]["deleted_lines"], treatment["patch_size"]["added_lines"] + treatment["patch_size"]["deleted_lines"]),
    ]
    control_tokens = control["tokens"]["input"] + control["tokens"]["output"] if control["tokens"]["input"] is not None and control["tokens"]["output"] is not None else None
    treatment_tokens = treatment["tokens"]["input"] + treatment["tokens"]["output"] if treatment["tokens"]["input"] is not None and treatment["tokens"]["output"] is not None else None
    if control_tokens is not None and treatment_tokens is not None:
        measures.append((control_tokens, treatment_tokens))
    losses = sum(new > base * increase for base, new in measures if base > 0)
    success_loss = control["regression_free_success"] and not treatment["regression_free_success"]
    negative = bool(success_loss or (losses >= thresholds["negative_transfer_effort_measure_count"] and treatment["regression_free_success"] == control["regression_free_success"]))
    control["negative_transfer"] = False
    treatment["negative_transfer"] = negative
    report = {
        "pair_id": control["pair_id"],
        "replicate": control["replicate"],
        "control": control,
        "treatment": treatment,
        "negative_transfer": negative,
        "stop_condition_triggered": "treatment_causes_additional_regressions" if success_loss else None,
    }
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("validate")
    sub.add_parser("preflight")
    package = sub.add_parser("package-arm")
    package.add_argument("--pair", required=True)
    package.add_argument("--replicate", type=int, required=True)
    package.add_argument("--mode", choices=MODES, required=True)
    package.add_argument("--output", required=True)
    schedule = sub.add_parser("schedule-s1")
    schedule.add_argument("--output", required=True)
    evaluate = sub.add_parser("evaluate-arm")
    evaluate.add_argument("--pair", required=True)
    evaluate.add_argument("--replicate", type=int, required=True)
    evaluate.add_argument("--mode", choices=MODES, required=True)
    evaluate.add_argument("--arm-output", required=True)
    evaluate.add_argument("--output", required=True)
    compare = sub.add_parser("compare-pair")
    compare.add_argument("--control", required=True)
    compare.add_argument("--treatment", required=True)
    compare.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.action == "validate":
        result = validate()
    elif args.action == "preflight":
        result = preflight()
    elif args.action == "schedule-s1":
        result = schedule_s1(Path(args.output).resolve())
    elif args.action == "compare-pair":
        result = compare_pair(Path(args.control), Path(args.treatment), Path(args.output))
    else:
        manifest = load_json(MANIFEST)
        pair = find_pair(manifest, args.pair)
        if args.action == "package-arm":
            validate()
            result = package_arm(manifest, pair, args.replicate, args.mode, Path(args.output).resolve())
        else:
            result = evaluate_arm(pair, args.replicate, args.mode, Path(args.arm_output).resolve(), Path(args.output).resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProtocolError, subprocess.TimeoutExpired, json.JSONDecodeError, re.error) as error:
        print(f"situated benchmark protocol error: {error}", file=sys.stderr)
        raise SystemExit(2)
