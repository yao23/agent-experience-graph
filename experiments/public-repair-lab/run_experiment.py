#!/usr/bin/env python3
"""Run isolated baseline and AEG-assisted Codex repairs."""

import argparse
import hashlib
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
REPO_DIR = LAB_DIR.parents[1]
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
    "protocol-resource-delegation": {
        "name": "Protocol-owned resource delegation transfer",
        "fixture": LAB_DIR / "tasks" / "protocol-resource-delegation" / "fixture",
        "experience": REPO_DIR / "experiences" / "verified.json",
        "experienceId": "trace-2026-08-03-tr-04-tornado-nodelay",
        "retrievalQuery": "repair a public wrapper control after an active resource moved behind a protocol layer",
        "source": LAB_DIR / "tasks" / "protocol-resource-delegation" / "SOURCE.md",
        "verification": "python3 test_bug.py",
    },
    "rpc-upgrade-interactive-mode": {
        "name": "RPC upgrade interactive-mode delegation trap",
        "fixture": LAB_DIR / "tasks" / "rpc-upgrade-interactive-mode" / "fixture",
        "experience": LAB_DIR / "tasks" / "rpc-upgrade-interactive-mode" / "experience.json",
        "experienceId": "trace-2026-08-03-tr-04-tornado-nodelay",
        "retrievalQuery": "avoid repairing the wrong client-side surface when a public low-latency control broke after protocol stream ownership migration",
        "source": LAB_DIR / "tasks" / "rpc-upgrade-interactive-mode" / "SOURCE.md",
        "verification": "python3 test_bug.py",
        "fixedPrompt": """Read ISSUE.md and repair the bug. Work only in this repository.
Run `python3 test_bug.py` before editing. Before the first edit, report the first
production location you intend to change and your proposed approach in the
structured result fields. Make the smallest production-code change and run the
same test command afterward. Do not edit the test. Set aeg_experience_used
accurately.""",
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


def experience_prompt(path, experience_id=None):
    experience = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(experience, dict) and "failedApproach" in experience:
        return f"""AEG retrieved one concise, verified experience:

Experience ID: {experience['id']}
Relevant context: {experience['context']}
Known failed approach: {experience['failedApproach']}
Recovery: {experience['recovery']}
Validated outcome: {experience['validatedOutcome']}

Use this only if local evidence matches. Do not assume file or class names transfer."""
    if experience_id is not None:
        experience = next(item for item in experience if item["id"] == experience_id)
        steps = "\n".join(f"{index}. {item}" for index, item in enumerate(experience["lessons"][:3], 1))
        failures = "\n".join(f"- {item}" for item in experience["limitations"][:2])
        return f"""AEG retrieved a compact, verified recovery capsule:

Verified experience: {experience['id']}
Pattern: {experience['task']}
Diagnostic path:
{steps}
Guardrails:
{failures}

Verify that the pattern matches local evidence before editing."""
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
    shared = task.get("fixedPrompt") or f"""Read ISSUE.md and repair the bug. Work only in this repository.
Run `{verification_command}` before editing, make the smallest production-code change,
and run the same command afterward. Do not edit the test. Return the requested
structured result and set aeg_experience_used accurately."""
    if arm == "assisted":
        return shared + "\n\n" + experience_prompt(task["experience"], task.get("experienceId"))
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


def summarize_events(events, verification_command, known_files=()):
    commands = []
    usage = {}
    file_changes = 0
    attempt_paths = []
    pre_edit_messages = []
    files_inspected = set()
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage", usage)
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and file_changes == 0 and item.get("text"):
            pre_edit_messages.append(item["text"])
        if item.get("type") == "command_execution" and item.get("command"):
            commands.append(item["command"])
            if re.search(r"(?:^|\s)(?:cat|sed|head|tail|rg)(?:\s|$)", shell_body(item["command"])):
                for path in known_files:
                    if path in item["command"]:
                        files_inspected.add(path)
        if item.get("type") == "file_change":
            file_changes += 1
            attempt_paths.append([
                Path(change.get("path", "")).name
                for change in item.get("changes", [])
                if change.get("path")
            ])
    input_tokens = usage.get("input_tokens", 0)
    cached_tokens = usage.get("cached_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return {
        "commands": commands,
        "commandCount": len(commands),
        "testCommandCount": count_command_invocations(commands, verification_command),
        "fileChangeEvents": file_changes,
        "attemptCount": file_changes,
        "attemptPaths": attempt_paths,
        "firstRepairPaths": attempt_paths[0] if attempt_paths else [],
        "filesInspected": sorted(files_inspected),
        "preEditAgentMessages": pre_edit_messages,
        "usage": usage,
        "nonCachedInputTokens": max(0, input_tokens - cached_tokens),
        "totalNonCachedTokens": max(0, input_tokens - cached_tokens) + output_tokens,
    }


def execute_arm(codex, trial_dir, arm, task, model):
    workspace = trial_dir / arm
    events_path = trial_dir / f"{arm}.jsonl"
    stderr_path = trial_dir / f"{arm}.stderr.log"
    last_message = trial_dir / f"{arm}.result.json"
    started = time.monotonic()
    command = [
        codex,
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
        str(last_message),
        prompt_for(arm, task),
    ]
    attempt_snapshots = []
    with events_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.Popen(
            command,
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            bufsize=1,
        )
        assert completed.stdout is not None
        for line in completed.stdout:
            stdout.write(line)
            stdout.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "file_change":
                snapshot = run(["git", "diff", "--", "."], workspace).stdout
                snapshot_index = len(attempt_snapshots) + 1
                (trial_dir / f"{arm}.attempt-{snapshot_index}.patch").write_text(snapshot, encoding="utf-8")
                attempt_snapshots.append({
                    "index": snapshot_index,
                    "changedFiles": run(["git", "diff", "--name-only"], workspace).stdout.splitlines(),
                    "patchSha256": hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
                })
        completed.wait(timeout=900)
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
        "events": summarize_events(
            events,
            task["verification"],
            [str(path.relative_to(task["fixture"])) for path in task["fixture"].rglob("*") if path.is_file()],
        ),
        "attemptSnapshots": attempt_snapshots,
        "changedFiles": run(["git", "diff", "--name-only"], workspace).stdout.splitlines(),
        "patchSha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
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
            f"| {trial['index']} | {arm} | {verification.get('passed', False)} | {events.get('attemptCount', '-')} | {item.get('durationMs', '-')} | "
                f"{events.get('commandCount', '-')} | {events.get('testCommandCount', '-')} | "
                f"{events.get('totalNonCachedTokens', '-')} |"
            )
    aggregate = report.get("aggregate", {})
    delta = aggregate.get("pairedMedianDelta", {})
    markdown = f"""# AEG Public Repair Lab report

Task: **{report['task']}**

This is a controlled repair experiment. A positive result on one task family is not evidence of general improvement.

| Trial | Arm | Verified | Attempts | Duration ms | Commands | Test runs | Non-cached tokens |
|---:|---|---:|---:|---:|---:|---:|---:|
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
    parser.add_argument("--model", default="gpt-5.6-sol", help="Explicit Codex model used identically for both arms.")
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
        "model": args.model,
        "sharedPromptSha256": hashlib.sha256(prompt_for("baseline", task).split("\n\nThis is the baseline arm.")[0].encode("utf-8")).hexdigest(),
        "trialsRequested": args.trials,
        "trials": [],
    }
    codex = shutil.which("codex")
    if codex:
        report["codexVersion"] = run([codex, "--version"], LAB_DIR).stdout.strip()
    if task.get("retrievalQuery"):
        report["retrieval"] = {
            "query": task["retrievalQuery"],
            "verifiedExperienceId": task.get("experienceId"),
            "delivery": "compact capsule injected only into the assisted arm",
        }

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
            trial["arms"][arm] = execute_arm(codex, trial_dir, arm, task, args.model)

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
