#!/usr/bin/env python3
"""Standalone one-arm worker for a disposable Situated Experience runner."""

import argparse
import hashlib
import json
import os
import re
import select
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


EXPECTED_TOP_LEVEL = {"agent-result.schema.json", "arm.json", "arm_worker.py", "workspace"}
SECRET_NAME = re.compile(r"(TOKEN|SECRET|PASSWORD|API_KEY|ACTIONS_|GITHUB_)", re.IGNORECASE)


class WorkerError(RuntimeError):
    pass


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def run(args, cwd=None, env=None, timeout=120):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def git(workspace, *args):
    result = run(["git", *args], cwd=workspace)
    if result.returncode:
        raise WorkerError(result.stderr.strip() or "git command failed")
    return result.stdout


def assert_bundle(bundle, expected_mode=None):
    actual = {path.name for path in bundle.iterdir()}
    if actual != EXPECTED_TOP_LEVEL:
        raise WorkerError(f"unexpected bundle entries: {sorted(actual ^ EXPECTED_TOP_LEVEL)}")
    envelope = load_json(bundle / "arm.json")
    if expected_mode and envelope.get("mode") != expected_mode:
        raise WorkerError("--mode differs from immutable arm envelope")
    if envelope.get("mode") not in ("control", "aeg-assisted"):
        raise WorkerError("invalid arm mode")
    workspace = bundle / "workspace"
    if git(workspace, "remote").strip():
        raise WorkerError("arm workspace has a Git remote")
    if git(workspace, "rev-list", "--all", "--count").strip() != "1":
        raise WorkerError("arm workspace must have exactly one commit")
    if git(workspace, "status", "--short").strip():
        raise WorkerError("arm workspace is not clean")
    if envelope["mode"] == "control" and "experience" in envelope:
        raise WorkerError("control envelope contains an experience")
    if envelope["mode"] == "aeg-assisted" and set(envelope.get("experience", {})) != set(envelope["allowed_experience_fields"]):
        raise WorkerError("assisted experience fields differ from the frozen allowlist")
    return envelope


def probe(bundle):
    envelope = assert_bundle(bundle)
    exposed = sorted(name for name in os.environ if SECRET_NAME.search(name))
    allowed = {"GITHUB_ACTIONS"} if os.environ.get("GITHUB_ACTIONS") == "false" else set()
    exposed = [name for name in exposed if name not in allowed]
    if exposed:
        raise WorkerError(f"credential-shaped environment names are exposed: {exposed}")
    for forbidden in ("human.patch", "test_hidden.py", "evaluator.json", "prior-arm.patch", "prior-arm.log"):
        if any(path.name == forbidden for path in bundle.rglob("*")):
            raise WorkerError(f"evaluator or cross-arm artifact is reachable: {forbidden}")
    runner_root_text = os.environ.get("SEB_RUNNER_ROOT")
    if runner_root_text:
        runner_root = Path(runner_root_text).resolve()
        if bundle.parent != runner_root:
            raise WorkerError("bundle is not the sole child of SEB_RUNNER_ROOT")
        siblings = [path.name for path in runner_root.iterdir() if path.resolve() != bundle]
        if siblings:
            raise WorkerError(f"other-arm or controller artifacts are reachable: {sorted(siblings)}")
    return {"arm_id": envelope["arm_id"], "status": "passed"}


def render_prompt(envelope):
    prompt = envelope["task_prompt"]
    prompt += (
        "\n\nBefore the first edit, state the intended production location and approach. "
        "Check the relevant runtime or dependency representation locally. "
        "Do not modify tests. Work only in this repository. Return the required "
        "structured result, including environment assumptions checked."
    )
    if envelope["mode"] == "aeg-assisted":
        prompt += "\n\nAEG retrieved this compact experience. Use it only if local evidence satisfies its applicability conditions:\n"
        for key in envelope["allowed_experience_fields"]:
            prompt += f"\n{key}: {envelope['experience'][key]}"
    else:
        prompt += "\n\nNo AEG experience is available in the control mode. Record experience_disposition as abstained."
    return prompt


def parse_event_metrics(events, workspace, public_command):
    commands = []
    attempts = []
    inspected = set()
    tests = []
    usage = {}
    known = [path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file() and ".git" not in path.parts]
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or usage
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "command_execution" and item.get("command"):
            value = item["command"]
            commands.append(value)
            for relative in known:
                if relative in value:
                    inspected.add(relative)
            if re.search(r"(?:pytest|unittest|test_[A-Za-z0-9_./-]*\.py|python\d*\s+[^\n]*test)", value):
                tests.append({"command": value, "scope": "agent", "passed": item.get("exit_code", 0) == 0})
        if item.get("type") == "file_change":
            changed = sorted(change.get("path", "") for change in item.get("changes", []) if change.get("path"))
            attempts.append(changed)
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    return {
        "commands": commands,
        "attempts": attempts,
        "files_inspected": sorted(inspected),
        "tests": tests,
        "tokens": {
            "input": input_tokens if isinstance(input_tokens, int) else None,
            "output": output_tokens if isinstance(output_tokens, int) else None,
            "unavailable_reason": None if isinstance(input_tokens, int) and isinstance(output_tokens, int) else "runner event stream did not expose complete token usage",
        },
    }


def patch_stats(diff):
    added = deleted = 0
    files = []
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            files.append(line.split(" b/", 1)[1])
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return {"added_lines": added, "deleted_lines": deleted, "files": len(set(files))}, sorted(set(files))


def read_events(path):
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def execute(bundle, output, mode, codex):
    if os.environ.get("SEB_DISPOSABLE_RUNNER") != "1":
        raise WorkerError("execution requires SEB_DISPOSABLE_RUNNER=1 on a one-arm host")
    if not os.environ.get("SEB_RUNNER_ROOT"):
        raise WorkerError("execution requires a dedicated SEB_RUNNER_ROOT containing only this bundle")
    envelope = assert_bundle(bundle, mode)
    probe(bundle)
    output.mkdir(parents=True, exist_ok=False)
    workspace = bundle / "workspace"
    events_path = output / "events.jsonl"
    stderr_path = output / "stderr.log"
    structured_path = output / "agent-result.json"
    command = [
        str(codex), "exec", "--ephemeral", "--ignore-user-config",
        "--model", envelope["model"], "--sandbox", "workspace-write", "--json",
        "--output-schema", str(bundle / "agent-result.schema.json"),
        "-o", str(structured_path), render_prompt(envelope),
    ]
    started = time.monotonic()
    completed_commands = 0
    attempt_hashes = []
    timed_out = budget_exceeded = False
    with events_path.open("w", encoding="utf-8") as stream, stderr_path.open("w", encoding="utf-8") as error_stream:
        process = subprocess.Popen(command, cwd=workspace, stdout=subprocess.PIPE, stderr=error_stream, text=True, bufsize=1)
        assert process.stdout is not None
        while process.poll() is None:
            if time.monotonic() - started > envelope["budget"]["wall_time_seconds"]:
                timed_out = True
                process.terminate()
                break
            ready, _, _ = select.select([process.stdout], [], [], 0.25)
            if not ready:
                continue
            line = process.stdout.readline()
            if not line:
                continue
            stream.write(line)
            stream.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                completed_commands += 1
            if event.get("type") == "item.completed" and item.get("type") == "file_change":
                snapshot = git(workspace, "diff", "--binary", "--", ".")
                snapshot_hash = sha256_bytes(snapshot.encode()) if snapshot else None
                if snapshot_hash and snapshot_hash not in attempt_hashes:
                    attempt_hashes.append(snapshot_hash)
            if completed_commands > envelope["budget"]["max_completed_commands"] or len(attempt_hashes) > envelope["budget"]["max_attempts"]:
                budget_exceeded = True
                process.terminate()
                break
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        for line in process.stdout:
            stream.write(line)
    wall_time_ms = round((time.monotonic() - started) * 1000)
    diff = git(workspace, "diff", "--binary", "--", ".")
    final_hash = sha256_bytes(diff.encode()) if diff else None
    if final_hash and final_hash not in attempt_hashes:
        attempt_hashes.append(final_hash)
    (output / "patch.diff").write_text(diff, encoding="utf-8")
    metrics = parse_event_metrics(read_events(events_path), workspace, envelope["public_test_command"])
    public = run(shlex.split(envelope["public_test_command"]), cwd=workspace, timeout=120)
    metrics["tests"].append({"command": envelope["public_test_command"], "scope": "focused", "passed": public.returncode == 0})
    stats, changed_files = patch_stats(diff)
    structured = load_json(structured_path) if structured_path.is_file() else {}
    if mode == "control":
        experiences = [{"experience_id": None, "disposition": "abstained", "reason": "control mode has no AEG experience"}]
    else:
        disposition = structured.get("experience_disposition", "abstained")
        experiences = [
            {"experience_id": envelope["experience_id"], "disposition": "retrieved", "reason": "frozen treatment payload delivered"},
            {"experience_id": envelope["experience_id"], "disposition": disposition, "reason": structured.get("experience_reason", "structured disposition unavailable")},
        ]
    result = {
        "schema_version": "1.0.0",
        "benchmark_id": envelope["benchmark_id"],
        "family": "S1",
        "pair_id": envelope["pair_id"],
        "replicate": envelope["replicate"],
        "mode": mode,
        "evaluation_status": "captured",
        "input_hashes": envelope["input_hashes"],
        "budget": envelope["budget"],
        "regression_free_success": None,
        "attempts": len(attempt_hashes),
        "completed_commands": len(metrics["commands"]),
        "tests_run": metrics["tests"],
        "files_inspected": metrics["files_inspected"],
        "files_changed": changed_files,
        "patch_size": stats,
        "wall_time_ms": wall_time_ms,
        "tokens": metrics["tokens"],
        "failed_historical_paths_repeated": [],
        "environment_assumptions_checked": structured.get("environment_assumptions_checked", []),
        "experiences": experiences,
        "negative_transfer": None,
        "evaluator_findings": ["hidden evaluation pending"],
        "limitations": [item for item, present in (("agent timed out", timed_out), ("agent exceeded a frozen command or attempt budget", budget_exceeded), ("Codex process exited non-zero", process.returncode != 0)) if present],
    }
    (output / "arm-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("probe")
    check.add_argument("--bundle", default=".")
    run_parser = sub.add_parser("execute")
    run_parser.add_argument("--bundle", default=".")
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--mode", required=True, choices=("control", "aeg-assisted"))
    run_parser.add_argument("--codex", default=shutil.which("codex"))
    args = parser.parse_args()
    bundle = Path(args.bundle).resolve()
    if args.action == "probe":
        print(json.dumps(probe(bundle), indent=2, sort_keys=True))
        return 0
    if not args.codex:
        raise WorkerError("Codex executable not found")
    result = execute(bundle, Path(args.output).resolve(), args.mode, Path(args.codex).resolve())
    print(json.dumps({"arm_id": load_json(bundle / "arm.json")["arm_id"], "captured": result["evaluation_status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (WorkerError, subprocess.TimeoutExpired) as error:
        print(f"situated arm worker error: {error}", file=sys.stderr)
        raise SystemExit(2)
