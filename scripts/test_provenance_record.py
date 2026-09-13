"""Exercise provenance disclosures and local evidence integrity without network access."""

import copy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "aeg_provenance_validator", ROOT / "scripts" / "validate_verified_experiences.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
ARTIFACT_BYTES = b"Sanitized replay evidence.\n"


class ProvenanceRecordTest(unittest.TestCase):
    def setUp(self):
        self.legacy = json.loads((ROOT / "experiences" / "registry.json").read_text())
        self.experience = copy.deepcopy(self.legacy[0])
        digest = {
            "artifact": "evidence/replay.txt",
            "sha256": hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
            "scope": "Exact sanitized evidence bytes; no authorship claim.",
        }
        self.record = {
            "schema_version": "1.0.0",
            "claim": "A bounded reproduction report with explicit unknowns.",
            "task_origin": {
                "url": "https://github.com/example/project/issues/1#issuecomment-2",
                "revision": None,
                "description": "Public task report.",
            },
            "prior_art": [],
            "contributors": [{
                "identity": "Example reporter",
                "role": "reporter",
                "contribution": "Shared a sanitized report.",
                "evidence_urls": [],
            }],
            "models_and_harnesses_ref": "/context/agent_context",
            "environment_ref": "/context/environment_fingerprint",
            "trace_digest": [digest],
            "verification_ref": "/verification_method",
            "independent_replays": [{
                "id": "replay-1",
                "reporter": "Example reporter",
                "source_url": "https://github.com/example/project/issues/1#issuecomment-3",
                "reported_at": "2026-09-09T12:30:00Z",
                "evidence_status": "SELF_REPORTED",
                "tested_commit_sha": None,
                "environment": "Reporter did not provide a complete environment.",
                "result": "Reporter says the local check passed.",
                "artifacts": [],
                "audit": None,
                "limitations": ["The report has not been independently audited."],
            }],
            "negative_results_ref": "/failed_attempts",
            "disputes_and_limits": {
                "status": "NOT_ASSESSED",
                "notes": ["No dispute review was performed."],
                "evidence_urls": [],
            },
            "license_and_consent": {
                "record_license": "CC0-1.0",
                "upstream_licenses": [],
                "consent_status": "NOT_REQUESTED",
                "consent_evidence_urls": [],
                "reuse_limits": ["Upstream evidence retains its own rights and restrictions."],
            },
        }
        self.experience["provenance"]["record"] = self.record

    def validate(self):
        VALIDATOR.validate_json_schema([self.experience])
        return VALIDATOR.validate_library([self.experience])

    def artifact_library(self, digest=None):
        """Exercise the public file validator independently of unrelated legacy files."""
        record = copy.deepcopy(self.record)
        if digest is not None:
            record["trace_digest"] = [digest]
        return [{"provenance": {"record": record}}]

    def test_legacy_library_remains_valid_and_unmodified(self):
        library = self.legacy
        for experience in library:
            experience["provenance"].pop("record", None)
        original = copy.deepcopy(library)
        VALIDATOR.validate_json_schema(library)
        VALIDATOR.validate_library(library)
        self.assertEqual(library, original)

    def test_optional_record_is_metadata_only_and_does_not_promote(self):
        original = copy.deepcopy(self.experience)
        with patch.object(VALIDATOR, "validate_repository_reference", side_effect=AssertionError("unexpected file access")):
            self.assertEqual(self.validate()["status"], "passed")
        self.assertEqual(self.experience, original)

    def test_every_record_field_is_required(self):
        for field in self.record:
            with self.subTest(field=field):
                experience = copy.deepcopy(self.experience)
                del experience["provenance"]["record"][field]
                with self.assertRaises(VALIDATOR.ValidationError):
                    VALIDATOR.validate_json_schema([experience])

    def test_wrong_version_and_reference_are_rejected(self):
        self.record["schema_version"] = "2.0.0"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "schema_version"):
            VALIDATOR.validate_library([self.experience])
        self.record["schema_version"] = "1.0.0"
        self.record["verification_ref"] = "/verification"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "verification_ref"):
            VALIDATOR.validate_library([self.experience])
        self.record["verification_ref"] = "/verification_method"
        del self.experience["verification_method"]
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "does not resolve"):
            VALIDATOR.validate_library([self.experience])

    def test_reported_promotion_remains_explicitly_reported(self):
        promotion = self.experience["provenance"]["promotionEvidence"]
        promotion.update({
            "status": "reported-passed",
            "validatedCommitSha": self.experience["context"]["source_revision"]["commit_sha"],
            "runResolver": "https://github.com/example/project/issues/1",
        })
        self.validate()
        self.assertEqual(promotion["status"], "reported-passed")

    def test_attached_or_audited_replay_requires_supporting_evidence(self):
        replay = self.record["independent_replays"][0]
        for status in ("EVIDENCE_ATTACHED", "AUDITED"):
            for sha, artifacts in ((None, []), ("a" * 40, []), (None, self.record["trace_digest"])):
                with self.subTest(status=status, sha=sha, artifacts=bool(artifacts)):
                    replay.update(evidence_status=status, tested_commit_sha=sha, artifacts=artifacts)
                    with self.assertRaisesRegex(VALIDATOR.ValidationError, "requires a tested commit SHA and artifacts"):
                        VALIDATOR.validate_library([self.experience])

    def test_audited_replay_requires_audit_disclosure(self):
        replay = self.record["independent_replays"][0]
        replay.update(evidence_status="AUDITED", tested_commit_sha="a" * 40, artifacts=self.record["trace_digest"])
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "requires an audit disclosure"):
            VALIDATOR.validate_library([self.experience])
        with self.assertRaises(VALIDATOR.ValidationError):
            VALIDATOR.validate_json_schema([self.experience])
        replay["audit"] = {
            "reviewer": "Named reviewer",
            "reviewed_at": "2026-09-10T10:00:00+01:00",
            "scope": "Review of the attached sanitized test result.",
            "independence_basis": "Reviewer reports no participation in the original run.",
            "evidence_urls": ["https://github.com/example/project/issues/1#issuecomment-4"],
        }
        self.validate()
        replay["audit"]["evidence_urls"] = []
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "audit requires evidence URLs"):
            VALIDATOR.validate_library([self.experience])

    def test_duplicate_replay_ids_are_rejected(self):
        duplicate = copy.deepcopy(self.record["independent_replays"][0])
        duplicate["result"] = "A different claim still needs its own identifier."
        self.record["independent_replays"].append(duplicate)
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate replay ID"):
            VALIDATOR.validate_library([self.experience])

    def test_timestamps_require_valid_calendar_values_and_timezone(self):
        replay = self.record["independent_replays"][0]
        for timestamp in ("2026-09-09T12:30:00", "2026-02-30T12:30:00Z", "2026-09-09 12:30:00Z"):
            with self.subTest(timestamp=timestamp):
                replay["reported_at"] = timestamp
                with self.assertRaises(VALIDATOR.ValidationError):
                    VALIDATOR.validate_library([self.experience])

    def test_url_fragments_work_but_credentials_and_unsafe_urls_do_not(self):
        self.validate()
        for url in ("http://example.com/report", "https://user:password@example.com/report", "https://@example.com/report", "https://example.com/\nreport"):
            with self.subTest(url=url):
                self.record["task_origin"]["url"] = url
                with self.assertRaises(VALIDATOR.ValidationError):
                    VALIDATOR.validate_library([self.experience])

    def test_secret_and_private_path_redaction_applies_to_record(self):
        for claim in ("source /home/alice/private/project/report", "ghp_" + "a" * 24):
            with self.subTest(claim=claim):
                self.record["claim"] = claim
                with self.assertRaisesRegex(VALIDATOR.ValidationError, "private workspace path|credential-like token"):
                    VALIDATOR.validate_library([self.experience])

    def test_granted_consent_requires_evidence(self):
        licenses = self.record["license_and_consent"]
        licenses["consent_status"] = "GRANTED"
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "GRANTED consent requires evidence URLs"):
            VALIDATOR.validate_library([self.experience])
        licenses["consent_evidence_urls"] = ["https://github.com/example/project/issues/1#issuecomment-5"]
        self.validate()

    def test_digest_checks_actual_bytes_and_replay_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "evidence" / "replay.txt"
            artifact.parent.mkdir()
            artifact.write_bytes(ARTIFACT_BYTES)
            library = self.artifact_library()
            VALIDATOR.validate_evidence_files(library, root)
            record = library[0]["provenance"]["record"]
            record["independent_replays"][0]["artifacts"] = [{
                **record["trace_digest"][0], "sha256": "0" * 64,
            }]
            with self.assertRaisesRegex(VALIDATOR.ValidationError, r"independent_replays\[0\].artifacts\[0\].sha256 does not match"):
                VALIDATOR.validate_evidence_files(library, root)
            record["independent_replays"][0]["artifacts"] = []
            artifact.write_bytes(ARTIFACT_BYTES + b"changed\n")
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "does not match artifact bytes"):
                VALIDATOR.validate_evidence_files(library, root)

    def test_artifact_traversal_absolute_paths_and_symlink_escape_are_rejected(self):
        digest = self.record["trace_digest"][0]
        for artifact in ("../outside.txt", "/tmp/outside.txt", "C:\\outside.txt", "..\\outside.txt"):
            with self.subTest(artifact=artifact):
                digest["artifact"] = artifact
                with self.assertRaisesRegex(VALIDATOR.ValidationError, "repository-relative"):
                    VALIDATOR.validate_library([self.experience])
        with tempfile.TemporaryDirectory() as directory:
            outer = Path(directory)
            root = outer / "repo"
            root.mkdir()
            outside = outer / "outside.txt"
            outside.write_bytes(ARTIFACT_BYTES)
            (root / "escape.txt").symlink_to(outside)
            digest["artifact"] = "escape.txt"
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "outside the repository"):
                VALIDATOR.validate_evidence_files(self.artifact_library(), root)

    def test_external_schema_references_are_rejected_before_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            schema_path = Path(directory) / "external-schema.json"
            schema_path.write_text(json.dumps({"$ref": "https://example.invalid/schema.json"}))
            with patch("urllib.request.urlopen", side_effect=AssertionError("network access forbidden")):
                with self.assertRaisesRegex(VALIDATOR.ValidationError, "references must be local"):
                    VALIDATOR.validate_json_schema([self.experience], schema_path)

    def test_cli_check_evidence_checks_custom_library_digests(self):
        schema_bytes = (ROOT / "experiences" / "verified-experience.schema.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = self.experience["verification"]["evidence"]
            refs = [evidence[field] for field in VALIDATOR.EVIDENCE_FILE_FIELDS if field in evidence]
            refs.extend(self.experience["verification_method"]["evidence_refs"])
            for reference in refs:
                file_path = root / reference
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(b"Local evidence fixture.\n")
            schema_path = root / "experiences" / "verified-experience.schema.json"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_bytes(schema_bytes)
            artifact = root / self.record["trace_digest"][0]["artifact"]
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(b"These bytes do not match the declared digest.\n")
            library_path = root / "candidate.json"
            library_path.write_text(json.dumps([self.experience]))
            argv = ["validate_verified_experiences.py", "--library", str(library_path)]
            with patch.object(VALIDATOR, "ROOT", root):
                output = io.StringIO()
                with patch.object(sys, "argv", argv), redirect_stdout(output):
                    VALIDATOR.main()
                self.assertEqual(json.loads(output.getvalue())["status"], "passed")
                with patch.object(sys, "argv", argv + ["--check-evidence"]):
                    with self.assertRaisesRegex(VALIDATOR.ValidationError, "does not match artifact bytes"):
                        VALIDATOR.main()
                artifact.write_bytes(ARTIFACT_BYTES)
                output = io.StringIO()
                with patch.object(sys, "argv", argv + ["--check-evidence"]), redirect_stdout(output):
                    VALIDATOR.main()
                self.assertNotIn("recommendationSafety", json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
