#!/usr/bin/env python3
"""Prepare, run, and evaluate the frozen AEG natural-transfer benchmark."""

import argparse
import collections
import hashlib
import io
import json
import os
import random
import re
import select
import shlex
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "manifest.json"
RESULT_SCHEMA = HERE / "result.schema.json"
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".aeg-isolated"}
ARMS = ("control", "treatment")
CAPSULE_KEYS = (
    "applicableContext",
    "failedApproach",
    "recoveryPrinciple",
    "validatedOutcome",
    "uncertaintyAndApplicability",
)


class ProtocolError(RuntimeError):
    """Raised when a frozen benchmark invariant is violated."""


def command(args, cwd=None, env=None, timeout=120, input_bytes=None, binary=False):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_bytes,
        capture_output=True,
        timeout=timeout,
        check=False,
        text=not binary and input_bytes is None,
    )


def load_manifest(path=DEFAULT_MANIFEST):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value):
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def gate_decision(manifest, task):
    gate = task["gate"]
    thresholds = manifest["retrievalGate"]
    return (
        "inject"
        if gate["relevance"] >= thresholds["relevanceThreshold"]
        and gate["expectedUtility"] >= thresholds["expectedUtilityThreshold"]
        else "abstain"
    )


def expected_orders(manifest):
    rng = random.Random(manifest["protocol"]["randomizationSeed"])
    return [
        ["control", "treatment"] if rng.randrange(2) == 0 else ["treatment", "control"]
        for _ in range(len(manifest["tasks"]) * manifest["protocol"]["replicatesPerArm"])
    ]


def validate_manifest(manifest):
    errors = []
    if manifest.get("status") != "frozen-before-execution":
        errors.append("manifest status must be frozen-before-execution")
    tasks = manifest.get("tasks", [])
    if len(tasks) != 5:
        errors.append("exactly five tasks are required")
    if manifest.get("protocol", {}).get("replicatesPerArm") != 3:
        errors.append("exactly three replicates per arm are required")
    if manifest.get("protocol", {}).get("arms") != list(ARMS):
        errors.append("arms must be control then treatment")
    frozen_orders = [order for task in tasks for order in task.get("orders", [])]
    if frozen_orders != expected_orders(manifest):
        errors.append("stored arm orders do not match the frozen randomization seed")
    seen_transfer = set()
    injected = 0
    abstained = 0
    for task in tasks:
        label = task.get("id", "<missing-id>")
        for field in ("source", "transfer", "experience", "gate", "orders", "taskPrompt"):
            if field not in task:
                errors.append(f"{label}: missing {field}")
        if any(not task.get("experience", {}).get(key) for key in CAPSULE_KEYS):
            errors.append(f"{label}: experience capsule is incomplete")
        source = task.get("source", {})
        transfer = task.get("transfer", {})
        try:
            if parse_time(source["fixedAt"]) >= parse_time(transfer["fixedAt"]):
                errors.append(f"{label}: source fix must predate transfer fix")
        except (KeyError, ValueError):
            errors.append(f"{label}: invalid source/transfer timestamp")
        key = (task.get("repository"), transfer.get("buggyCommit"), transfer.get("fixedCommit"))
        if key in seen_transfer:
            errors.append(f"{label}: duplicate transfer bug")
        seen_transfer.add(key)
        if source.get("patchSha256") == transfer.get("humanPatchSha256"):
            errors.append(f"{label}: source and transfer patch hashes must differ")
        decision = gate_decision(manifest, task)
        if task.get("gate", {}).get("decision") != decision:
            errors.append(f"{label}: stored gate decision disagrees with thresholds")
        injected += decision == "inject"
        abstained += decision == "abstain"
        if len(task.get("orders", [])) != 3 or any(sorted(order) != sorted(ARMS) for order in task.get("orders", [])):
            errors.append(f"{label}: invalid replicate arm order")
        if not transfer.get("testFiles") or not transfer.get("focusedCommand") or not transfer.get("regressionCommand"):
            errors.append(f"{label}: transfer oracle is incomplete")
        for failure in task.get("knownFailurePaths", []):
            if not failure.get("label") or not failure.get("pattern"):
                errors.append(f"{label}: known failure detector is incomplete")
            else:
                try:
                    re.compile(failure["pattern"], re.IGNORECASE | re.DOTALL)
                except re.error as error:
                    errors.append(f"{label}: invalid known failure regex: {error}")
    if injected < 2:
        errors.append("at least two tasks must pass the retrieval gate")
    if abstained < 1:
        errors.append("at least one pre-registered abstention is required")
    if errors:
        raise ProtocolError("\n".join(errors))
    return {
        "benchmarkId": manifest["benchmarkId"],
        "manifestSha256": canonical_sha256(manifest),
        "tasks": len(tasks),
        "injected": injected,
        "abstained": abstained,
        "replicatesPerArm": 3,
    }


def render_capsule(task):
    exp = task["experience"]
    return "\n".join(
        [
            "AEG_RETRIEVAL_CONTEXT (not part of the task specification)",
            f"applicable_context: {exp['applicableContext']}",
            f"failed_approach: {exp['failedApproach']}",
            f"recovery_principle: {exp['recoveryPrinciple']}",
            f"validated_outcome: {exp['validatedOutcome']}",
            f"uncertainty_and_applicability: {exp['uncertaintyAndApplicability']}",
        ]
    )


def arm_prompt(manifest, task, arm):
    shared = task["taskPrompt"] + (
        "\n\nBefore the first edit, state the first production location and approach in the final structured fields. "
        "Run the focused test before editing. Record AEG usage accurately."
    )
    if arm == "treatment" and gate_decision(manifest, task) == "inject":
        return shared + "\n\n" + render_capsule(task)
    return shared


def copy_commit_tree(mirror, commit_id, destination):
    archived = command(["git", "archive", "--format=tar", commit_id], cwd=mirror, timeout=300, binary=True)
    if archived.returncode:
        raise ProtocolError(f"cannot archive {commit_id}: {archived.stderr.decode(errors='replace')}")
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        members = archive.getmembers()
        if any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
            raise ProtocolError("unsafe path in git archive")
        archive.extractall(destination, members=members)


def git_file(mirror, commit_id, path):
    result = command(["git", "show", f"{commit_id}:{path}"], cwd=mirror, timeout=120, binary=True)
    if result.returncode:
        raise ProtocolError(f"cannot read {path} at {commit_id}: {result.stderr.decode(errors='replace')}")
    return result.stdout


def init_seed_git(seed):
    steps = [
        ["git", "init", "-q"],
        ["git", "add", "."],
        [
            "git",
            "-c",
            "user.name=AEG Benchmark",
            "-c",
            "user.email=aeg-benchmark@example.invalid",
            "commit",
            "-qm",
            "frozen buggy benchmark seed",
        ],
    ]
    for step in steps:
        result = command(step, cwd=seed)
        if result.returncode:
            raise ProtocolError(result.stderr)


def iter_tree_files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
            yield path


def tree_sha256(root):
    digest = hashlib.sha256()
    for path in iter_tree_files(root):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def assert_blind_workspace(manifest, task, workspace):
    forbidden = [
        task["transfer"]["fixedCommit"],
        manifest["benchmarkId"],
        "human.patch",
        "evaluator.json",
        "AEG_RETRIEVAL_CONTEXT",
    ] + [task["experience"][key] for key in CAPSULE_KEYS]
    for path in iter_tree_files(workspace):
        if path.stat().st_size > 2_000_000:
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for needle in forbidden:
            if needle and needle in text:
                raise ProtocolError(f"blindness violation: {needle[:40]!r} found in {path}")
    remotes = command(["git", "remote"], cwd=workspace)
    if remotes.stdout.strip():
        raise ProtocolError("blindness violation: arm workspace has a Git remote")
    revs = command(["git", "rev-list", "--all", "--count"], cwd=workspace)
    if revs.returncode or revs.stdout.strip() != "1":
        raise ProtocolError("blindness violation: arm workspace must have one commit")


def parse_mapping(values, label):
    output = {}
    for value in values:
        if "=" not in value:
            raise ProtocolError(f"{label} must use NAME=/absolute/path")
        name, raw_path = value.split("=", 1)
        path = Path(raw_path).resolve()
        if not path.exists():
            raise ProtocolError(f"{label} path does not exist: {path}")
        output[name] = path
    return output


def prepare_seed(manifest, task, mirror, seeds_root, check_oracle=True, env=None):
    seed = seeds_root / task["id"]
    copy_commit_tree(mirror, task["transfer"]["buggyCommit"], seed)
    for relative in task["transfer"]["testFiles"]:
        target = seed / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_file(mirror, task["transfer"]["fixedCommit"], relative))
    init_seed_git(seed)
    assert_blind_workspace(manifest, task, seed)
    seed_hash = tree_sha256(seed)
    expected_hash = task["transfer"].get("expectedSeedTreeSha256")
    if expected_hash and seed_hash != expected_hash:
        raise ProtocolError(f"{task['id']}: prepared seed hash differs from frozen manifest")
    initial = None
    if check_oracle:
        initial = execute_test(task["transfer"]["focusedCommand"], seed, env, timeout=300)
        if initial["passed"]:
            raise ProtocolError(f"{task['id']}: buggy seed unexpectedly passes focused regression")
    return {"path": str(seed), "treeSha256": seed_hash, "initialFocused": initial}


def isolated_env(base_env, state_dir, python_env=None):
    env = dict(base_env)
    state_dir.mkdir(parents=True, exist_ok=False)
    for name in ("cache", "bytecode", "tmp"):
        (state_dir / name).mkdir()
    env.update(
        {
            "XDG_CACHE_HOME": str(state_dir / "cache"),
            "PIP_CACHE_DIR": str(state_dir / "cache" / "pip"),
            "PYTHONPYCACHEPREFIX": str(state_dir / "bytecode"),
            "TMPDIR": str(state_dir / "tmp"),
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
            "AEG_BENCHMARK_ARM_STATE": str(state_dir),
        }
    )
    if python_env:
        env["PATH"] = str(python_env / "bin") + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(python_env)
    return env


def execute_test(command_text, cwd, env, timeout=300):
    started = time.monotonic()
    result = command(shlex.split(command_text), cwd=cwd, env=env, timeout=timeout)
    return {
        "command": command_text,
        "passed": result.returncode == 0,
        "exitCode": result.returncode,
        "durationMs": round((time.monotonic() - started) * 1000),
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def parse_events(path):
    events = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def shell_body(value):
    try:
        parts = shlex.split(value)
    except ValueError:
        return value
    for index, item in enumerate(parts[:-1]):
        if item in ("-c", "-lc"):
            return parts[index + 1]
    return value


def count_tests(commands, focused, regression):
    targets = (shlex.split(focused), shlex.split(regression))
    count = 0
    for value in commands:
        for segment in re.split(r"\s*(?:&&|\|\||;)\s*", shell_body(value)):
            try:
                tokens = shlex.split(segment)
            except ValueError:
                continue
            if any(tokens[: len(target)] == target for target in targets):
                count += 1
    return count


def event_metrics(events, task, known_files):
    commands = []
    messages = []
    attempts = []
    usage = {}
    inspected = set()
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage", usage)
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and item.get("text"):
            messages.append(item["text"])
        elif item.get("type") == "command_execution" and item.get("command"):
            value = item["command"]
            commands.append(value)
            for relative in known_files:
                if relative in value:
                    inspected.add(relative)
        elif item.get("type") == "file_change":
            changed = sorted(change.get("path", "") for change in item.get("changes", []) if change.get("path"))
            attempts.append(changed)
    input_tokens = usage.get("input_tokens", 0) or 0
    cached = usage.get("cached_input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    return {
        "commands": commands,
        "commandCount": len(commands),
        "testExecutions": count_tests(commands, task["transfer"]["focusedCommand"], task["transfer"]["regressionCommand"]),
        "filesInspected": sorted(inspected),
        "filesInspectedCount": len(inspected),
        "attempts": len(attempts),
        "attemptPaths": attempts,
        "messages": messages,
        "usage": usage,
        "nonCachedInputTokens": max(0, input_tokens - cached),
        "nonCachedTotalTokens": max(0, input_tokens - cached) + output_tokens,
    }


def diff_text(workspace):
    result = command(["git", "diff", "--binary", "--", "."], cwd=workspace)
    if result.returncode:
        raise ProtocolError(result.stderr)
    return result.stdout


def read_structured_result(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def detect_known_failure_paths(task, evidence):
    entered = []
    for failure in task["knownFailurePaths"]:
        if re.search(failure["pattern"], evidence, re.IGNORECASE | re.DOTALL):
            entered.append(failure["label"])
    return entered


def diff_stats(diff):
    added = deleted = 0
    files = []
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            files.append(line.split(" b/", 1)[1])
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return {"addedLines": added, "deletedLines": deleted, "filesChanged": sorted(set(files))}


def diff_features(diff):
    stats = diff_stats(diff)
    tokens = set()
    symbols = set()
    for line in diff.splitlines():
        if (line.startswith("+") and not line.startswith("+++")) or (line.startswith("-") and not line.startswith("---")):
            tokens.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line[1:].lower()))
        elif line.startswith("@@"):
            symbols.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line.split("@@")[-1].lower()))
    return {"files": set(stats["filesChanged"]), "tokens": tokens, "symbols": symbols}


def jaccard(left, right):
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right) if left | right else 0.0


def semantic_similarity(agent_diff, human_diff):
    agent = diff_features(agent_diff)
    human = diff_features(human_diff)
    components = {
        "changedFileJaccard": jaccard(agent["files"], human["files"]),
        "normalizedTokenJaccard": jaccard(agent["tokens"], human["tokens"]),
        "changedSymbolJaccard": jaccard(agent["symbols"], human["symbols"]),
    }
    components["weightedScore"] = round(
        components["changedFileJaccard"] * 0.5
        + components["normalizedTokenJaccard"] * 0.3
        + components["changedSymbolJaccard"] * 0.2,
        4,
    )
    return components


def human_production_diff(task, mirror):
    args = ["git", "diff", "--binary", task["transfer"]["buggyCommit"], task["transfer"]["fixedCommit"], "--", "."]
    for path in task["transfer"]["testFiles"]:
        args.append(f":(exclude){path}")
    result = command(args, cwd=mirror, timeout=300)
    if result.returncode:
        raise ProtocolError(result.stderr)
    return result.stdout


def evaluate_patch(task, workspace, seed, patch, env, human_diff, snapshot=False):
    stats = diff_stats(patch)
    test_changed = any(path in set(task["transfer"]["testFiles"]) for path in stats["filesChanged"])
    target = workspace
    temporary = None
    if snapshot:
        temporary = Path(tempfile.mkdtemp(prefix="aeg-evaluate-"))
        target = temporary / "workspace"
        shutil.copytree(seed, target)
        applied = command(["git", "apply", "--whitespace=nowarn", "-"], cwd=target, input_bytes=patch.encode())
        if applied.returncode:
            shutil.rmtree(temporary)
            return {"applicable": False, "focused": {"passed": False}, "testChanged": test_changed}
    focused = execute_test(task["transfer"]["focusedCommand"], target, env)
    regression = execute_test(task["transfer"]["regressionCommand"], target, env) if focused["passed"] else {"passed": False, "skipped": True}
    changed_python = [path for path in stats["filesChanged"] if path.endswith(".py") and (target / path).exists()]
    syntax = {"passed": True, "files": changed_python}
    if changed_python:
        compiled = command(["python", "-m", "py_compile", *changed_python], cwd=target, env=env)
        syntax = {"passed": compiled.returncode == 0, "files": changed_python, "stderr": compiled.stderr[-2000:]}
    human_churn = max(1, diff_stats(human_diff)["addedLines"] + diff_stats(human_diff)["deletedLines"])
    agent_churn = stats["addedLines"] + stats["deletedLines"]
    maintainability = {
        "testsUnchanged": not test_changed,
        "syntax": syntax,
        "noGeneratedOrBinaryFiles": not any(path.endswith((".pyc", ".so", ".zip", ".png")) for path in stats["filesChanged"]),
        "patchChurnRatioToHuman": round(agent_churn / human_churn, 3),
        "churnWithinLimit": agent_churn <= human_churn * 2.5,
    }
    if temporary:
        shutil.rmtree(temporary)
    return {
        "applicable": True,
        "focused": focused,
        "regression": regression,
        "testChanged": test_changed,
        "finalSuccess": focused["passed"] and regression["passed"] and not test_changed,
        "stats": stats,
        "semanticSimilarity": semantic_similarity(patch, human_diff),
        "maintainability": maintainability,
    }


def execute_arm(manifest, task, arm, workspace, state_dir, codex, model, env, seed, human_diff, timeout):
    assert_blind_workspace(manifest, task, workspace)
    raw_dir = state_dir / "raw"
    raw_dir.mkdir()
    events_path = raw_dir / "events.jsonl"
    stderr_path = raw_dir / "stderr.log"
    result_path = raw_dir / "result.json"
    known_files = [path.relative_to(workspace).as_posix() for path in iter_tree_files(workspace)]
    prompt = arm_prompt(manifest, task, arm)
    cmd = [
        str(codex),
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--model",
        model,
        "--sandbox",
        "workspace-write",
        "--json",
        "--output-schema",
        str(RESULT_SCHEMA),
        "-o",
        str(result_path),
        prompt,
    ]
    snapshots = []
    started = time.monotonic()
    with events_path.open("w", encoding="utf-8") as event_stream, stderr_path.open("w", encoding="utf-8") as error_stream:
        process = subprocess.Popen(cmd, cwd=workspace, env=env, stdout=subprocess.PIPE, stderr=error_stream, text=True, bufsize=1)
        assert process.stdout is not None
        try:
            while process.poll() is None:
                if time.monotonic() - started >= timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    continue
                line = process.stdout.readline()
                if not line:
                    continue
                event_stream.write(line)
                event_stream.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                item = event.get("item") or {}
                if event.get("type") == "item.completed" and item.get("type") == "file_change":
                    snapshot = diff_text(workspace)
                    if snapshot and (not snapshots or snapshots[-1] != snapshot):
                        snapshots.append(snapshot)
            for line in process.stdout:
                event_stream.write(line)
            process.wait(timeout=max(1, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    duration_ms = round((time.monotonic() - started) * 1000)
    final_patch = diff_text(workspace)
    events = event_metrics(parse_events(events_path), task, known_files)
    structured = read_structured_result(result_path)
    failure_evidence = "\n".join(
        [
            structured.get("first_repair_location", ""),
            structured.get("proposed_approach", ""),
            snapshots[0] if snapshots else final_patch,
        ]
    )
    events["knownFailurePathsEntered"] = detect_known_failure_paths(task, failure_evidence)
    first_eval = evaluate_patch(task, workspace, seed, snapshots[0], env, human_diff, snapshot=True) if snapshots else {"focused": {"passed": False}}
    final_eval = evaluate_patch(task, workspace, seed, final_patch, env, human_diff)
    return {
        "arm": arm,
        "gateDecision": gate_decision(manifest, task) if arm == "treatment" else "disabled",
        "experienceInjected": arm == "treatment" and gate_decision(manifest, task) == "inject",
        "codexExitCode": process.returncode,
        "durationMs": duration_ms,
        "firstRepairLocation": structured.get("first_repair_location", ""),
        "proposedApproach": structured.get("proposed_approach", ""),
        "passAt1": bool(first_eval.get("focused", {}).get("passed") and not first_eval.get("testChanged", False)),
        "finalSuccess": bool(final_eval.get("finalSuccess")),
        "events": events,
        "patch": {
            **final_eval.get("stats", diff_stats(final_patch)),
            "sha256": sha256_bytes(final_patch.encode()),
            "exactHumanPatchEquivalent": final_patch == human_diff,
            "semanticSimilarity": final_eval.get("semanticSimilarity", semantic_similarity(final_patch, human_diff)),
        },
        "focusedRegression": final_eval.get("focused", {}),
        "broaderRegression": final_eval.get("regression", {}),
        "maintainability": final_eval.get("maintainability", {}),
        "snapshotCount": len(snapshots),
    }


def material_increase(new, old, fraction):
    return new > old * (1 + fraction) if old else new > 0


def classify_pair(manifest, control, treatment):
    materiality = manifest["protocol"]["materiality"]
    if treatment["finalSuccess"] and not control["finalSuccess"]:
        return "helped"
    if control["finalSuccess"] and not treatment["finalSuccess"]:
        return "negative-transfer"
    measures = (
        ("attempts", control["events"]["attempts"], treatment["events"]["attempts"]),
        ("commands", control["events"]["commandCount"], treatment["events"]["commandCount"]),
        ("tests", control["events"]["testExecutions"], treatment["events"]["testExecutions"]),
        ("tokens", control["events"]["nonCachedTotalTokens"], treatment["events"]["nonCachedTotalTokens"]),
    )
    effort = materiality["effortReductionFraction"]
    wins = [name for name, base, new in measures if base and new <= base * (1 - effort)]
    losses = [name for name, base, new in measures if material_increase(new, base, effort)]
    complexity_bad = material_increase(
        treatment["patch"]["addedLines"] + treatment["patch"]["deletedLines"],
        control["patch"]["addedLines"] + control["patch"]["deletedLines"],
        materiality["patchComplexityIncreaseFraction"],
    )
    regression_bad = control["broaderRegression"].get("passed") and not treatment["broaderRegression"].get("passed")
    if treatment["finalSuccess"] == control["finalSuccess"] and len(wins) >= 2 and not complexity_bad and not regression_bad:
        return "helped"
    if treatment["finalSuccess"] == control["finalSuccess"] and len(losses) >= 2 and not treatment["passAt1"] > control["passAt1"]:
        return "negative-transfer"
    return "no-effect"


def median(values):
    return round(statistics.median(values), 2) if values else None


def aggregate_report(manifest, task_results):
    per_task = []
    for task in manifest["tasks"]:
        rows = [row for row in task_results if row["taskId"] == task["id"]]
        summary = {"taskId": task["id"], "gateDecision": task["gate"]["decision"], "arms": {}, "effects": collections.Counter(row["effect"] for row in rows)}
        for arm in ARMS:
            arms = [row["arms"][arm] for row in rows]
            summary["arms"][arm] = {
                "passAt1Rate": sum(item["passAt1"] for item in arms) / len(arms),
                "finalSuccessRate": sum(item["finalSuccess"] for item in arms) / len(arms),
                "medianAttempts": median([item["events"]["attempts"] for item in arms]),
                "medianCommands": median([item["events"]["commandCount"] for item in arms]),
                "medianTests": median([item["events"]["testExecutions"] for item in arms]),
                "medianNonCachedTokens": median([item["events"]["nonCachedTotalTokens"] for item in arms]),
                "medianPatchChurn": median([item["patch"]["addedLines"] + item["patch"]["deletedLines"] for item in arms]),
                "medianSemanticSimilarity": median([item["patch"]["semanticSimilarity"]["weightedScore"] for item in arms]),
            }
        summary["effects"] = dict(summary["effects"])
        per_task.append(summary)
    injected = [task for task in per_task if task["gateDecision"] == "inject"]
    helped_tasks = sum(task["effects"].get("helped", 0) > task["effects"].get("negative-transfer", 0) for task in injected)
    negative_tasks = sum(task["effects"].get("negative-transfer", 0) > task["effects"].get("helped", 0) for task in injected)
    macro = {"arms": {}}
    for arm in ARMS:
        macro["arms"][arm] = {
            key: median([task["arms"][arm][key] for task in per_task])
            for key in (
                "passAt1Rate",
                "finalSuccessRate",
                "medianAttempts",
                "medianCommands",
                "medianTests",
                "medianNonCachedTokens",
                "medianPatchChurn",
                "medianSemanticSimilarity",
            )
        }
    token_base = macro["arms"]["control"]["medianNonCachedTokens"] or 0
    token_new = macro["arms"]["treatment"]["medianNonCachedTokens"] or 0
    positive = helped_tasks >= 2 and negative_tasks == 0 and not material_increase(
        token_new, token_base, manifest["protocol"]["materiality"]["tokenCostIncreaseFraction"]
    )
    macro["verdict"] = "positive" if positive else "not-positive"
    macro["helpedInjectedTasks"] = helped_tasks
    macro["negativeTransferInjectedTasks"] = negative_tasks
    macro["wallClockExcludedFromBenefitRule"] = True
    return {"perTask": per_task, "macro": macro}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_protocol(args, manifest):
    mirrors = parse_mapping(args.mirror, "--mirror")
    python_envs = parse_mapping(args.python_env, "--python-env") if args.python_env else {}
    missing = sorted({task["project"] for task in manifest["tasks"]} - set(mirrors))
    if missing:
        raise ProtocolError(f"missing mirrors: {', '.join(missing)}")
    codex = Path(args.codex or shutil.which("codex") or "")
    if not codex.exists():
        raise ProtocolError("Codex executable not found")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    controller = output / "controller"
    seeds = output / "seeds"
    arms_root = output / "arms"
    states = output / "arm-state"
    for directory in (controller, seeds, arms_root, states):
        directory.mkdir()
    write_json(controller / "manifest.snapshot.json", manifest)
    preparation = {}
    for task in manifest["tasks"]:
        project = task["project"]
        env = isolated_env(os.environ, states / f"prepare-{task['id']}", python_envs.get(project))
        preparation[task["id"]] = prepare_seed(manifest, task, mirrors[project], seeds, check_oracle=not args.skip_initial_oracle, env=env)
    write_json(controller / "preparation.json", preparation)
    if args.prepare_only:
        print(output)
        return 0
    results = []
    for task in manifest["tasks"]:
        seed = seeds / task["id"]
        human_diff = human_production_diff(task, mirrors[task["project"]])
        write_json(controller / "human-patch-hashes" / f"{task['id']}.json", {"sha256": sha256_bytes(human_diff.encode())})
        for replicate, order in enumerate(task["orders"], 1):
            pair_dir = arms_root / task["id"] / f"replicate-{replicate:02d}"
            pair_dir.mkdir(parents=True)
            workspaces = {}
            envs = {}
            for arm in ARMS:
                workspace = pair_dir / arm
                shutil.copytree(seed, workspace)
                state = states / task["id"] / f"replicate-{replicate:02d}" / arm
                envs[arm] = isolated_env(os.environ, state, python_envs.get(task["project"]))
                assert_blind_workspace(manifest, task, workspace)
                if tree_sha256(workspace) != preparation[task["id"]]["treeSha256"]:
                    raise ProtocolError("arm seed hashes differ")
                workspaces[arm] = workspace
            raw_arms = {}
            for arm in order:
                raw_arms[arm] = execute_arm(
                    manifest,
                    task,
                    arm,
                    workspaces[arm],
                    Path(envs[arm]["AEG_BENCHMARK_ARM_STATE"]),
                    codex,
                    args.model or manifest["protocol"]["model"],
                    envs[arm],
                    seed,
                    human_diff,
                    manifest["protocol"]["perArmTimeoutSeconds"],
                )
            pair = {
                "taskId": task["id"],
                "replicate": replicate,
                "executionOrder": order,
                "initialTreeSha256": preparation[task["id"]]["treeSha256"],
                "arms": raw_arms,
                "effect": classify_pair(manifest, raw_arms["control"], raw_arms["treatment"]),
            }
            results.append(pair)
            write_json(controller / "pair-results" / f"{task['id']}-{replicate:02d}.json", pair)
    report = {
        "benchmarkId": manifest["benchmarkId"],
        "manifestSha256": canonical_sha256(manifest),
        "completedAt": datetime.now().astimezone().isoformat(),
        "model": args.model or manifest["protocol"]["model"],
        "pairs": results,
        "aggregate": aggregate_report(manifest, results),
    }
    write_json(controller / "report.json", report)
    print(controller / "report.json")
    return 0


def self_test(manifest):
    validate_manifest(manifest)
    with tempfile.TemporaryDirectory(prefix="aeg-natural-transfer-selftest-") as raw:
        root = Path(raw)
        seed = root / "seed"
        seed.mkdir()
        (seed / "bug.py").write_text("def value():\n    return 1\n", encoding="utf-8")
        init_seed_git(seed)
        task = manifest["tasks"][0]
        assert_blind_workspace(manifest, task, seed)
        control = root / "control"
        treatment = root / "treatment"
        shutil.copytree(seed, control)
        shutil.copytree(seed, treatment)
        if tree_sha256(control) != tree_sha256(treatment):
            raise ProtocolError("self-test isolation hashes differ")
        human = "diff --git a/bug.py b/bug.py\n--- a/bug.py\n+++ b/bug.py\n@@ -1,2 +1,2 @@ def value\n def value():\n-    return 1\n+    return 2\n"
        equivalent = semantic_similarity(human, human)
        unrelated = semantic_similarity("", human)
        if equivalent["weightedScore"] != 1.0 or unrelated["weightedScore"] >= equivalent["weightedScore"]:
            raise ProtocolError("self-test semantic evaluator failed")
        if arm_prompt(manifest, task, "control").startswith(task["taskPrompt"]) is False:
            raise ProtocolError("self-test fixed prompt failed")
        if render_capsule(task) in arm_prompt(manifest, task, "control"):
            raise ProtocolError("self-test control contamination")
    return {"status": "passed", "checks": ["manifest", "randomization", "gate", "one-commit blindness", "tree equality", "capsule separation", "semantic evaluator"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("validate")
    sub.add_parser("self-test")
    for action in ("prepare", "run"):
        child = sub.add_parser(action)
        child.add_argument("--output", required=True)
        child.add_argument("--mirror", action="append", default=[], help="PROJECT=/absolute/upstream/mirror")
        child.add_argument("--python-env", action="append", default=[], help="PROJECT=/absolute/venv")
        child.add_argument("--codex")
        child.add_argument("--model")
        child.add_argument("--skip-initial-oracle", action="store_true", help="CI/development only; forbidden for published execution")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    validated = validate_manifest(manifest)
    if args.action == "validate":
        print(json.dumps(validated, indent=2, sort_keys=True))
        return 0
    if args.action == "self-test":
        print(json.dumps(self_test(manifest), indent=2, sort_keys=True))
        return 0
    args.prepare_only = args.action == "prepare"
    if args.action == "run" and args.skip_initial_oracle:
        raise ProtocolError("--skip-initial-oracle is forbidden for full execution")
    return run_protocol(args, manifest)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProtocolError, subprocess.TimeoutExpired) as error:
        print(f"benchmark protocol error: {error}", file=sys.stderr)
        raise SystemExit(2)
