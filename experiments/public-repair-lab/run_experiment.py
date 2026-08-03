#!/usr/bin/env python3
"""Run isolated baseline and AEG-assisted Codex repairs."""

import argparse
import json
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parent
RESULT_SCHEMA = LAB_DIR / "result.schema.json"
DEFAULT_TASK = "fastapi-nested-response"
TASKS = {
    "pysnooper-path-output": {
        "name": "PySnooper path-output NameError",
        "fixture": LAB_DIR / "fixture",
        "experience": LAB_DIR / "experience.json",
        "source": LAB_DIR / "SOURCE.md",
        "verification": "python3 test_bug.py",
    },
    "fastapi-nested-response": {
        "name": "FastAPI nested response-model data leak",
        "fixture": LAB_DIR / "tasks" / "fastapi-nested-response" / "fixture",
        "experience": LAB_DIR / "tasks" / "fastapi-nested-response" / "experience.json",
        "source": LAB_DIR / "tasks" / "fastapi-nested-response" / "SOURCE.md",
        "verification": "python3 test_bug.py",
    },
}


def run(command, cwd, timeout=60):
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def verify(workspace, verification_command):
    started = time.monotonic()
    result = run(shlex.split(verification_command), workspace)
    return {
        "passed": result.returncode == 0,
        "exitCode": result.returncode,
        "durationMs": round((time.monotonic() - started) * 1000),
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def prepare_arm(trial_dir, arm, task):
    workspace = trial_dir / arm
    shutil.copytree(task["fixture"], workspace)
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


def experience_prompt(path):
    experience = json.loads(path.read_text(encoding="utf-8"))
    steps = "\n".join(f"{index}. {item}" for index, item in enumerate(experience["steps"][1:4], 1))
    failures = "\n".join(f"- {item}" for item in experience["failures"][:2])
    return f"""AEG retrieved a compact, verified recovery capsule:

Pattern: {experience['recovery']}
Diagnostic path:
{steps}
Guardrails:
{failures}

Verify that the pattern matches local evidence before editing."""


def prompt_for(arm, task):
    verification_command = task["verification"]
    shared = f"""Read ISSUE.md and repair the bug. Work only in this repository.
Run `{verification_command}` before editing, make the smallest production-code change,
and run the same command afterward. Do not edit the test. Return the requested
structured result and set aeg_experience_used accurately."""
    if arm == "assisted":
        return shared + "\n\n" + experience_prompt(task["experience"])
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


def shell_body(command):
    """Return the script passed to a shell, or the original command."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    for index, part in enumerate(parts[:-1]):
        if part in ("-c", "-lc"):
            return parts[index + 1]
    return command


def count_command_invocations(commands, expected_command):
    """Count actual shell invocations without matching filenames in inspection commands."""
    expected = shlex.split(expected_command)
    count = 0
    for command in commands:
        for segment in re.split(r"\s*(?:&&|\|\||;)\s*", shell_body(command)):
            try:
                tokens = shlex.split(segment)
            except ValueError:
                continue
            if tokens[:len(expected)] == expected:
                count += 1
    return count


def summarize_events(events, verification_command):
    commands = []
    usage = {}
    file_changes = 0
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage", usage)
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "command_execution" and item.get("command"):
            commands.append(item["command"])
        if item.get("type") == "file_change":
            file_changes += 1
    input_tokens = usage.get("input_tokens", 0)
    cached_tokens = usage.get("cached_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return {
        "commands": commands,
        "commandCount": len(commands),
        "testCommandCount": count_command_invocations(commands, verification_command),
        "fileChangeEvents": file_changes,
        "usage": usage,
        "nonCachedInputTokens": max(0, input_tokens - cached_tokens),
        "totalNonCachedTokens": max(0, input_tokens - cached_tokens) + output_tokens,
    }


def execute_arm(codex, trial_dir, arm, task):
    workspace = trial_dir / arm
    events_path = trial_dir / f"{arm}.jsonl"
    stderr_path = trial_dir / f"{arm}.stderr.log"
    last_message = trial_dir / f"{arm}.result.json"
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
        prompt_for(arm, task),
    ]
    with events_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, cwd=workspace, stdout=stdout, stderr=stderr, timeout=900, check=False)
    duration_ms = round((time.monotonic() - started) * 1000)
    verification = verify(workspace, task["verification"])
    diff = run(["git", "diff", "--", "."], workspace).stdout
    (trial_dir / f"{arm}.patch").write_text(diff, encoding="utf-8")
    events = parse_events(events_path)
    return {
        "arm": arm,
        "codexExitCode": completed.returncode,
        "durationMs": duration_ms,
        "verification": verification,
        "events": summarize_events(events, task["verification"]),
        "changedFiles": run(["git", "diff", "--name-only"], workspace).stdout.splitlines(),
    }


def paired_delta(trial, key):
    return trial["arms"]["assisted"][key] - trial["arms"]["baseline"][key]


def event_delta(trial, key):
    return trial["arms"]["assisted"]["events"][key] - trial["arms"]["baseline"]["events"][key]


def median(values):
    return round(statistics.median(values), 1) if values else 0


def aggregate_trials(trials):
    aggregate = {"arms": {}, "pairedMedianDelta": {}}
    for arm in ("baseline", "assisted"):
        rows = [trial["arms"][arm] for trial in trials]
        aggregate["arms"][arm] = {
            "verifiedCount": sum(row["verification"]["passed"] for row in rows),
            "trialCount": len(rows),
            "medianDurationMs": median([row["durationMs"] for row in rows]),
            "medianCommandCount": median([row["events"]["commandCount"] for row in rows]),
            "medianTestCommandCount": median([row["events"]["testCommandCount"] for row in rows]),
            "medianTotalNonCachedTokens": median([row["events"]["totalNonCachedTokens"] for row in rows]),
        }
    aggregate["pairedMedianDelta"] = {
        "durationMs": median([paired_delta(trial, "durationMs") for trial in trials]),
        "commandCount": median([event_delta(trial, "commandCount") for trial in trials]),
        "testCommandCount": median([event_delta(trial, "testCommandCount") for trial in trials]),
        "totalNonCachedTokens": median([event_delta(trial, "totalNonCachedTokens") for trial in trials]),
    }
    baseline_verified = aggregate["arms"]["baseline"]["verifiedCount"]
    assisted_verified = aggregate["arms"]["assisted"]["verifiedCount"]
    if len(trials) < 3:
        verdict = "insufficient-trials"
    elif assisted_verified > baseline_verified:
        verdict = "assisted-improved-success-rate"
    elif assisted_verified < baseline_verified:
        verdict = "assisted-regressed-success-rate"
    else:
        efficiency_wins = sum(
            aggregate["pairedMedianDelta"][key] < 0
            for key in ("durationMs", "commandCount", "totalNonCachedTokens")
        )
        baseline_tokens = aggregate["arms"]["baseline"]["medianTotalNonCachedTokens"]
        token_regression = aggregate["pairedMedianDelta"]["totalNonCachedTokens"]
        material_token_regression = baseline_tokens > 0 and token_regression > baseline_tokens * 0.25
        if efficiency_wins >= 2 and not material_token_regression:
            verdict = "assisted-improved-efficiency"
        elif efficiency_wins >= 2:
            verdict = "mixed-efficiency-signal"
        else:
            verdict = "no-measured-benefit"
    aggregate["verdict"] = verdict
    return aggregate


def write_report(run_dir, report):
    (run_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = []
    for trial in report.get("trials", []):
        for arm in ("baseline", "assisted"):
            item = trial["arms"].get(arm, {})
            verification = item.get("verification", {})
            events = item.get("events", {})
            rows.append(
                f"| {trial['index']} | {arm} | {verification.get('passed', False)} | {item.get('durationMs', '-')} | "
                f"{events.get('commandCount', '-')} | {events.get('testCommandCount', '-')} | "
                f"{events.get('totalNonCachedTokens', '-')} |"
            )
    aggregate = report.get("aggregate", {})
    delta = aggregate.get("pairedMedianDelta", {})
    markdown = f"""# AEG Public Repair Lab report

Task: **{report['task']}**

This is a controlled repair experiment. A positive result on one task family is not evidence of general improvement.

| Trial | Arm | Verified | Duration ms | Commands | Test runs | Non-cached tokens |
|---:|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Aggregate

- Verdict: **{aggregate.get('verdict', 'not-run')}**
- Paired median assisted-minus-baseline duration: {delta.get('durationMs', '-')} ms
- Paired median assisted-minus-baseline commands: {delta.get('commandCount', '-')}
- Paired median assisted-minus-baseline test runs: {delta.get('testCommandCount', '-')}
- Paired median assisted-minus-baseline non-cached tokens: {delta.get('totalNonCachedTokens', '-')}
"""
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Create and validate isolated workspaces without invoking Codex.")
    parser.add_argument("--output", help="Override the run output directory.")
    parser.add_argument("--task", choices=sorted(TASKS), default=DEFAULT_TASK, help="Public repair task to run.")
    parser.add_argument("--trials", type=int, default=1, help="Number of paired trials (1-10).")
    args = parser.parse_args()
    if not 1 <= args.trials <= 10:
        parser.error("--trials must be between 1 and 10")

    task = TASKS[args.task]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output).resolve() if args.output else Path.cwd() / ".aeg" / "repair-lab" / f"{args.task}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "schemaVersion": "0.1.3",
        "taskId": args.task,
        "task": task["name"],
        "source": str(task["source"].relative_to(LAB_DIR)),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "trialsRequested": args.trials,
        "trials": [],
    }
    codex = shutil.which("codex")

    for index in range(1, args.trials + 1):
        trial_dir = run_dir / f"trial-{index:02d}"
        trial_dir.mkdir()
        for arm in ("baseline", "assisted"):
            prepare_arm(trial_dir, arm, task)
        initial = {arm: verify(trial_dir / arm, task["verification"]) for arm in ("baseline", "assisted")}
        if any(result["passed"] for result in initial.values()):
            raise RuntimeError("The buggy fixture unexpectedly passed before repair.")
        trial = {
            "index": index,
            "executionOrder": ["baseline", "assisted"] if index % 2 else ["assisted", "baseline"],
            "initialVerification": initial,
            "arms": {},
        }
        report["trials"].append(trial)
        if args.prepare_only or not codex:
            continue
        for arm in trial["executionOrder"]:
            trial["arms"][arm] = execute_arm(codex, trial_dir, arm, task)

    if args.prepare_only or not codex:
        report["status"] = "prepared" if args.prepare_only else "blocked-codex-not-found"
        report["aggregate"] = {"verdict": "not-run"}
        write_report(run_dir, report)
        print(run_dir)
        if not codex and not args.prepare_only:
            print("Codex executable not found. Open this repository in the local Codex app or install the CLI, then rerun.", file=sys.stderr)
            return 2
        return 0

    report["aggregate"] = aggregate_trials(report["trials"])
    report["status"] = "completed"
    write_report(run_dir, report)
    print(run_dir)
    return 0 if all(
        item["verification"]["passed"]
        for trial in report["trials"]
        for item in trial["arms"].values()
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
