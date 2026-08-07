#!/usr/bin/env python3
"""Deterministically validate the sanitized Batch 01 evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


BATCH = Path(__file__).resolve().parent
REPO = BATCH.parents[1]
CANDIDATES = BATCH / "candidates"
MANIFESTS = BATCH / "manifests"
ALLOWED_SUFFIXES = {".json", ".md", ".py"}
ALLOWED_DIRECTORIES = {"candidates", "evidence", "manifests"}
REJECTED_SUFFIXES = {
    ".7z", ".bin", ".diff", ".gz", ".jsonl", ".log", ".ndjson",
    ".orig", ".out", ".patch", ".pdf", ".rej", ".tar", ".trace",
    ".vsix", ".zip",
}
REJECTED_TREE_NAMES = {
    ".git", ".venv", "clone", "external", "node_modules", "repo",
    "source", "source-tree", "src", "tmp", "vendor",
}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer credential": re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    "password assignment": re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"\n]{8,}['\"]"),
}
PRIVATE_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
)
PROPRIETARY_MARKERS = re.compile(
    r"(?im)^(?:confidential|proprietary source|trade secret)(?:\s|:|$)"
)
RAW_CONVERSATION_MARKERS = re.compile(
    r"(?i)[{,]\s*['\"]role['\"]\s*:\s*['\"](?:user|assistant|system)['\"]"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(REPO)}: {exc}") from exc


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO, check=True)


def validate_file_layout() -> list[Path]:
    files = sorted(path for path in BATCH.rglob("*") if path.is_file())
    require(files, "batch directory is empty")
    for path in files:
        relative = path.relative_to(BATCH)
        require(path.suffix.lower() in ALLOWED_SUFFIXES, f"disallowed file type: {relative}")
        require(path.suffix.lower() not in REJECTED_SUFFIXES, f"raw log/binary/patch artifact: {relative}")
        require(not any(part.lower() in REJECTED_TREE_NAMES for part in relative.parts[:-1]), f"external or temporary source tree: {relative}")
        if len(relative.parts) > 1:
            require(relative.parts[0] in ALLOWED_DIRECTORIES, f"unexpected batch directory: {relative}")
        require("full-log" not in path.name.lower(), f"full log artifact: {relative}")
        require("conversation" not in path.name.lower() and "transcript" not in path.name.lower(), f"raw conversation artifact: {relative}")
        content = path.read_bytes()
        require(b"\x00" not in content, f"binary artifact: {relative}")
        if path.resolve() == Path(__file__).resolve():
            continue
        text = content.decode("utf-8")
        for label, pattern in SECRET_PATTERNS.items():
            require(pattern.search(text) is None, f"{label} detected in {relative}")
        for pattern in PRIVATE_PATH_PATTERNS:
            require(pattern.search(text) is None, f"private filesystem path detected in {relative}")
        require(PROPRIETARY_MARKERS.search(text) is None, f"proprietary-material marker detected in {relative}")
        require(RAW_CONVERSATION_MARKERS.search(text) is None, f"raw conversation record detected in {relative}")
    return files


def validate_records() -> tuple[list[Path], list[Path]]:
    candidate_paths = sorted(CANDIDATES.glob("*.json"))
    manifest_paths = sorted(MANIFESTS.glob("*.json"))
    require(len(candidate_paths) == 7, f"expected 7 candidates, found {len(candidate_paths)}")
    require(len(manifest_paths) == 7, f"expected 7 manifests, found {len(manifest_paths)}")
    require((BATCH / "execution-state.json").is_file(), "execution-state.json is missing")

    manifests = {}
    for path in manifest_paths:
        manifest = load_json(path)
        require(isinstance(manifest, dict), f"manifest must be an object: {path.name}")
        manifests[path.name[:2]] = manifest
    state = load_json(BATCH / "execution-state.json")
    require(isinstance(state, dict) and len(state.get("projects", [])) == 7, "execution state must describe seven projects")

    records = {}
    for path in candidate_paths:
        payload = load_json(path)
        require(isinstance(payload, list) and len(payload) == 1, f"candidate must contain one record: {path.name}")
        record = payload[0]
        public = record.get("provenance", {}).get("publicSource", {})
        require(isinstance(public.get("repository"), str) and public["repository"].startswith("https://"), f"missing public repository provenance: {path.name}")
        require(isinstance(public.get("license"), str) and public["license"].strip(), f"missing public license status: {path.name}")
        expected_manifest_hash = hashlib.sha256((MANIFESTS / path.name).read_bytes()).hexdigest()
        actual_manifest_hash = record.get("verification", {}).get("localChecks", {}).get("taskManifestSha256")
        require(actual_manifest_hash == expected_manifest_hash, f"manifest digest mismatch: {path.name}")
        records[path.name[:2]] = record

    for category in ("05", "06"):
        checks = records[category]["verification"]["localChecks"]
        require(checks.get("retrievalTimingValidity", "").startswith("invalid/procedurally contaminated"), f"Category {category} must disclose contaminated late retrieval")
        require(checks.get("retrievalEffectEvidence", "").startswith("invalid:"), f"Category {category} must reject retrieval-effect evidence")
        require(checks.get("priorAEGExperienceUsed", "").lower().startswith("no;"), f"Category {category} must not claim experience reuse")

    category05 = records["05"]
    license_text = category05["provenance"]["publicSource"]["license"].lower()
    limitations = " ".join(category05.get("limitations", [])).lower()
    require("license" in license_text and "missing" in license_text, "Category 05 public-source license status must disclose the missing packaged license")
    require("license" in limitations and ("missing" in limitations or "omitted" in limitations), "Category 05 limitations must disclose the missing packaged license")

    category07 = records["07"]
    experiment = category07["provenance"]["experimentEvidence"]
    require(experiment.get("runnerSourceCommitSha") is None, "Category 07 original runner commit must be null")
    require("unavailable" in experiment.get("runnerSourceCommitStatus", "").lower(), "Category 07 must explain the unavailable original commit")
    qualification = category07["verification"]["localChecks"].get("commitIdentityQualification", "").lower()
    require("patch" in qualification and "does not recover" in qualification, "Category 07 must distinguish patch equivalence from commit identity")
    manifest07 = manifests["07"]
    require(manifest07.get("fixedCommit") is None, "Category 07 manifest original fixed commit must be null")
    require("unavailable" in manifest07.get("fixedCommitStatus", "").lower(), "Category 07 manifest must explain the unavailable original commit")
    require(manifest07.get("equivalentReconstructedCommit") == category07["provenance"]["publicSource"]["fixedCommitSha"], "Category 07 reconstructed commit must agree across manifest and candidate")
    require(manifest07.get("stablePatchId") == category07["verification"]["localChecks"].get("stablePatchId"), "Category 07 stable patch ID must agree across manifest and candidate")
    return candidate_paths, manifest_paths


def validate_schema_and_semantics(candidate_paths: list[Path]) -> None:
    run([
        "npx", "--yes", "ajv-cli@5.0.0", "validate", "--all-errors",
        "-s", "experiences/verified-experience.schema.json",
        "-d", "dogfood/self-consumption-batch-01/candidates/*.json",
    ])
    for path in candidate_paths:
        run([sys.executable, "scripts/validate_verified_experiences.py", "--library", str(path.relative_to(REPO))])


def validate_git(base_ref: str) -> None:
    run(["git", "rev-parse", "--verify", base_ref])
    run(["git", "diff", "--check"])
    run(["git", "diff", "--cached", "--check"])
    run(["git", "diff", "--check", base_ref])
    result = subprocess.run(
        ["git", "diff", "--quiet", base_ref, "--", "experiences/verified.json"],
        cwd=REPO,
    )
    require(result.returncode == 0, "experiences/verified.json differs from the base ref")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main", help="base commit/ref used for diff checks")
    args = parser.parse_args()
    files = validate_file_layout()
    candidates, manifests = validate_records()
    validate_schema_and_semantics(candidates)
    validate_git(args.base_ref)
    print(json.dumps({
        "status": "passed",
        "files": len(files),
        "candidates": len(candidates),
        "manifests": len(manifests),
        "baseRef": args.base_ref,
        "modelOrAgentExecution": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.CalledProcessError) as exc:
        print(f"Batch 01 evidence validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
