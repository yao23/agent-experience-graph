#!/usr/bin/env python3
"""Validate sanitized paired results and recompute their published aggregate."""

import argparse
import json
import re
import statistics
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS = LAB_DIR / "results" / "v0.1.3-paired-results.json"
DEFAULT_EXPERIENCES = LAB_DIR.parents[1] / "experiences" / "verified.json"
ARMS = ("baseline", "assisted")
METRICS = ("completedCommands", "actualTestExecutions", "nonCachedTokens", "durationMs")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
FORBIDDEN_KEYS = {
    "rawprompt", "rawprompts", "rawjsonl", "stderr", "logs", "rawlogs",
    "patch", "sourcepatch", "credential", "credentials", "secret", "secrets",
    "workspacepath", "privatepath", "privatesource",
}


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def is_nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_forbidden_keys(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            require(normalized not in FORBIDDEN_KEYS, f"{path}.{key} is a forbidden public field")
            check_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden_keys(child, f"{path}[{index}]")


def paired_median(trials, metric):
    values = [trial["arms"]["assisted"][metric] - trial["arms"]["baseline"][metric] for trial in trials]
    result = statistics.median(values)
    return int(result) if result == int(result) else result


def recompute_aggregate(results):
    trials = results["trials"]
    return {
        "armCounts": {arm: len(trials) for arm in ARMS},
        "verifiedCounts": {
            arm: sum(1 for trial in trials if trial["arms"][arm]["verified"])
            for arm in ARMS
        },
        "pairedMedianAssistedMinusBaseline": {
            metric: paired_median(trials, metric) for metric in METRICS
        },
    }


def validate_results(results):
    require(isinstance(results, dict), "paired results must be an object")
    check_forbidden_keys(results)
    trials = results.get("trials")
    require(isinstance(trials, list) and trials, "trials must be a non-empty array")
    expected_hash = results.get("expectedPatchSha256")
    require(isinstance(expected_hash, str) and SHA256_RE.fullmatch(expected_hash), "expectedPatchSha256 must be a SHA-256 hex digest")

    seen_ids = set()
    task_ids = set()
    all_patch_hashes = set()
    for index, trial in enumerate(trials):
        path = f"trials[{index}]"
        require(isinstance(trial, dict), f"{path} must be an object")
        trial_id = trial.get("trialId")
        require(isinstance(trial_id, str) and trial_id, f"{path}.trialId must be a non-empty string")
        require(trial_id not in seen_ids, f"duplicate trial ID: {trial_id}")
        seen_ids.add(trial_id)
        task_id = trial.get("taskId")
        require(isinstance(task_id, str) and task_id, f"{path}.taskId must be a non-empty string")
        task_ids.add(task_id)
        expected_order = list(ARMS) if index % 2 == 0 else list(reversed(ARMS))
        require(trial.get("executionOrder") == expected_order, f"{path}.executionOrder must preserve alternating paired order")
        source_sha = trial.get("runnerSourceCommitSha")
        require(source_sha is None or (isinstance(source_sha, str) and COMMIT_RE.fullmatch(source_sha)), f"{path}.runnerSourceCommitSha must be null or a commit SHA")
        require(trial.get("model") is None or isinstance(trial.get("model"), str), f"{path}.model must be null or a string")
        runtime = trial.get("runtime")
        require(isinstance(runtime, dict), f"{path}.runtime must be an object")
        require(runtime.get("sessionMode") == "ephemeral", f"{path}.runtime.sessionMode must be ephemeral")
        require(runtime.get("sandbox") == "workspace-write", f"{path}.runtime.sandbox must be workspace-write")
        require(runtime.get("codexCliVersion") is None or isinstance(runtime.get("codexCliVersion"), str), f"{path}.runtime.codexCliVersion must be null or a string")
        arms = trial.get("arms")
        require(isinstance(arms, dict) and set(arms) == set(ARMS), f"{path}.arms must contain exactly baseline and assisted")
        for arm in ARMS:
            row = arms[arm]
            arm_path = f"{path}.arms.{arm}"
            require(isinstance(row, dict), f"{arm_path} must be an object")
            require(isinstance(row.get("verified"), bool), f"{arm_path}.verified must be boolean")
            for metric in METRICS:
                require(is_nonnegative_int(row.get(metric)), f"{arm_path}.{metric} must be a non-negative integer")
            patch_hash = row.get("patchSha256")
            require(isinstance(patch_hash, str) and SHA256_RE.fullmatch(patch_hash), f"{arm_path}.patchSha256 must be a SHA-256 hex digest")
            all_patch_hashes.add(patch_hash)
            require(patch_hash == expected_hash, f"{arm_path}.patchSha256 is inconsistent with expectedPatchSha256")

    require(len(task_ids) == 1, "all pairs must use the same task ID")
    require(len(all_patch_hashes) == 1, "verified arms must have consistent patch hashes")
    recomputed = recompute_aggregate(results)
    require(results.get("aggregate") == recomputed, f"published aggregate does not match recomputation: {recomputed}")
    return recomputed


def find_experience(experiences, artifact_path):
    matches = [
        item for item in experiences
        if item.get("provenance", {}).get("experimentEvidence", {}).get("artifact") == artifact_path
    ]
    require(len(matches) == 1, f"expected exactly one experience for {artifact_path}, found {len(matches)}")
    return matches[0]


def validate_against_experience(aggregate, experiences, artifact_path):
    require(isinstance(experiences, list), "verified experience library must be an array")
    experience = find_experience(experiences, artifact_path)
    metrics = experience.get("metrics", {})
    expected = {
        "armCounts": {
            "baseline": metrics.get("baselineArms"),
            "assisted": metrics.get("assistedArms"),
        },
        "verifiedCounts": {
            "baseline": metrics.get("baselineArmsVerified"),
            "assisted": metrics.get("assistedArmsVerified"),
        },
        "pairedMedianAssistedMinusBaseline": metrics.get("pairedMedianAssistedMinusBaseline"),
    }
    require(aggregate == expected, f"paired aggregate does not match verified experience: {expected}")


def validate_files(results_path, experiences_path):
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    experiences = json.loads(Path(experiences_path).read_text(encoding="utf-8"))
    aggregate = validate_results(results)
    artifact_path = str(Path(results_path).resolve().relative_to(LAB_DIR.parents[1])).replace("\\", "/")
    validate_against_experience(aggregate, experiences, artifact_path)
    return aggregate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--experiences", default=str(DEFAULT_EXPERIENCES))
    args = parser.parse_args()
    aggregate = validate_files(args.results, args.experiences)
    print(json.dumps({"status": "passed", "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
