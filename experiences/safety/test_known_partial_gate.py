#!/usr/bin/env python3
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("known_partial_gate.py")
SPEC = importlib.util.spec_from_file_location("aeg_known_partial_gate", SCRIPT)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_publication_fixture(root):
    relative_paths = [
        GATE.PROVENANCE_RECORD_PATH,
        *GATE.EXPECTED_DERIVATIVES,
    ]
    for relative_value in relative_paths:
        relative = Path(relative_value)
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(GATE.ROOT / relative, destination)
    return root / GATE.PROVENANCE_RECORD_PATH


def update_derived_hash(root, relative_value):
    provenance_path = root / GATE.PROVENANCE_RECORD_PATH
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    derivative_path = root / relative_value
    for row in provenance["derivatives"]:
        if row["path"] == relative_value:
            row["derived_sha256"] = GATE.sha256_file(derivative_path)
            break
    else:
        raise AssertionError(f"missing derivative record: {relative_value}")
    write_json(provenance_path, provenance)


def complete_profile(experience_id="trace-complete"):
    return {
        "schema_version": "1.0.0",
        "experience_id": experience_id,
        "experience_version_sha256": "1" * 64,
        "recommendation_eligible": True,
        "completeness_status": "complete",
        "repair_components": [
            {"component_id": "ownership_inventory", "source_evidence": "verified source"},
            {"component_id": "representation_contract", "source_evidence": "verified source"},
        ],
        "required_repair_components": ["ownership_inventory", "representation_contract"],
        "ownership_requirements": ["owner verified"],
        "lifetime_requirements": ["lifetime verified"],
        "representation_requirements": ["representation verified"],
        "required_local_checks": [
            {
                "check_id": "visible_contract",
                "description": "run the worker-visible contract",
                "executable": True,
                "worker_visible": True,
                "command": ["python3", "check.py"],
                "worker_visible_paths": ["check.py"],
                "demonstrates_invariants": ["complete_local_contract"],
                "evidence_provenance": "verified source check",
            }
        ],
        "known_partial_repair_ids": [],
        "applicability_conditions": ["local mechanism established"],
        "abstention_conditions": ["mechanism absent"],
        "failed_approaches": ["incomplete component-only repair"],
        "environment_assumptions": ["offline worker-visible fixture"],
        "uncertainty": "bounded to the verified fixture",
        "invariant_status": {
            "ownership": "verified",
            "lifetime": "verified",
            "representation": "verified",
            "compatibility": "verified",
            "environment": "verified",
        },
        "applicability_status": "verified",
        "negative_transfer_status": "none",
        "quarantine": None,
        "evidence_provenance": [
            {"artifact": "fixture.json", "artifact_sha256": "2" * 64, "supports": ["complete contract"]}
        ],
    }


def passing_context():
    return {
        "repair_component_coverage": ["ownership_inventory", "representation_contract"],
        "environment_match": True,
        "environment_assumptions_checked": True,
        "applicability_established": True,
        "local_check_results": [
            {
                "check_id": "visible_contract",
                "exit_code": 0,
                "worker_visible": True,
                "forbidden_sources_used": False,
                "environment_supported": True,
                "demonstrated_invariants": ["complete_local_contract"],
            }
        ],
    }


def executable_partial():
    return {
        "partial_repair_id": "kp-synthetic-fresh-context-v1",
        "semantic_signature": {
            "normalization_version": "aeg-semantic-concepts-v1",
            "required_concepts": ["instantiate_new_object", "per_operation_lifetime", "security_context"],
            "minimum_concept_coverage": 1.0,
        },
        "required_disconfirmation_checks": [
            {
                "check_id": "ownership_disconfirmation",
                "executable": True,
                "command": ["python3", "check.py"],
                "worker_visible_paths": ["check.py"],
                "demonstrates_invariants": ["configuration_ownership"],
            }
        ],
    }


class KnownPartialGateTests(unittest.TestCase):
    def setUp(self):
        self.profiles = GATE.load_profiles()
        self.partials = GATE.load_known_partials()

    def evaluate(self, profile, context=None, **kwargs):
        return GATE.evaluate_recommendation(
            relevant=True,
            experience_id=profile["experience_id"],
            profile=profile,
            task_context=context if context is not None else passing_context(),
            known_partials=kwargs.pop("known_partials", []),
            **kwargs,
        )

    def test_publication_sanitization_validates_derived_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            result = GATE.validate_publication_sanitization(provenance_path, root)
        self.assertEqual(result["status"], "valid_derived_public_safe_evidence_v1")
        self.assertEqual(result["derivatives"], 2)
        self.assertFalse(result["raw_originals_in_release"])

    def test_publication_sanitization_rejects_tampered_derived_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            audit_relative = next(path for path in GATE.EXPECTED_DERIVATIVES if path.endswith("/audit.json"))
            with (root / audit_relative).open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with self.assertRaisesRegex(GATE.GateValidationError, "derived evidence hash mismatch"):
                GATE.validate_publication_sanitization(provenance_path, root)

    def test_publication_sanitization_rejects_missing_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            provenance_path.unlink()
            with self.assertRaisesRegex(GATE.GateValidationError, "provenance is missing"):
                GATE.validate_publication_sanitization(provenance_path, root)

    def test_publication_sanitization_rejects_mismatched_original_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["derivatives"][0]["original_sha256"] = "0" * 64
            write_json(provenance_path, provenance)
            with self.assertRaisesRegex(GATE.GateValidationError, "original SHA-256 mismatch"):
                GATE.validate_publication_sanitization(provenance_path, root)

    def test_publication_sanitization_rejects_forbidden_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            manifest_relative = next(path for path in GATE.EXPECTED_DERIVATIVES if path.endswith("/manifest.json"))
            manifest_path = root / manifest_relative
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["local_path"] = "/Applications/PrivateTool/bin/tool"
            write_json(manifest_path, manifest)
            update_derived_hash(root, manifest_relative)
            with self.assertRaisesRegex(GATE.GateValidationError, "host-local path"):
                GATE.validate_publication_sanitization(provenance_path, root)

    def test_publication_sanitization_rejects_command_and_model_narrative_fields(self):
        for forbidden_key in ("command", "first_stated_approach"):
            with self.subTest(forbidden_key=forbidden_key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                provenance_path = copy_publication_fixture(root)
                audit_relative = next(path for path in GATE.EXPECTED_DERIVATIVES if path.endswith("/audit.json"))
                audit_path = root / audit_relative
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit[forbidden_key] = "removed process material"
                write_json(audit_path, audit)
                update_derived_hash(root, audit_relative)
                with self.assertRaisesRegex(GATE.GateValidationError, "forbidden in derived evidence"):
                    GATE.validate_publication_sanitization(provenance_path, root)

    def test_publication_sanitization_rejects_removed_limitation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = copy_publication_fixture(root)
            audit_relative = next(path for path in GATE.EXPECTED_DERIVATIVES if path.endswith("/audit.json"))
            audit_path = root / audit_relative
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["scientific_limitations"].pop()
            write_json(audit_path, audit)
            update_derived_hash(root, audit_relative)
            with self.assertRaisesRegex(GATE.GateValidationError, "required scientific limitations"):
                GATE.validate_publication_sanitization(provenance_path, root)

    def test_versioned_artifacts_validate_and_generation_fields_are_preserved(self):
        result = GATE.validate_safety_artifacts()
        self.assertEqual(result["status"], "valid_known_partial_disconfirmation_gate_v1")
        required = set(json.loads(GATE.POLICY_PATH.read_text())["generation_preservation_requirements"])
        for profile in self.profiles.values():
            self.assertLessEqual(required, set(profile))
            if profile["completeness_status"] != "complete":
                self.assertFalse(profile["recommendation_eligible"])

    def test_relevant_complete_experience_is_recommendable(self):
        decision = self.evaluate(complete_profile())
        self.assertEqual(decision["state"], "retrieved_and_recommended")

    def test_irrelevant_experience_is_withheld_before_retrieval(self):
        decision = GATE.evaluate_recommendation(
            relevant=False,
            experience_id="trace-complete",
            profile=complete_profile(),
            task_context=passing_context(),
            known_partials=[],
        )
        self.assertEqual(decision["state"], "not_retrieved_irrelevant")

    def test_partial_experience_without_disconfirmation_is_withheld(self):
        profile = complete_profile()
        profile["recommendation_eligible"] = False
        profile["completeness_status"] = "partial"
        profile["known_partial_repair_ids"] = [self.partials[0]["partial_repair_id"]]
        decision = self.evaluate(profile, known_partials=self.partials)
        self.assertIn("partial_or_unknown_completeness", decision["private_evidence"]["reasons"])
        self.assertIn("known_partial_without_executable_disconfirmation", decision["private_evidence"]["reasons"])

    def test_partial_experience_with_failing_disconfirmation_is_withheld(self):
        partial = executable_partial()
        profile = complete_profile()
        profile["recommendation_eligible"] = False
        profile["completeness_status"] = "partial"
        profile["known_partial_repair_ids"] = [partial["partial_repair_id"]]
        decision = self.evaluate(
            profile,
            known_partials=[partial],
            proposed_repair={"description": "Construct a fresh TLS context for every request."},
            disconfirmation_results=[
                {
                    "check_id": "ownership_disconfirmation",
                    "exit_code": 1,
                    "worker_visible": True,
                    "forbidden_sources_used": False,
                    "environment_supported": True,
                    "demonstrated_invariants": [],
                }
            ],
        )
        self.assertIn("known_partial_disconfirmation_failed", decision["private_evidence"]["reasons"])

    def test_partial_experience_with_missing_local_evidence_is_withheld(self):
        profile = complete_profile()
        context = passing_context()
        context["local_check_results"] = []
        decision = self.evaluate(profile, context)
        self.assertIn("missing_or_ambiguous_local_checks", decision["private_evidence"]["reasons"])

    def test_unresolved_environment_mismatch_is_withheld(self):
        context = passing_context()
        context["environment_match"] = False
        decision = self.evaluate(complete_profile(), context)
        self.assertIn("environment_mismatch", decision["private_evidence"]["reasons"])

    def test_incomplete_component_coverage_and_unresolved_invariant_are_withheld(self):
        profile = complete_profile()
        profile["invariant_status"]["ownership"] = "unresolved"
        context = passing_context()
        context["repair_component_coverage"] = ["ownership_inventory"]
        decision = self.evaluate(profile, context)
        self.assertIn("incomplete_repair_component_coverage", decision["private_evidence"]["reasons"])
        self.assertIn("unresolved_invariants", decision["private_evidence"]["reasons"])

    def test_quarantined_harmful_transfer_experience_is_withheld_at_high_precedence(self):
        profile = self.profiles["seb-requests-tls-efficiency-experience-v1"]
        decision = self.evaluate(profile, known_partials=self.partials)
        self.assertEqual(decision["state"], "retrieved_but_recommendation_withheld")
        self.assertEqual(decision["private_evidence"]["reasons"][0], "quarantined_harmful_transfer")
        self.assertEqual(profile["quarantine"]["quarantine_reason"], "observed_harmful_transfer")

    def test_retrieved_but_withheld_content_is_not_worker_visible(self):
        profile = self.profiles["seb-requests-tls-efficiency-experience-v1"]
        decision = self.evaluate(profile, known_partials=self.partials)
        self.assertEqual(decision["worker_payload"], {"notice": GATE.WORKER_WITHHELD_NOTICE})
        serialized = json.dumps(decision["worker_payload"])
        self.assertNotIn(profile["experience_id"], serialized)
        self.assertNotIn("ownership", serialized.lower())

    def test_semantic_paraphrases_of_known_partial_are_detected(self):
        paraphrases = [
            "Instantiate an SSL context on each invocation.",
            "For every call, construct a new security-context object.",
            "Build a fresh TLS context per request.",
        ]
        for text in paraphrases:
            with self.subTest(text=text):
                matches = GATE.match_known_partials({"plan": text}, self.partials)
                self.assertEqual(matches[0]["partial_repair_id"], self.partials[0]["partial_repair_id"])

    def test_superficial_textual_differences_do_not_evade_gate(self):
        variants = [
            "+ result = create_fresh_ssl_context()  # request-local",
            "ALLOCATE new TLS_CONTEXT per-operation",
            "Every request now constructs its own security context",
        ]
        signatures = [GATE.match_known_partials({"diff": text}, self.partials) for text in variants]
        self.assertTrue(all(signatures))

    def test_independent_correct_patch_is_not_falsely_labelled_leakage(self):
        decision = self.evaluate(
            complete_profile(),
            proposed_repair={
                "description": "Keep request-specific identity in immutable request configuration and preserve dependency representation.",
                "independently_produced": True,
            },
        )
        self.assertFalse(decision["private_evidence"]["output_similarity_is_leakage"])
        self.assertEqual(decision["private_evidence"]["known_partial_matches"], [])

    def test_worker_visible_disconfirmation_executes_without_raw_output(self):
        partial = executable_partial()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "check.py").write_text("print('sanitized check passed')\n", encoding="utf-8")
            bundle_audit = GATE.audit_worker_visible_bundle(root, ["check.py"])
            results = GATE.execute_worker_visible_checks(
                root,
                partial["required_disconfirmation_checks"],
                ["check.py"],
                {
                    **bundle_audit,
                    "protected_sources_unreachable": True,
                    "credentials_unavailable": True,
                },
            )
        self.assertEqual(results[0]["exit_code"], 0)
        self.assertNotIn("stdout", results[0])
        self.assertNotIn("stderr", results[0])
        self.assertEqual(results[0]["demonstrated_invariants"], ["configuration_ownership"])

    def test_worker_visible_disconfirmation_rejects_non_visible_input(self):
        partial = executable_partial()
        with tempfile.TemporaryDirectory() as directory:
            bundle_audit = GATE.audit_worker_visible_bundle(Path(directory), [])
            with self.assertRaisesRegex(GATE.GateValidationError, "requires non-visible evidence"):
                GATE.execute_worker_visible_checks(
                    Path(directory),
                    partial["required_disconfirmation_checks"],
                    [],
                    {
                        **bundle_audit,
                        "bundle_audit_passed": True,
                        "protected_sources_unreachable": True,
                        "credentials_unavailable": True,
                    },
                )

    def test_protected_controller_artifact_bytes_are_rejected_from_worker_bundle(self):
        protected_bytes = b"synthetic protected controller fixture"
        protected_hash = GATE.sha256_bytes(protected_bytes)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "visible.py").write_text("print('visible')\n", encoding="utf-8")
            audit = GATE.audit_worker_visible_bundle(root, ["visible.py"], {protected_hash})
            self.assertEqual(audit["protected_artifact_matches"], 0)
            (root / "protected.bin").write_bytes(protected_bytes)
            with self.assertRaisesRegex(GATE.GateValidationError, "protected controller artifact"):
                GATE.audit_worker_visible_bundle(root, ["visible.py", "protected.bin"], {protected_hash})

    def test_disconfirmation_execution_requires_isolation_and_credential_attestation(self):
        partial = executable_partial()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "check.py").write_text("print('visible')\n", encoding="utf-8")
            with self.assertRaisesRegex(GATE.GateValidationError, "credential isolation"):
                GATE.execute_worker_visible_checks(
                    root,
                    partial["required_disconfirmation_checks"],
                    ["check.py"],
                    {
                        "bundle_audit_passed": True,
                        "protected_sources_unreachable": True,
                        "credentials_unavailable": False,
                    },
                )

    def test_disconfirmation_fails_if_bundle_changes_after_attestation(self):
        partial = executable_partial()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "check.py"
            script.write_text("print('first')\n", encoding="utf-8")
            bundle_audit = GATE.audit_worker_visible_bundle(root, ["check.py"])
            script.write_text("print('changed')\n", encoding="utf-8")
            with self.assertRaisesRegex(GATE.GateValidationError, "changed after isolation attestation"):
                GATE.execute_worker_visible_checks(
                    root,
                    partial["required_disconfirmation_checks"],
                    ["check.py"],
                    {
                        **bundle_audit,
                        "protected_sources_unreachable": True,
                        "credentials_unavailable": True,
                    },
                )

    def test_missing_profile_fails_closed(self):
        decision = GATE.evaluate_recommendation(
            relevant=True,
            experience_id="trace-unregistered",
            profile=None,
            task_context=passing_context(),
            known_partials=[],
        )
        self.assertEqual(decision["state"], "retrieved_but_recommendation_withheld")
        self.assertIn("administratively_ineligible", decision["private_evidence"]["reasons"])

    def test_safety_artifacts_contain_no_private_paths_or_process_material(self):
        artifacts = [
            GATE.PROFILE_REGISTRY,
            GATE.KNOWN_PARTIAL_REGISTRY,
            GATE.POLICY_PATH,
            GATE.SANITIZATION_PROVENANCE,
            *(GATE.ROOT / path for path in GATE.EXPECTED_DERIVATIVES),
        ]
        for artifact in artifacts:
            raw = artifact.read_text(encoding="utf-8")
            self.assertIsNone(GATE.PRIVATE_PATH_RE.search(raw), artifact)
            self.assertIsNone(GATE.TOKEN_RE.search(raw), artifact)
        GATE.validate_publication_sanitization()

    def test_historical_source_bindings_and_derived_hashes_are_unchanged(self):
        base = GATE.ROOT / "experiments" / "situated-experience-benchmark-v1" / "efficiency-transfer"
        self.assertEqual(
            GATE.sha256_file(base / "requests-tls-efficiency-experience-v1.json"),
            "9b8a917d433c3876b00bb9701e64308c89a242348735b853a3a7415fdd70377b",
        )
        v2 = base / "seb-requests-tls-efficiency-transfer-smoke-v2"
        self.assertEqual(GATE.sha256_file(v2 / "freeze.json"), "848e4d71812a818acf5bd3f5609e2a8f3104729777d3925b8ec50dd7a7eb892d")
        self.assertEqual(GATE.sha256_file(v2 / "manifest.json"), "db9a9378d95300fc26ce891c015200ef6f9fe0f92d456c542f13abebc224506b")
        audit_path = v2 / "results" / "top-level-run-01" / "audit.json"
        self.assertEqual(GATE.sha256_file(audit_path), "228909c4d931d7ccae25b9d8c3d4813e7354d245d8495568970118ac250a1321")
        audit = json.loads(audit_path.read_text())
        self.assertEqual(audit["source_binding"]["original_sha256"], "bd11eb884470f73ff9aec44007786cde7ef5859ccf3691b8e74bc1dc97765c7e")
        self.assertEqual(audit["source_hashes"]["original_audit_payload_sha256"], "4da25db054333414a2040e28fa82c3f2275cd84de96b737906f87a26bc443ac4")
        self.assertEqual(audit["source_hashes"]["source_result_tree_sha256"], "a9fbd705d8c58ac911f3b67be6d1179bcb1a3fa78f968436d57263a67e4af1d4")


if __name__ == "__main__":
    unittest.main()
