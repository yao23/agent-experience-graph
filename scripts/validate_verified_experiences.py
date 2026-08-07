#!/usr/bin/env python3
"""Apply semantic and redaction checks not expressible in JSON Schema."""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = ROOT / "experiences" / "verified.json"
ID_RE = re.compile(r"^trace-[a-z0-9][a-z0-9.-]+$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
FORBIDDEN_KEYS = {
    "rawprompt", "rawprompts", "rawjsonl", "stderr", "log", "logs", "rawlog", "rawlogs",
    "patch", "sourcepatch", "credential", "credentials", "secret", "secrets",
    "workspacepath", "privatepath", "privatesource", "privateworkspace",
}
PRIVATE_PATH_RE = re.compile(r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\)")
TOKEN_RE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})")
EVIDENCE_FILE_FIELDS = (
    "experimentArtifact",
    "experienceSchema",
    "semanticValidator",
    "pairedResultsValidator",
    "resultValidator",
)


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def inspect_public_value(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            require(normalized not in FORBIDDEN_KEYS, f"{path}.{key} is a forbidden public field")
            inspect_public_value(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            inspect_public_value(child, f"{path}[{index}]")
    elif isinstance(value, str):
        require(not PRIVATE_PATH_RE.search(value), f"{path} contains a private workspace path")
        require(not TOKEN_RE.search(value), f"{path} contains a credential-like token")


def validate_evidence_files(library, root=ROOT):
    """Require promoted-library evidence references to resolve inside the repository."""
    root = Path(root).resolve()
    for index, experience in enumerate(library):
        evidence = experience.get("verification", {}).get("evidence", {})
        for field in EVIDENCE_FILE_FIELDS:
            value = evidence.get(field)
            if value is None:
                continue
            path = f"experiences[{index}].verification.evidence.{field}"
            require(isinstance(value, str) and value, f"{path} must be a non-empty path")
            relative = Path(value)
            require(not relative.is_absolute() and ".." not in relative.parts, f"{path} must stay repository-relative")
            require((root / relative).is_file(), f"{path} does not resolve to a file: {value}")


def validate_library(library):
    require(isinstance(library, list) and library, "verified experience library must be a non-empty array")
    inspect_public_value(library)
    seen_ids = set()
    for index, experience in enumerate(library):
        path = f"experiences[{index}]"
        require(isinstance(experience, dict), f"{path} must be an object")
        experience_id = experience.get("id")
        require(isinstance(experience_id, str) and ID_RE.fullmatch(experience_id), f"{path}.id is not stable")
        require(experience_id not in seen_ids, f"duplicate experience ID: {experience_id}")
        seen_ids.add(experience_id)
        require(experience.get("outcome") in {"success", "partial", "failure"}, f"{path}.outcome is invalid")

        provenance = experience.get("provenance", {})
        for category in ("publicSource", "experimentEvidence", "promotionEvidence"):
            require(isinstance(provenance.get(category), dict), f"{path}.provenance.{category} is required")
        experiment = provenance["experimentEvidence"]
        promotion = provenance["promotionEvidence"]
        source_sha = experiment.get("runnerSourceCommitSha")
        require(source_sha is None or (isinstance(source_sha, str) and COMMIT_RE.fullmatch(source_sha)), f"{path} has an invalid runner source commit SHA")
        if source_sha is None:
            require("unavailable" in experiment.get("runnerSourceCommitStatus", "").lower(), f"{path} must explain unavailable runner commit metadata")
        promoted_sha = promotion.get("validatedCommitSha")
        status = promotion.get("status")
        if status == "expected-on-pull-request":
            require(promoted_sha is None, f"{path} cannot claim a validated commit before its workflow runs")
        else:
            require(isinstance(promoted_sha, str) and COMMIT_RE.fullmatch(promoted_sha), f"{path} observed promotion evidence requires a commit SHA")
        require("workflowRun" not in provenance and "workflowRunId" not in provenance, f"{path} uses ambiguous workflow provenance")

        verification = experience.get("verification", {})
        require(verification.get("status") in {"passed", "failed", "partial"}, f"{path}.verification.status is invalid")
        evidence = verification.get("evidence", {})
        require(evidence.get("experimentArtifact") == experiment.get("artifact"), f"{path} verification artifact does not match experiment provenance")

        metrics = experience.get("metrics", {})
        is_paired = "pairedTrials" in metrics
        if is_paired:
            for name in ("pairedTrials", "baselineArms", "assistedArms", "baselineArmsVerified", "assistedArmsVerified"):
                require(isinstance(metrics.get(name), int) and not isinstance(metrics.get(name), bool), f"{path}.metrics.{name} must be an integer")
            deltas = metrics.get("pairedMedianAssistedMinusBaseline", {})
            for name in ("completedCommands", "actualTestExecutions", "nonCachedTokens", "durationMs"):
                require(is_number(deltas.get(name)), f"{path}.metrics.{name} delta must be numeric")
            require(metrics["baselineArms"] == metrics["pairedTrials"] == metrics["assistedArms"], f"{path} arm counts do not match paired trial count")
            require(metrics["baselineArmsVerified"] <= metrics["baselineArms"], f"{path} baseline verified count exceeds arm count")
            require(metrics["assistedArmsVerified"] <= metrics["assistedArms"], f"{path} assisted verified count exceeds arm count")
        else:
            for name in ("attempts", "completedCommands", "actualTestExecutions"):
                require(isinstance(metrics.get(name), int) and not isinstance(metrics.get(name), bool) and metrics[name] >= 0, f"{path}.metrics.{name} must be a non-negative integer")
            for name in ("durationMs", "nonCachedTokens"):
                require(metrics.get(name) is None or (isinstance(metrics.get(name), int) and not isinstance(metrics.get(name), bool) and metrics[name] >= 0), f"{path}.metrics.{name} must be null or a non-negative integer")

        limitations = experience.get("limitations", [])
        require(isinstance(limitations, list) and limitations, f"{path}.limitations is required")
        limitation_text = " ".join(limitations).lower()
        if is_paired and deltas["durationMs"] > 0:
            require("regress" in limitation_text, f"{path} must disclose the duration regression")
        if is_paired and metrics["baselineArmsVerified"] == metrics["assistedArmsVerified"]:
            require("no success-rate improvement" in limitation_text, f"{path} must disclose no success-rate improvement")

        reuse = experience.get("reuse", {})
        for field in ("retrievalTags", "recommendedFor"):
            values = reuse.get(field)
            require(isinstance(values, list) and values and all(isinstance(item, str) and item for item in values), f"{path}.reuse.{field} must be a non-empty string array")
    return {"status": "passed", "experienceCount": len(library), "uniqueIds": len(seen_ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", default=str(DEFAULT_LIBRARY))
    args = parser.parse_args()
    library_path = Path(args.library)
    library = json.loads(library_path.read_text(encoding="utf-8"))
    if library_path.resolve() == DEFAULT_LIBRARY.resolve():
        validate_evidence_files(library)
    print(json.dumps(validate_library(library), indent=2))


if __name__ == "__main__":
    main()
