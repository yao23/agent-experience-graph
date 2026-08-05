#!/usr/bin/env python3
"""Build and adversarially validate one-arm benchmark envelopes."""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
FROZEN_FILES = {
    "manifest.json": "46a78815b1a69f39c69a3a468ac977cc71668603ac4e856c307a7208330b95c1",
    "environment-lock.json": "283db19eeb172038b8993514ae4a08a173a8c1f22bfaebdd5bf3c9d5a5e77251",
}
FORBIDDEN_KEYS = {
    "fixedCommit",
    "humanPatchSha256",
    "source",
    "experience",
    "knownFailurePaths",
    "evaluation",
    "tasks",
}


def fail(message):
    raise SystemExit(f"isolation preflight failed: {message}")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runner_module():
    spec = importlib.util.spec_from_file_location("aeg_frozen_runner", HERE / "run_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_frozen_inputs():
    for name, expected in FROZEN_FILES.items():
        actual = digest(HERE / name)
        if actual != expected:
            fail(f"frozen input changed: {name} ({actual})")
    runner = runner_module()
    manifest = runner.load_manifest()
    runner.validate_manifest(manifest)
    return runner, manifest


def arm_id(task_id, replicate, arm):
    return f"{task_id}--r{replicate:02d}--{arm}"


def build_envelope(runner, manifest, task, replicate, arm):
    if replicate not in (1, 2, 3) or arm not in ("control", "treatment"):
        fail("invalid arm coordinate")
    envelope = {
        "schemaVersion": "1.0.0",
        "benchmarkCommit": "846d018a26d7464f4de85537e5c54fb98a09af31",
        "armId": arm_id(task["id"], replicate, arm),
        "taskId": task["id"],
        "replicate": replicate,
        "arm": arm,
        "repository": task["repository"],
        "project": task["project"],
        "buggyCommit": task["transfer"]["buggyCommit"],
        "testFiles": task["transfer"]["testFiles"],
        "focusedCommand": task["transfer"]["focusedCommand"],
        "regressionCommand": task["transfer"]["regressionCommand"],
        "fixtureFiles": task["transfer"].get("fixtureFiles", []),
        "prompt": runner.arm_prompt(manifest, task, arm),
        "gateDecision": runner.gate_decision(manifest, task) if arm == "treatment" else "disabled",
        "model": manifest["protocol"]["model"],
        "timeoutSeconds": manifest["protocol"]["perArmTimeoutSeconds"],
        "tokenBudget": manifest["protocol"]["tokenBudget"],
        "environmentLockSha256": FROZEN_FILES["environment-lock.json"],
    }
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    envelope["envelopeSha256"] = hashlib.sha256(encoded).hexdigest()
    return envelope


def package(args):
    runner, manifest = verify_frozen_inputs()
    tasks = {task["id"]: task for task in manifest["tasks"]}
    if args.task_id not in tasks:
        fail(f"unknown task {args.task_id}")
    output = Path(args.output).resolve()
    if output.exists():
        fail(f"output already exists: {output}")
    output.mkdir(parents=True)
    envelope = build_envelope(runner, manifest, tasks[args.task_id], args.replicate, args.arm)
    (output / "arm.json").write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copyfile(__file__, output / "isolation_controller.py")
    for path in output.iterdir():
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    output.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    print(envelope["armId"])


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def probe(args):
    bundle = Path(args.bundle).resolve()
    expected = {"arm.json", "isolation_controller.py"}
    actual = {path.name for path in bundle.iterdir()}
    if actual != expected:
        fail(f"arm can enumerate unexpected workspace entries: {sorted(actual - expected)}")
    envelope = json.loads((bundle / "arm.json").read_text(encoding="utf-8"))
    leaked = FORBIDDEN_KEYS.intersection(walk_keys(envelope))
    if leaked:
        fail(f"hidden controller/evaluator keys exposed: {sorted(leaked)}")
    forbidden_env = [
        name for name in os.environ
        if "TOKEN" in name or "SECRET" in name or name.startswith("GITHUB_") or name.startswith("ACTIONS_")
    ]
    if forbidden_env:
        fail(f"credential or Actions control environment exposed: {sorted(forbidden_env)}")
    roots = [
        bundle.parent,
        Path(os.environ["TMPDIR"]),
        Path(os.environ["HOME"]),
        Path(os.environ["AEG_RUNNER_TEMP_ROOT"]),
    ]
    own_arm = envelope["armId"]
    forbidden_names = {"human.patch", "evaluator.json", "manifest.json", "prior-arm.log", "prior-arm.patch"}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.name in forbidden_names or (path.name.startswith(".aeg-arm-sentinel-") and own_arm not in path.name):
                fail(f"cross-arm or evaluator artifact readable: {path}")
    cache = Path(os.environ["AEG_WRITABLE_CACHE"])
    if cache.exists():
        fail("writable cache was reused from an earlier arm")
    cache.mkdir()
    sentinel = cache / f".aeg-arm-sentinel-{own_arm}"
    sentinel.write_text(own_arm, encoding="utf-8")
    attestation = {
        "armId": own_arm,
        "status": "passed",
        "checks": [
            "single-arm-workspace",
            "no-other-arm-sentinel",
            "no-other-workspace-or-artifact",
            "no-prior-log-or-patch",
            "no-hidden-evaluator-data",
            "no-reused-writable-cache",
            "no-actions-or-github-credential",
        ],
    }
    Path(args.attestation).write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("package")
    make.add_argument("--task-id", required=True)
    make.add_argument("--replicate", required=True, type=int)
    make.add_argument("--arm", required=True)
    make.add_argument("--output", required=True)
    check = sub.add_parser("probe")
    check.add_argument("--bundle", required=True)
    check.add_argument("--attestation", required=True)
    args = parser.parse_args()
    return package(args) if args.action == "package" else probe(args)


if __name__ == "__main__":
    main()
