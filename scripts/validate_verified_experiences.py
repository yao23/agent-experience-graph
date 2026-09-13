#!/usr/bin/env python3
"""Apply semantic and redaction checks not expressible in JSON Schema."""

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_LIBRARY = ROOT / "experiences" / "registry.json"
ID_RE = re.compile(r"^trace-[a-z0-9][a-z0-9.-]+$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
PROVENANCE_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
PROVENANCE_REFS = {
    "models_and_harnesses_ref": "/context/agent_context",
    "environment_ref": "/context/environment_fingerprint",
    "verification_ref": "/verification_method",
    "negative_results_ref": "/failed_attempts",
}
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


def validate_safe_url(value, path, allow_fragment=False):
    require(isinstance(value, str), f"{path} must be a URL string")
    require(not re.search(r"[\s\x00-\x1f\x7f\\]", value), f"{path} contains invalid URL characters")
    try:
        parsed = urlsplit(value)
        valid_host = bool(parsed.hostname)
        parsed.port  # Reject malformed or out-of-range ports.
    except ValueError as error:
        raise ValidationError(f"{path} is not a valid URL") from error
    require(parsed.scheme == "https" and valid_host, f"{path} must be an absolute HTTPS URL")
    require(parsed.username is None and parsed.password is None, f"{path} must not contain URL credentials")
    require(allow_fragment or not parsed.fragment, f"{path} must not contain a fragment")


def validate_provenance_timestamp(value, path):
    require(isinstance(value, str) and PROVENANCE_TIMESTAMP_RE.fullmatch(value), f"{path} must be an ISO timestamp with a timezone")
    validate_timestamp(value, path)


def validate_digest_metadata(digest, path):
    """Check public metadata without accessing artifact files."""
    require(isinstance(digest, dict), f"{path} must be an object")
    artifact = digest.get("artifact")
    require(isinstance(artifact, str) and artifact, f"{path}.artifact must be a non-empty path")
    relative = Path(artifact)
    require(
        not relative.is_absolute() and not PureWindowsPath(artifact).drive
        and ".." not in relative.parts and "\\" not in artifact
        and not re.search(r"[\x00-\x1f\x7f]", artifact),
        f"{path}.artifact must stay repository-relative",
    )
    sha256 = digest.get("sha256")
    require(isinstance(sha256, str) and SHA256_RE.fullmatch(sha256), f"{path}.sha256 must be a SHA-256 hex digest")
    require(isinstance(digest.get("scope"), str) and digest["scope"], f"{path}.scope must be a non-empty string")


def validate_provenance_record(experience, path):
    """Validate disclosures; this does not establish truth, independence, or rights."""
    provenance = experience.get("provenance", {})
    if "record" not in provenance:
        return
    record = provenance["record"]
    path = f"{path}.provenance.record"
    require(isinstance(record, dict), f"{path} must be an object")
    require(record.get("schema_version") == "1.0.0", f"{path}.schema_version is unsupported")
    for field, expected in PROVENANCE_REFS.items():
        require(record.get(field) == expected, f"{path}.{field} must reference {expected}")
        target = experience
        for component in expected.lstrip("/").split("/"):
            require(isinstance(target, dict) and component in target, f"{path}.{field} does not resolve")
            target = target[component]
        require(target is not None, f"{path}.{field} does not resolve to an existing value")

    def public_url(value, location):
        validate_safe_url(value, location, allow_fragment=True)

    def public_urls(values, location):
        require(isinstance(values, list), f"{location} must be an array")
        for index, value in enumerate(values):
            public_url(value, f"{location}[{index}]")

    def commit(value, location):
        require(value is None or (isinstance(value, str) and COMMIT_RE.fullmatch(value)), f"{location} must be null or a full commit SHA")

    origin = record.get("task_origin")
    require(isinstance(origin, dict), f"{path}.task_origin must be an object")
    public_url(origin.get("url"), f"{path}.task_origin.url")
    commit(origin.get("revision"), f"{path}.task_origin.revision")
    prior_art = record.get("prior_art")
    require(isinstance(prior_art, list), f"{path}.prior_art must be an array")
    for index, source in enumerate(prior_art):
        source_path = f"{path}.prior_art[{index}]"
        require(isinstance(source, dict), f"{source_path} must be an object")
        public_url(source.get("url"), f"{source_path}.url")
        commit(source.get("revision"), f"{source_path}.revision")
    contributors = record.get("contributors")
    require(isinstance(contributors, list) and contributors, f"{path}.contributors must be a non-empty array")
    for index, contributor in enumerate(contributors):
        contributor_path = f"{path}.contributors[{index}]"
        require(isinstance(contributor, dict), f"{contributor_path} must be an object")
        public_urls(contributor.get("evidence_urls"), f"{contributor_path}.evidence_urls")
    digests = record.get("trace_digest")
    require(isinstance(digests, list) and digests, f"{path}.trace_digest must be a non-empty array")
    for index, digest in enumerate(digests):
        validate_digest_metadata(digest, f"{path}.trace_digest[{index}]")

    replays = record.get("independent_replays")
    require(isinstance(replays, list), f"{path}.independent_replays must be an array")
    seen_replay_ids = set()
    for index, replay in enumerate(replays):
        replay_path = f"{path}.independent_replays[{index}]"
        require(isinstance(replay, dict), f"{replay_path} must be an object")
        replay_id = replay.get("id")
        require(isinstance(replay_id, str) and replay_id, f"{replay_path}.id is required")
        require(replay_id not in seen_replay_ids, f"{replay_path} has duplicate replay ID: {replay_id}")
        seen_replay_ids.add(replay_id)
        public_url(replay.get("source_url"), f"{replay_path}.source_url")
        validate_provenance_timestamp(replay.get("reported_at"), f"{replay_path}.reported_at")
        status = replay.get("evidence_status")
        require(status in {"SELF_REPORTED", "EVIDENCE_ATTACHED", "AUDITED"}, f"{replay_path}.evidence_status is invalid")
        commit(replay.get("tested_commit_sha"), f"{replay_path}.tested_commit_sha")
        artifacts = replay.get("artifacts")
        require(isinstance(artifacts, list), f"{replay_path}.artifacts must be an array")
        for artifact_index, artifact in enumerate(artifacts):
            validate_digest_metadata(artifact, f"{replay_path}.artifacts[{artifact_index}]")
        if status in {"EVIDENCE_ATTACHED", "AUDITED"}:
            require(replay.get("tested_commit_sha") is not None and artifacts, f"{replay_path} evidence status requires a tested commit SHA and artifacts")
        require("audit" in replay, f"{replay_path}.audit is required")
        audit = replay.get("audit")
        if status == "AUDITED":
            require(isinstance(audit, dict), f"{replay_path} AUDITED status requires an audit disclosure")
        if audit is not None:
            require(isinstance(audit, dict), f"{replay_path}.audit must be null or an object")
            for field in ("reviewer", "scope", "independence_basis"):
                require(isinstance(audit.get(field), str) and audit[field], f"{replay_path}.audit.{field} is required")
            validate_provenance_timestamp(audit.get("reviewed_at"), f"{replay_path}.audit.reviewed_at")
            require(audit.get("evidence_urls"), f"{replay_path}.audit requires evidence URLs")
            public_urls(audit.get("evidence_urls"), f"{replay_path}.audit.evidence_urls")

    disputes = record.get("disputes_and_limits")
    require(isinstance(disputes, dict), f"{path}.disputes_and_limits must be an object")
    require(disputes.get("status") in {"NOT_ASSESSED", "NONE_REPORTED", "OPEN", "RESOLVED"}, f"{path}.disputes_and_limits.status is invalid")
    public_urls(disputes.get("evidence_urls"), f"{path}.disputes_and_limits.evidence_urls")
    licenses = record.get("license_and_consent")
    require(isinstance(licenses, dict), f"{path}.license_and_consent must be an object")
    upstream = licenses.get("upstream_licenses")
    require(isinstance(upstream, list), f"{path}.license_and_consent.upstream_licenses must be an array")
    for index, source in enumerate(upstream):
        source_path = f"{path}.license_and_consent.upstream_licenses[{index}]"
        require(isinstance(source, dict), f"{source_path} must be an object")
        public_url(source.get("evidence_url"), f"{source_path}.evidence_url")
    consent_status = licenses.get("consent_status")
    require(consent_status in {"NOT_REQUESTED", "GRANTED", "NOT_REQUIRED", "UNKNOWN"}, f"{path}.license_and_consent.consent_status is invalid")
    consent_evidence = licenses.get("consent_evidence_urls")
    public_urls(consent_evidence, f"{path}.license_and_consent.consent_evidence_urls")
    if consent_status == "GRANTED":
        require(consent_evidence, f"{path}.license_and_consent GRANTED consent requires evidence URLs")


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
    def require_local_refs(value):
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                require(isinstance(reference, str) and reference.startswith("#/"), "JSON Schema references must be local; network resolution is disabled")
            for child in value.values():
                require_local_refs(child)
        elif isinstance(value, list):
            for child in value:
                require_local_refs(child)

    require_local_refs(schema)
    errors = sorted(Draft7Validator(schema).iter_errors(library), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValidationError(f"JSON Schema validation failed at {location}: {error.message}")
    return {"status": "passed", "schema": str(schema_path.relative_to(ROOT))}


def validate_evidence_files(library, root=ROOT):
    """Check repository-contained evidence files and the content integrity of digests."""
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
        record = experience.get("provenance", {}).get("record")
        if record is None:
            continue
        record_path = f"experiences[{index}].provenance.record"
        digests = [
            (digest, f"{record_path}.trace_digest[{digest_index}]")
            for digest_index, digest in enumerate(record.get("trace_digest", []))
        ]
        for replay_index, replay in enumerate(record.get("independent_replays", [])):
            digests.extend(
                (digest, f"{record_path}.independent_replays[{replay_index}].artifacts[{digest_index}]")
                for digest_index, digest in enumerate(replay.get("artifacts", []))
            )
        for digest, digest_path in digests:
            validate_digest_metadata(digest, digest_path)
            artifact = digest["artifact"]
            validate_repository_reference(artifact, f"{digest_path}.artifact", root)
            try:
                actual = hashlib.sha256((root / artifact).read_bytes()).hexdigest()
            except OSError as error:
                raise ValidationError(f"{digest_path}.artifact cannot be read") from error
            require(actual == digest["sha256"], f"{digest_path}.sha256 does not match artifact bytes")


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
        validate_provenance_record(experience, path)

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
    parser.add_argument(
        "--check-evidence", action="store_true",
        help="Check repository-contained evidence files and artifact digests for the selected library.",
    )
    args = parser.parse_args()
    library_path = Path(args.library)
    library = json.loads(library_path.read_text(encoding="utf-8"))
    schema_result = validate_json_schema(library)
    result = validate_library(library)
    result["schemaValidation"] = schema_result["status"]
    is_default_library = library_path.resolve() == DEFAULT_LIBRARY.resolve()
    if is_default_library or args.check_evidence:
        validate_evidence_files(library, root=ROOT)
    if is_default_library:
        from experiences.safety.known_partial_gate import validate_safety_artifacts

        result["recommendationSafety"] = validate_safety_artifacts()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
