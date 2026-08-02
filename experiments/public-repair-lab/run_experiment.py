#!/usr/bin/env python3
"""Run isolated baseline and AEG-assisted Codex repairs of one public bug."""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = LAB_DIR / "fixture"
RESULT_SCHEMA = LAB_DIR / "result.schema.json"
EXPERIENCE = LAB_DIR / "experience.json"


def run(command, cwd, timeout=60):
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def verify(workspace):
    started = time.monotonic()
    result = run([sys.executable, "test_bug.py"], workspace)
    return {
        "passed": result.returncode == 0,
        "exitCode": result.returncode,
        "durationMs": round((time.monotonic() - started) * 1000),
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def prepare_arm(run_dir, arm):
    workspace = run_dir / arm
    shutil.copytree(FIXTURE_DIR, workspace)
    if arm == "assisted":
        shutil.copy2(EXPERIENCE, workspace / "AEG_EXPERIENCE.json")
    run(["git", "init", "-q"], workspace)
    run(["git", "add", "."], workspace)
    run(
        [
            "git",
            "-c",
            "user.name=AEG Repair Lab",
            "-c",
            "user.email=aeg-repair-lab@example.invalid",
            "commit",
            "-qm",
            "buggy fixture",
        ],
        workspace,
    )
    return workspace


def prompt_for(arm):
    shared = """Read ISSUE.md and repair the bug. Work only in this repository.
Run `python3 test_bug.py` before editing, make the smallest production-code change,
and run the same command afterward. Do not edit the test. Return the requested
structured result and set aeg_experience_used accurately."""
    if arm == "assisted":
        return shared + "\n\nBefore diagnosing, read AEG_EXPERIENCE.json and use only the guidance that fits this failure."
    return shared + "\n\nThis is the baseline arm. No AEG experience is available."


def parse_events(path):
    events = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def summarize_events(events):
    commands = []
    usage = {}
    file_changes = 0
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage", usage)
        item = event.get("item") or {}
        if item.get("type") == "command_execution" and item.get("command"):
            commands.append(item["command"])
        if item.get("type") == "file_change" and event.get("type") == "item.completed":
            file_changes += 1
    return {
        "commands": commands,
        "commandCount": len(commands),
        "testCommandCount": sum("test_bug.py" in command for command in commands),
        "fileChangeEvents": file_changes,
        "usage": usage,
    }


def execute_arm(codex, run_dir, arm):
    workspace = run_dir / arm
    events_path = run_dir / f"{arm}.jsonl"
    stderr_path = run_dir / f"{arm}.stderr.log"
    last_message = run_dir / f"{arm}.result.json"
    started = time.monotonic()
    command = [
        codex,
        "exec",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--json",
        "--output-schema",
        str(RESULT_SCHEMA),
        "-o",
        str(last_message),
        prompt_for(arm),
    ]
    with events_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, cwd=workspace, stdout=stdout, stderr=stderr, timeout=900, check=False)
    duration_ms = round((time.monotonic() - started) * 1000)
    verification = verify(workspace)
    diff = run(["git", "diff", "--", "."], workspace).stdout
    (run_dir / f"{arm}.patch").write_text(diff, encoding="utf-8")
    events = parse_events(events_path)
    return {
        "arm": arm,
        "codexExitCode": completed.returncode,
        "durationMs": duration_ms,
        "verification": verification,
        "events": summarize_events(events),
        "changedFiles": run(["git", "diff", "--name-only"], workspace).stdout.splitlines(),
    }


def write_report(run_dir, report):
    (run_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = []
    for arm in ("baseline", "assisted"):
        item = report["arms"].get(arm, {})
        verification = item.get("verification", {})
        events = item.get("events", {})
        usage = events.get("usage", {})
        rows.append(
            f"| {arm} | {verification.get('passed', False)} | {item.get('durationMs', '-')} | "
            f"{events.get('commandCount', '-')} | {events.get('testCommandCount', '-')} | "
            f"{usage.get('input_tokens', '-')} | {usage.get('output_tokens', '-')} |"
        )
    markdown = """# AEG Public Repair Lab report

This is a one-task instrumentation trial, not statistical evidence of improvement.

| Arm | Verified | Duration ms | Commands | Test commands | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|---:|
""" + "\n".join(rows) + "\n"
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Create and validate both isolated workspaces without invoking Codex.")
    parser.add_argument("--output", help="Override the run output directory.")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output).resolve() if args.output else Path.cwd() / ".aeg" / "repair-lab" / f"pysnooper-path-output-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    for arm in ("baseline", "assisted"):
        prepare_arm(run_dir, arm)

    initial = {arm: verify(run_dir / arm) for arm in ("baseline", "assisted")}
    if any(result["passed"] for result in initial.values()):
        raise RuntimeError("The buggy fixture unexpectedly passed before repair.")

    report = {
        "schemaVersion": "0.1.2",
        "task": "PySnooper path-output NameError",
        "source": "experiments/public-repair-lab/SOURCE.md",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "initialVerification": initial,
        "arms": {},
    }
    codex = shutil.which("codex")
    if args.prepare_only or not codex:
        report["status"] = "prepared" if args.prepare_only else "blocked-codex-not-found"
        write_report(run_dir, report)
        print(run_dir)
        if not codex and not args.prepare_only:
            print("Codex executable not found. Open this repository in the local Codex app or install the CLI, then rerun.", file=sys.stderr)
            return 2
        return 0

    for arm in ("baseline", "assisted"):
        report["arms"][arm] = execute_arm(codex, run_dir, arm)
    report["status"] = "completed"
    write_report(run_dir, report)
    print(run_dir)
    return 0 if all(item["verification"]["passed"] for item in report["arms"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
