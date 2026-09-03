#!/usr/bin/env python3
"""Apply semantic and redaction checks not expressible in JSON Schema."""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_LIBRARY = ROOT / "experiences" / "registry.json"
ID_RE = re.compile(r"^trace-[a-z0-9][a-z0-9.-]+$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCHEMA_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
VERIFICATION_STATES = {
    "LOCALLY_VERIFIED",
    "CROSS_RUN_VERIFIED",
    "CROSS_MODEL_TRANSFERRED",
    "EXTERNALLY_REPRODUCED",
    "STALE_OR_FAILED_REPLAY",
}
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


def validate_timestamp(value, path):
    require(isinstance(value, str), f"{path} must be a timestamp string")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(f"{path} is not a valid timestamp") from error
    require(parsed.tzinfo is not None, f"{path} must include a timezone")


def validate_safe_url(value, path):
    require(isinstance(value, str), f"{path} must be a URL string")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and bool(parsed.netloc), f"{path} must be an absolute HTTPS URL")
    require(not parsed.username and not parsed.password, f"{path} must not contain URL credentials")
    require(not parsed.fragment, f"{path} must not contain a fragment")


def validate_repository_reference(value, path, root=ROOT):
    require(isinstance(value, str) and value, f"{path} must be a non-empty path")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{path} must stay repository-relative")
    try:
        resolved_root = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValidationError(f"{path} repository root cannot be resolved") from error
    require(resolved_root.is_dir(), f"{path} repository root must resolve to a directory")
    try:
        resolved_candidate = (resolved_root / relative).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValidationError(f"{path} does not resolve to a file: {value}") from error
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValidationError(f"{path} resolves outside the repository: {value}") from error
    require(resolved_candidate.is_file(), f"{path} does not resolve to a file: {value}")


def validate_json_schema(library, schema_path=None):
    from jsonschema import Draft7Validator

    schema_path = Path(schema_path or ROOT / "experiences" / "verified-experience.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(library), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValidationError(f"JSON Schema validation failed at {location}: {error.message}")
    return {"status": "passed", "schema": str(schema_path.relative_to(ROOT))}


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
            validate_repository_reference(value, path, root)
        for ref_index, value in enumerate(experience.get("verification_method", {}).get("evidence_refs", [])):
            validate_repository_reference(
                value,
                f"experiences[{index}].verification_method.evidence_refs[{ref_index}]",
                root,
            )


def validate_library(library):
    require(isinstance(library, list) and library, "verified experience library must be a non-empty array")
    inspect_public_value(library)
    seen_ids = set()
    seen_slugs = set()
    for index, experience in enumerate(library):
        path = f"experiences[{index}]"
        require(isinstance(experience, dict), f"{path} must be an object")
        schema_version = experience.get("schema_version")
        require(isinstance(schema_version, str) and SCHEMA_VERSION_RE.fullmatch(schema_version), f"{path}.schema_version is invalid")
        experience_id = experience.get("id")
        require(isinstance(experience_id, str) and ID_RE.fullmatch(experience_id), f"{path}.id is not stable")
        require(experience_id not in seen_ids, f"duplicate experience ID: {experience_id}")
        seen_ids.add(experience_id)
        slug = experience.get("slug")
        require(isinstance(slug, str) and SLUG_RE.fullmatch(slug), f"{path}.slug is invalid")
        require(slug not in seen_slugs, f"duplicate experience slug: {slug}")
        seen_slugs.add(slug)
        require(experience.get("verification_status") in VERIFICATION_STATES, f"{path}.verification_status is invalid")
        validate_timestamp(experience.get("last_verified_at"), f"{path}.last_verified_at")
        require(experience.get("outcome") in {"success", "partial", "failure"}, f"{path}.outcome is invalid")

        context = experience.get("context", {})
        validate_safe_url(context.get("repository"), f"{path}.context.repository")
        public_source = experience.get("provenance", {}).get("publicSource", {})
        require(experience.get("license") == public_source.get("license"), f"{path}.license must match public source license")
        require(context.get("source_revision", {}).get("commit_sha") in {
            public_source.get("buggyCommitSha"),
            public_source.get("fixedCommitSha"),
            experience.get("provenance", {}).get("promotionEvidence", {}).get("validatedCommitSha"),
        }, f"{path}.context.source_revision.commit_sha lacks provenance integrity")

        for url_path, value in (
            (f"{path}.provenance.repository", experience.get("provenance", {}).get("repository")),
            (f"{path}.provenance.publicSource.repository", public_source.get("repository")),
            (f"{path}.provenance.publication.pullRequest", experience.get("provenance", {}).get("publication", {}).get("pullRequest")),
        ):
            validate_safe_url(value, url_path)

        failed_attempts = experience.get("failed_attempts")
        require(isinstance(failed_attempts, list) and failed_attempts, f"{path}.failed_attempts is required")
        recovery_steps = experience.get("recovery_steps")
        require(isinstance(recovery_steps, list) and recovery_steps, f"{path}.recovery_steps is required")

        registry_metrics = experience.get("registry_metrics", {})
        require(set(registry_metrics) == {"tokens", "commands", "retries", "wall_time"}, f"{path}.registry_metrics must cover token, command, retry, and wall-time metrics")
        for metric_name, metric in registry_metrics.items():
            metric_path = f"{path}.registry_metrics.{metric_name}"
            require(metric.get("status") in {"measured", "unknown"}, f"{metric_path}.status is invalid")
            value = metric.get("value")
            if metric.get("status") == "unknown":
                require(value is None, f"{metric_path}.value must be null when status is unknown")
            else:
                require(is_number(value), f"{metric_path}.value must be numeric when measured")

        provenance = experience.get("provenance", {})
        for category in ("publicSource", "experimentEvidence", "promotionEvidence"):
            require(isinstance(provenance.get(category), dict), f"{path}.provenance.{category} is required")
        experiment = provenance["experimentEvidence"]
        promotion = provenance["promotionEvidence"]
        validate_timestamp(provenance.get("recordedAt"), f"{path}.provenance.recordedAt")
        validate_timestamp(experiment.get("sourceReportCreatedAt"), f"{path}.provenance.experimentEvidence.sourceReportCreatedAt")
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
            validate_safe_url(promotion.get("runResolver"), f"{path}.provenance.promotionEvidence.runResolver")
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
    schema_result = validate_json_schema(library)
    result = validate_library(library)
    result["schemaValidation"] = schema_result["status"]
    if library_path.resolve() == DEFAULT_LIBRARY.resolve():
        validate_evidence_files(library)
        from experiences.safety.known_partial_gate import validate_safety_artifacts

        result["recommendationSafety"] = validate_safety_artifacts()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
