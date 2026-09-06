from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("aeg_foundry.py")
SPEC = importlib.util.spec_from_file_location("aeg_foundry", MODULE_PATH)
assert SPEC and SPEC.loader
foundry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(foundry)


class FoundryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        source_root = MODULE_PATH.parents[1]
        (self.root / "foundry").mkdir()
        for name in ("CHARTER.md", "pilot.json", "backlog.json", "state.json", "rounds.jsonl"):
            shutil.copy2(source_root / "foundry" / name, self.root / "foundry" / name)
        backlog = json.loads((self.root / "foundry" / "backlog.json").read_text(encoding="utf-8"))
        first = backlog["work_items"][0]
        first.update(
            {
                "attempts": 0,
                "claim": None,
                "failure_code": None,
                "next_step_code": "FINALIZE_INITIAL_FAMILY_SELECTION",
                "status": "READY",
            }
        )
        foundry.atomic_write_json(self.root / "foundry" / "backlog.json", backlog)
        foundry.atomic_write_json(
            self.root / "foundry" / "state.json",
            {
                "active_round": None,
                "automation": {"id": None, "status": "NOT_CREATED"},
                "channels": {
                    "DISPOSABLE_RUNTIME": {
                        "consecutive_infrastructure_failures": 0,
                        "last_infrastructure_failure_code": None,
                        "status": "BLOCKED_ENVIRONMENT",
                        "status_reason_code": "BLOCKED_ENVIRONMENT_NO_DISPOSABLE_RUNTIME",
                    },
                    "MODEL_WORKER": {
                        "consecutive_infrastructure_failures": 0,
                        "last_infrastructure_failure_code": None,
                        "status": "ACTIVE",
                        "status_reason_code": None,
                    },
                    "PUBLIC_GITHUB_READ": {
                        "consecutive_infrastructure_failures": 0,
                        "last_infrastructure_failure_code": None,
                        "status": "ACTIVE",
                        "status_reason_code": None,
                    },
                },
                "counters_by_utc_day": {},
                "discovery_no_qualified_streak": 0,
                "effect_events": [],
                "external_reuse_events": [],
                "external_users": [],
                "founder_interventions": 1,
                "human_decision_queue": [],
                "integrity_incidents": [],
                "last_charter_sha256": None,
                "last_remote_ref_sha": None,
                "last_round_id": None,
                "pause": None,
                "pending_effect": None,
                "pilot_status": "ACTIVE",
                "rounds_completed": 0,
                "rounds_started": 0,
                "runtime_environment_claims": [],
                "runtime_environments": [],
                "schema_version": 4,
                "worker_events": [],
            },
        )
        foundry.atomic_write(self.root / "foundry" / "rounds.jsonl", "")
        self._git("init", "-q")
        self._git("checkout", "-q", "-b", "codex/aeg-experience-foundry-pilot-v0.1")
        self._git("config", "user.name", "Test")
        self._git("config", "user.email", "test@example.invalid")
        self._git("remote", "add", "origin", "https://github.com/yao23/agent-experience-graph.git")
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "fixture")
        self.start = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *arguments], cwd=self.root, text=True, check=True, capture_output=True)

    def load(self, name: str) -> dict:
        return json.loads((self.root / "foundry" / f"{name}.json").read_text(encoding="utf-8"))

    def write(self, name: str, value: dict) -> None:
        foundry.atomic_write_json(self.root / "foundry" / f"{name}.json", value)

    def append_candidate(
        self, backlog: dict, number: int, qualification: str = "NOT_QUALIFIED"
    ) -> None:
        backlog["candidates"].append(
            {
                "candidate_id": f"AEG-C-{number:03d}",
                "category": "PROSPECTIVE_REPAIR",
                "contamination": "LOW",
                "family": "PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT",
                "issue_number": number,
                "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                "qualification": qualification,
                "repository": f"example/project-{number}",
                "source_state": "OPEN",
                "source_url": f"https://github.com/example/project-{number}/issues/{number}",
            }
        )

    def runtime_receipt(self, environment_id: str = "AEG-E-001") -> dict:
        return {
            "company_data_mounted": False,
            "dependency_host_codes": ["PYPI_ORG"],
            "dependency_network_policy": "ALLOWLISTED",
            "disposable": True,
            "environment_id": environment_id,
            "evidence_digest_sha256": "d" * 64,
            "expires_at": "2026-09-07T08:00:00Z",
            "fresh_instance": True,
            "github_write_credentials_present": False,
            "host_home_mounted": False,
            "isolation_class": "QUALIFIED_ONE_TIME_RUNTIME",
            "model_credentials_present": False,
            "qualified_at": "2026-09-06T07:59:00Z",
            "qualification_status": "VERIFIED_DISPOSABLE_RUNTIME",
            "test_host_codes": [],
            "test_network_policy": "DENY_ALL",
            "verifier_code": "INDEPENDENT_RUNTIME_VERIFIER",
        }

    def prepare_disposable_runtime(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["channel_code"] = "DISPOSABLE_RUNTIME"
        self.write("backlog", backlog)
        state = self.load("state")
        state["channels"]["DISPOSABLE_RUNTIME"].update(
            {"status": "ACTIVE", "status_reason_code": None}
        )
        state["runtime_environments"].append(self.runtime_receipt())
        self.write("state", state)

    def add_valid_positive_transfer(self) -> dict:
        backlog = self.load("backlog")
        target_id = "AEG-C-999"
        backlog["candidates"].append(
            {
                "candidate_id": target_id,
                "category": "HELD_OUT_TRANSFER",
                "contamination": "LOW",
                "family": "PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT",
                "issue_number": 999999,
                "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                "qualification": "QUALIFIED",
                "repository": "example/held-out-project",
                "source_state": "OPEN",
                "source_url": "https://github.com/example/held-out-project/issues/999999",
            }
        )
        transfer_task = {
            "attempts": 1,
            "candidate_ids": [target_id],
            "channel_code": "DISPOSABLE_RUNTIME",
            "claim": None,
            "failure_code": None,
            "next_step_code": "REVIEW_EXPERIENCE_RELEASE",
            "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
            "priority": 70,
            "stage": "TRANSFER_EVALUATION",
            "status": "COMPLETED",
            "task_id": "AEG-W-900",
        }
        backlog["work_items"].append(transfer_task)
        verification_task = {
            "attempts": 1,
            "candidate_ids": ["AEG-C-001"],
            "channel_code": "DISPOSABLE_RUNTIME",
            "claim": None,
            "failure_code": None,
            "next_step_code": "BUILD_EXPERIENCE",
            "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
            "priority": 71,
            "stage": "VERIFICATION",
            "status": "COMPLETED",
            "task_id": "AEG-W-899",
        }
        backlog["work_items"].append(verification_task)
        builder_task = next(
            item for item in backlog["work_items"] if item["task_id"] == "AEG-W-001"
        )
        builder_task["attempts"] = 1
        builder_task["status"] = "COMPLETED"
        backlog["behavior_verifications"] = [
            {
                "baseline": {
                    "command_argv": ["python3", "frozen_oracle.py"],
                    "environment_code": "ENV_BASELINE_VERIFY_001",
                    "evidence_digest_sha256": "c" * 64,
                    "evidence_summary_codes": ["BASELINE_FAILURE_REPRODUCED"],
                    "exit_code": 1,
                    "oracle_observation": "FAILURE",
                    "workspace_code": "WS_BASELINE_VERIFY_001",
                },
                "budget": {
                    "max_retries": 0,
                    "max_seconds": 2700,
                    "max_worker_starts": 2,
                },
                "candidate_id": "AEG-C-001",
                "finished_at": "2026-09-06T08:00:00Z",
                "model_config": {"model": "TEST_MODEL", "reasoning_effort": "low"},
                "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                "oracle_version": 1,
                "outcome": "VERIFIED_REPAIR",
                "repaired": {
                    "command_argv": ["python3", "frozen_oracle.py"],
                    "environment_code": "ENV_REPAIRED_VERIFY_001",
                    "evidence_digest_sha256": "d" * 64,
                    "evidence_summary_codes": ["REPAIRED_ORACLE_PASSED"],
                    "exit_code": 0,
                    "oracle_observation": "SUCCESS",
                    "workspace_code": "WS_REPAIRED_VERIFY_001",
                },
                "result_revision": "b" * 40,
                "solver_code": "SOLVER_VERIFY_001",
                "started_at": "2026-09-06T07:58:00Z",
                "status": "COMPLETED",
                "target_revision": "a" * 40,
                "task_id": "AEG-W-899",
                "verification_id": "AEG-V-001",
                "verifier_code": "VALIDATOR_VERIFY_001",
            }
        ]
        artifact = {
            "schema_version": 1,
            "experience_id": "AEG-X-001",
            "version": 1,
            "family": "PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT",
            "problem_signature_codes": ["PLAYWRIGHT_BROWSER_REVISION_MISSING"],
            "precondition_codes": ["LOCKFILE_AND_BROWSER_CACHE_DRIFT"],
            "procedure_steps": [
                {
                    "action_code": "INSTALL_BROWSER_FOR_RESOLVED_PLAYWRIGHT_VERSION",
                    "verification_code": "RUN_FROZEN_BROWSER_LAUNCH_ORACLE",
                }
            ],
            "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
            "source_candidate_ids": ["AEG-C-001"],
            "limitation_codes": ["REQUIRES_DISPOSABLE_RUNTIME"],
        }
        artifact_path = self.root / "foundry" / "experiences" / "aeg-x-001-v1.json"
        foundry.atomic_write_json(artifact_path, artifact)
        backlog["experiences"] = [
            {
                "artifact_path": "foundry/experiences/aeg-x-001-v1.json",
                "artifact_sha256": foundry.sha256_bytes(artifact_path.read_bytes()),
                "builder_task_ids": ["AEG-W-001"],
                "experience_id": "AEG-X-001",
                "family": "PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT",
                "release_review_status": "READY",
                "source_candidate_ids": ["AEG-C-001"],
                "version": 1,
            }
        ]
        backlog["transfer_evaluations"] = [
            {
                "all_attempts_retained": True,
                "assisted": {
                    "attempts": [
                        {
                            "attempt_id": "AEG-A-ASSISTED-001",
                            "attempt_number": 1,
                            "command_argv": ["python3", "frozen_oracle.py"],
                            "evidence_digest_sha256": "b" * 64,
                            "evidence_summary_codes": ["ORACLE_EXIT_ZERO"],
                            "exit_code": 0,
                            "finished_at": "2026-09-06T08:03:00Z",
                            "oracle_executor_code": "VALIDATOR_ASSISTED_001",
                            "oracle_observation": "SUCCESS",
                            "run_status": "VALID",
                            "solver_code": "SOLVER_ASSISTED_001",
                            "started_at": "2026-09-06T08:02:00Z",
                        }
                    ],
                    "context_code": "CTX_ASSISTED_001",
                    "environment_code": "ENV_ASSISTED_001",
                    "oracle_observation": "SUCCESS",
                    "run_status": "VALID",
                    "workspace_code": "WS_ASSISTED_001",
                },
                "baseline": {
                    "attempts": [
                        {
                            "attempt_id": "AEG-A-BASELINE-001",
                            "attempt_number": 1,
                            "command_argv": ["python3", "frozen_oracle.py"],
                            "evidence_digest_sha256": "a" * 64,
                            "evidence_summary_codes": ["ORACLE_REPRODUCED_FAILURE"],
                            "exit_code": 1,
                            "finished_at": "2026-09-06T08:02:00Z",
                            "oracle_executor_code": "VALIDATOR_BASELINE_001",
                            "oracle_observation": "FAILURE",
                            "run_status": "VALID",
                            "solver_code": "SOLVER_BASELINE_001",
                            "started_at": "2026-09-06T08:01:00Z",
                        }
                    ],
                    "context_code": "CTX_BASELINE_001",
                    "environment_code": "ENV_BASELINE_001",
                    "oracle_observation": "FAILURE",
                    "run_status": "VALID",
                    "workspace_code": "WS_BASELINE_001",
                },
                "budget": {
                    "max_retries": 0,
                    "max_seconds": 2700,
                    "max_worker_starts": 2,
                },
                "decision_rule_code": foundry.TRANSFER_DECISION_RULE,
                "evaluator_feedback_visible_to_assisted": False,
                "experience_id": "AEG-X-001",
                "experience_version": 1,
                "model_config": {"model": "TEST_MODEL", "reasoning_effort": "low"},
                "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                "oracle_version": 1,
                "outcome": "POSITIVE",
                "preregistered_at": "2026-09-06T08:00:00Z",
                "retry_rule_code": "NO_RETRY",
                "run_order": "BASELINE_FIRST",
                "status": "COMPLETED",
                "target_candidate_id": target_id,
                "target_revision": "a" * 40,
                "task_id": "AEG-W-900",
                "tool_permission_profile": "DISPOSABLE_NO_SECRETS_DEP_FETCH_ONLY",
                "transfer_id": "AEG-T-001",
                "visible_material_codes": {
                    "assisted": ["TARGET_ISSUE", "ORACLE", "EXPERIENCE:AEG-X-001:V1"],
                    "baseline": ["TARGET_ISSUE", "ORACLE"],
                },
            }
        ]
        self.write("backlog", backlog)
        return backlog

    def add_valid_external_reuse(self) -> tuple[dict, dict]:
        backlog = self.add_valid_positive_transfer()
        state = self.load("state")
        state["external_users"] = [
            {
                "actor_class": "EXTERNAL",
                "evidence_digest_sha256": "e" * 64,
                "evidence_kind": "RECEIPT",
                "evidence_summary_codes": ["EXTERNAL_RECEIPT_OBSERVED"],
                "observed_at": "2026-09-06T08:04:00Z",
                "status": "VERIFIED_EXTERNAL_USER",
                "user_id": "AEG-U-001",
                "verifier_code": "INDEPENDENT_USER_VALIDATOR_001",
            }
        ]
        state["external_reuse_events"] = [
            {
                "command_argv": ["python3", "frozen_oracle.py"],
                "evidence_digest_sha256": "f" * 64,
                "evidence_summary_codes": ["EXTERNAL_ORACLE_EXIT_ZERO"],
                "exit_code": 0,
                "experience_id": "AEG-X-001",
                "experience_version": 1,
                "finished_at": "2026-09-06T08:06:00Z",
                "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                "oracle_observation": "SUCCESS",
                "oracle_version": 1,
                "outcome": "SUCCESS",
                "reuse_id": "AEG-ER-001",
                "started_at": "2026-09-06T08:05:00Z",
                "status": "VERIFIED",
                "target_revision": "c" * 40,
                "user_id": "AEG-U-001",
                "verification_environment_code": "ENV_EXTERNAL_VERIFY_001",
                "verifier_code": "INDEPENDENT_REUSE_VALIDATOR_001",
            }
        ]
        self.write("state", state)
        return backlog, state


class FoundryTests(FoundryFixture):
    def test_initial_state_validates_and_public_fields_are_deduplicated(self) -> None:
        backlog = self.load("backlog")
        result = foundry.validate(self.root, check_git=False)
        self.assertEqual(result["candidate_count"], len(backlog["candidates"]))
        self.assertEqual(
            result["qualified_candidate_count"],
            sum(
                candidate["qualification"] == "QUALIFIED"
                for candidate in backlog["candidates"]
            ),
        )
        self.assertEqual(result["public_scan"], "PASSED")

    def test_claim_finish_and_independent_resume(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertEqual(claim["task_id"], "AEG-W-001")
        record = foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "PROVISION_CLEAN_ONE_TIME_EXECUTION_ENVIRONMENT",
            model="TEST_MODEL",
            now=self.start + timedelta(minutes=2),
        )
        self.assertEqual(record["outcome"], "SUCCESS")
        self.assertEqual(foundry.validate(self.root, check_git=False)["completed_round_count"], 1)
        self.assertEqual(
            self.load("state")["counters_by_utc_day"]["2026-09-06"]["worker_starts"],
            1,
        )
        resumed = foundry.begin_round(
            self.root, now=self.start + timedelta(hours=12), check_git=False
        )
        self.assertTrue(resumed["synthesized_work_item"])
        resumed_number = int(resumed["task_id"].removeprefix("AEG-W-"))
        prior_numbers = [
            int(item["task_id"].removeprefix("AEG-W-"))
            for item in self.load("backlog")["work_items"]
            if item["task_id"] != resumed["task_id"]
        ]
        self.assertEqual(resumed_number, max(prior_numbers) + 1)
        self.assertEqual(resumed["source_ref_sha"], claim["source_ref_sha"])

    def test_source_observation_replaces_stale_tracking_sha(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        state = self.load("state")
        state["active_round"]["source_ref_sha"] = "b" * 40
        state["active_round"]["source_ref_verified_at"] = None
        self.write("state", state)
        intent = foundry.record_intent(
            self.root,
            claim["round_id"],
            "READ_PUBLIC_SOURCE",
            "CURRENT_SOURCE_REMOTE_REF",
            now=self.start + timedelta(seconds=1),
        )
        remote_sha = "a" * 40
        completed = subprocess.CompletedProcess(
            ["git", "ls-remote"],
            0,
            stdout=f"{remote_sha}\trefs/heads/main\n",
            stderr="",
        )
        with mock.patch.object(foundry, "run_git", return_value=completed):
            receipt = foundry.observe_source_ref(
                self.root,
                claim["round_id"],
                intent["effect_id"],
                now=self.start + timedelta(seconds=2),
            )
        state = self.load("state")
        self.assertEqual(receipt["source_ref_sha"], remote_sha)
        self.assertEqual(state["active_round"]["source_ref_sha"], remote_sha)
        self.assertEqual(state["last_remote_ref_sha"], remote_sha)
        self.assertIsNone(state["pending_effect"])
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )

    def test_finish_requires_current_remote_source_observation(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        state = self.load("state")
        state["active_round"]["source_ref_verified_at"] = None
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError):
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(minutes=1),
            )

    def test_synthesized_discovery_success_requires_a_candidate_gain(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        foundry.finish_round(
            self.root,
            first["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )
        second = foundry.begin_round(
            self.root, now=self.start + timedelta(hours=12), check_git=False
        )
        with self.assertRaises(foundry.ConfigError):
            foundry.finish_round(
                self.root,
                second["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(hours=12, minutes=1),
            )

    def test_synthesized_discovery_success_requires_frozen_batch_target(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        foundry.finish_round(
            self.root,
            first["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )
        second = foundry.begin_round(
            self.root, now=self.start + timedelta(hours=12), check_git=False
        )
        backlog = self.load("backlog")
        self.append_candidate(backlog, 900)
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                second["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(hours=12, minutes=1),
            )
        self.assertIn("frozen candidate-count target", str(raised.exception))

    def test_discovery_continues_past_candidate_minimum_until_qualified_minimum(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        for number in range(900, 910):
            self.append_candidate(backlog, number)
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertTrue(claim["synthesized_work_item"])
        self.assertEqual(claim["stage"], "DISCOVERY")
        task = next(
            item for item in self.load("backlog")["work_items"] if item["task_id"] == claim["task_id"]
        )
        self.assertEqual(task["target_candidate_count"], 40)

    def test_discovery_stops_only_after_candidate_and_qualified_minima(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        for number in range(900, 913):
            self.append_candidate(backlog, number, "QUALIFIED")
        self.write("backlog", backlog)
        with self.assertRaises(foundry.NoWorkError):
            foundry.begin_round(self.root, now=self.start, check_git=False)

    def test_two_no_qualified_cycles_force_one_strategy_version_change(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        self.write("backlog", backlog)
        state = self.load("state")
        state["discovery_no_qualified_streak"] = 2
        self.write("state", state)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertEqual(claim["oracle_kind"], "ONE_ACQUISITION_STRATEGY_VERSION_INCREMENT")
        backlog = self.load("backlog")
        backlog["discovery"]["acquisition_strategy_version"] += 1
        self.write("backlog", backlog)
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "DISCOVER_AND_SCREEN_NEXT_FAMILY_LOCKED_BATCH",
            now=self.start + timedelta(minutes=1),
        )
        self.assertEqual(self.load("state")["discovery_no_qualified_streak"], 0)

    def test_discovery_success_enqueues_new_qualified_candidate_reproduction(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        backlog = self.load("backlog")
        for number in range(900, 910):
            self.append_candidate(
                backlog,
                number,
                "QUALIFIED" if number == 900 else "NOT_QUALIFIED",
            )
        self.write("backlog", backlog)
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "CONTINUE_QUALIFIED_PIPELINE",
            now=self.start + timedelta(minutes=1),
        )
        reproduction = next(
            item
            for item in self.load("backlog")["work_items"]
            if item.get("stage") == "REPRODUCTION" and item.get("candidate_ids") == ["AEG-C-900"]
        )
        self.assertEqual(reproduction["status"], "BLOCKED_ENVIRONMENT")
        self.assertEqual(reproduction["failure_code"], foundry.NO_DISPOSABLE_RUNTIME_CODE)

    def test_duplicate_start_is_rejected(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.LeaseError) as raised:
            foundry.begin_round(self.root, now=self.start + timedelta(minutes=1), check_git=False)
        self.assertIn(first["round_id"], str(raised.exception))

    def test_expired_claim_is_recovered_then_reclaimed(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertEqual(
            self.load("state")["counters_by_utc_day"]["2026-09-06"]["worker_starts"],
            1,
        )
        second = foundry.begin_round(
            self.root,
            now=self.start + timedelta(minutes=46),
            check_git=False,
        )
        self.assertNotEqual(first["round_id"], second["round_id"])
        self.assertEqual(second["recovery"]["resulting_task_status"], "READY")
        self.assertEqual(second["task_id"], "AEG-W-001")
        self.assertEqual(
            self.load("state")["counters_by_utc_day"]["2026-09-06"]["worker_starts"],
            2,
        )

    def test_pause_and_expiry_block_new_work(self) -> None:
        foundry.pause(self.root, "OPERATOR_REQUEST", now=self.start)
        with self.assertRaises(foundry.PausedError):
            foundry.begin_round(self.root, now=self.start + timedelta(minutes=1), check_git=False)
        foundry.resume(self.root, now=self.start + timedelta(minutes=2))
        expiry = datetime(2026, 10, 18, 7, 22, 29, tzinfo=timezone.utc)
        with self.assertRaises(foundry.PausedError):
            foundry.begin_round(self.root, now=expiry, check_git=False)
        self.assertEqual(self.load("state")["pilot_status"], "EXPIRED")
        final = self.root / "foundry" / "reports" / "final.md"
        self.assertTrue(final.exists())
        self.assertIn("- Recommendation: `STOP`", final.read_text(encoding="utf-8"))

    def test_weekly_report_contains_required_evidence_fields(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "DISCOVER_FINAL_FAMILY_LOCKED_BATCH",
            now=self.start + timedelta(minutes=1),
        )
        pilot, backlog, state = foundry.load_all(self.root)
        created = foundry.generate_due_reports(
            self.root,
            pilot,
            backlog,
            state,
            datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc),
        )
        self.assertIn("foundry/reports/week-01.md", created)
        content = (self.root / "foundry" / "reports" / "week-01.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("- Qualification rate: `10%`", content)
        self.assertIn(
            "- Most important recorded outcome: `SUCCESS:AEG-W-001:PASSED`",
            content,
        )
        self.assertIn("- Weekly founder hours: `UNKNOWN`", content)
        self.assertIn("- Weekly compute USD: `UNKNOWN`", content)
        self.assertIn("- Release-review Experiences: `0 / 5-8`", content)
        self.assertIn("- Verified external users: `0 / 3`", content)
        self.assertIn("- Independently verified external successful reuses: `0`", content)
        self.assertIn("- Acquisition compute USD per qualified task: `UNKNOWN`", content)
        self.assertIn("- Weekly model usage events: `NONE`", content)
        self.assertIn("- Human decision queue: `NONE`", content)
        self.assertIn("not a held-out positive transfer", content)

    def test_due_weekly_report_is_synthesized_as_bounded_work(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        next_candidate_number = 900
        while len(backlog["candidates"]) < 30:
            candidate_id = f"AEG-C-{next_candidate_number:03d}"
            backlog["candidates"].append(
                {
                    "candidate_id": candidate_id,
                    "category": "RETROSPECTIVE_REPRODUCTION",
                    "contamination": "HIGH",
                    "family": "PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT",
                    "issue_number": next_candidate_number,
                    "oracle_kind": "CONTAINER_BROWSER_LAUNCH",
                    "qualification": "NOT_QUALIFIED",
                    "repository": f"example/project-{next_candidate_number}",
                    "source_state": "CLOSED",
                    "source_url": f"https://github.com/example/project-{next_candidate_number}/issues/{next_candidate_number}",
                }
            )
            next_candidate_number += 1
        self.write("backlog", backlog)
        week_one = self.start + timedelta(days=7)
        claim = foundry.begin_round(self.root, now=week_one, check_git=False)
        self.assertEqual(claim["stage"], "REPORTING")
        self.assertEqual(claim["oracle_kind"], "WEEKLY_REPORT_SCHEMA_AND_WINDOW_CHECK")
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "CONTINUE_HIGHEST_VALUE_AUTHORIZED_WORK",
            now=week_one + timedelta(minutes=1),
        )
        report = self.root / "foundry" / "reports" / "week-01.md"
        self.assertTrue(report.is_file())
        report_start = foundry.parse_time(self.load("pilot")["activation"]["starts_at"])
        self.assertEqual(foundry._weekly_report_schema_errors(report, 1, report_start), [])

    def test_incomplete_weekly_report_fails_validation(self) -> None:
        foundry.atomic_write(
            self.root / "foundry" / "reports" / "week-01.md",
            "# AEG Foundry week 1\n",
        )
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("week 1 report lacks required line", str(raised.exception))

    def test_final_report_exposes_each_unproven_continuation_gate(self) -> None:
        pilot, backlog, state = foundry.load_all(self.root)
        created = foundry.generate_due_reports(
            self.root,
            pilot,
            backlog,
            state,
            datetime(2026, 10, 18, 7, 22, 29, tzinfo=timezone.utc),
        )
        self.assertIn("foundry/reports/final.md", created)
        content = (self.root / "foundry" / "reports" / "final.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("- Recommendation: `STOP`", content)
        self.assertIn("- Gate TASK_SUPPLY_AND_ACQUISITION_COST: `FAIL`", content)
        self.assertIn("- Gate NO_UNCONTROLLED_INCIDENTS: `PASS`", content)
        self.assertIn("- Gate THREE_VERIFIED_EXTERNAL_USERS: `FAIL`", content)
        self.assertIn(
            "- Verified external reuse per founder hour: `UNDEFINED_ZERO_DENOMINATOR`",
            content,
        )

    def test_final_external_reuse_numerator_requires_verified_external_event(self) -> None:
        backlog, state = self.add_valid_external_reuse()
        pilot = self.load("pilot")
        foundry.validate(self.root, check_git=False)
        foundry.generate_due_reports(
            self.root,
            pilot,
            backlog,
            state,
            datetime(2026, 10, 18, 7, 22, 29, tzinfo=timezone.utc),
        )
        content = (self.root / "foundry" / "reports" / "final.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("- Behavior verified: `1`", content)
        self.assertIn("- Independently verified external successful reuses: `1`", content)

    def test_uncontrolled_integrity_incident_permanently_fails_continuation_gate(self) -> None:
        state = self.load("state")
        state["integrity_incidents"] = [
            {
                "affected_record_code": "PUBLIC_STATE",
                "containment_code": "NO_CONTAINMENT_AT_OBSERVATION",
                "evidence_digest_sha256": "a" * 64,
                "incident_code": "UNCONTROLLED_PUBLIC_DATA_EXPOSURE",
                "incident_id": "AEG-II-001",
                "observed_at": "2026-09-06T08:00:00Z",
                "status": "UNCONTROLLED",
            }
        ]
        self.write("state", state)
        foundry.validate(self.root, check_git=False)
        gates = foundry._continuation_gates(
            self.load("pilot"),
            foundry._counts(self.load("backlog")),
            state,
            [],
        )
        self.assertFalse(gates["NO_UNCONTROLLED_INCIDENTS"])
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record incident")
        state["integrity_incidents"][0]["status"] = "CONTROLLED"
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("committed integrity incident ledger was rewritten", str(raised.exception))

    def test_persisted_pause_blocks_before_push_reconciliation(self) -> None:
        state = self.load("state")
        state["pilot_status"] = "PAUSED"
        state["pause"] = {"reason_code": "OPERATOR_REQUEST", "recorded_at": "2026-09-06T08:00:00Z"}
        state["pending_effect"] = {
            "effect_id": "AEG-I-pause-checkpoint",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": "2026-09-06T08:00:00Z",
            "round_id": None,
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        self.write("state", state)
        with self.assertRaises(foundry.PausedError):
            foundry.begin_round(
                self.root,
                now=self.start + timedelta(minutes=1),
                reconcile_prior_push=True,
                check_git=False,
            )
        self.assertEqual(self.load("state")["pending_effect"]["effect_id"], "AEG-I-pause-checkpoint")

    def test_pause_push_reconciles_prior_push_before_persisting(self) -> None:
        state = self.load("state")
        state["pending_effect"] = {
            "effect_id": "AEG-I-before-pause",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": "2026-09-06T07:59:00Z",
            "round_id": None,
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        self.write("state", state)

        def reconcile(root: Path) -> dict:
            reconciled = self.load("state")
            reconciled["pending_effect"] = None
            self.write("state", reconciled)
            return {"outcome": "COMPLETED_VERIFIED"}

        with mock.patch.object(foundry, "reconcile_push_command", side_effect=reconcile):
            with mock.patch.object(
                foundry,
                "persist",
                return_value={"push_reported_success": True},
            ) as persistence:
                result = foundry.pause_and_persist(self.root, "OPERATOR_REQUEST")
        self.assertEqual(result["reconciliation"]["outcome"], "COMPLETED_VERIFIED")
        self.assertTrue(result["persistence"]["push_reported_success"])
        persistence.assert_called_once()
        self.assertEqual(self.load("state")["pilot_status"], "PAUSED")

    def test_pause_during_active_round_is_immediate_and_defers_push(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with mock.patch.object(foundry, "persist") as persistence:
            result = foundry.pause_and_persist(self.root, "OPERATOR_REQUEST")
        persistence.assert_not_called()
        self.assertEqual(
            result["persistence"],
            "DEFERRED_ACTIVE_ROUND_SAFE_CHECKPOINT_REQUIRED",
        )
        state = self.load("state")
        self.assertEqual(state["pilot_status"], "PAUSED")
        self.assertEqual(state["active_round"]["round_id"], claim["round_id"])
        self.assertTrue(state["active_round"]["stop_requested"])

    def test_expiry_reconciles_prior_push_before_writing_terminal_state(self) -> None:
        state = self.load("state")
        state["pending_effect"] = {
            "effect_id": "AEG-I-before-expiry",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": "2026-10-18T07:20:00Z",
            "round_id": None,
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        self.write("state", state)
        expiry = datetime(2026, 10, 18, 7, 22, 29, tzinfo=timezone.utc)
        with mock.patch.object(
            foundry,
            "_remote_contains_push_intent",
            return_value=(True, "a" * 40),
        ):
            with self.assertRaises(foundry.PausedError):
                foundry.begin_round(
                    self.root,
                    now=expiry,
                    reconcile_prior_push=True,
                    check_git=False,
                )
        state = self.load("state")
        self.assertEqual(state["pilot_status"], "EXPIRED")
        self.assertIsNone(state["pending_effect"])
        self.assertEqual(state["effect_events"][-1]["outcome"], "COMPLETED_VERIFIED")
        self.assertTrue((self.root / "foundry" / "reports" / "final.md").exists())

    def test_operator_pause_at_expiry_stays_network_quiet_but_writes_final(self) -> None:
        foundry.pause(self.root, "OPERATOR_REQUEST", now=self.start)
        state = self.load("state")
        state["pending_effect"] = {
            "effect_id": "AEG-I-paused-before-expiry",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": "2026-10-18T07:20:00Z",
            "round_id": None,
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        self.write("state", state)
        expiry = datetime(2026, 10, 18, 7, 22, 29, tzinfo=timezone.utc)
        with mock.patch.object(foundry, "_remote_contains_push_intent") as remote_check:
            with self.assertRaises(foundry.PausedError):
                foundry.begin_round(
                    self.root,
                    now=expiry,
                    reconcile_prior_push=True,
                    check_git=False,
                )
        remote_check.assert_not_called()
        state = self.load("state")
        self.assertEqual(state["pilot_status"], "EXPIRED")
        self.assertEqual(state["pending_effect"]["effect_id"], "AEG-I-paused-before-expiry")
        self.assertTrue((self.root / "foundry" / "reports" / "final.md").exists())

    def test_daily_and_total_budgets_fail_closed(self) -> None:
        state = self.load("state")
        state["rounds_started"] = 84
        state["counters_by_utc_day"] = {
            (self.start + timedelta(days=offset)).date().isoformat(): {
                "round_starts": 2,
                "worker_starts": 2,
            }
            for offset in range(42)
        }
        self.write("state", state)
        with self.assertRaises(foundry.BudgetError):
            foundry.begin_round(self.root, now=self.start, check_git=False)
        state = self.load("state")
        state["rounds_started"] = 2
        state["counters_by_utc_day"] = {
            "2026-09-06": {"round_starts": 2, "worker_starts": 2}
        }
        self.write("state", state)
        with self.assertRaises(foundry.BudgetError):
            foundry.begin_round(self.root, now=self.start, check_git=False)

    def test_budget_block_leaves_committed_push_intent_for_a_later_eligible_run(self) -> None:
        state = self.load("state")
        state["rounds_started"] = 2
        state["counters_by_utc_day"] = {
            "2026-09-06": {"round_starts": 2, "worker_starts": 2}
        }
        state["pending_effect"] = {
            "effect_id": "AEG-I-budget-safe-reconcile",
            "effect_type": "PUSH_PILOT_BRANCH",
            "recorded_at": "2026-09-06T07:59:00Z",
            "round_id": "AEG-R-PRIOR",
            "target_code": "ORIGIN_PILOT_BRANCH",
        }
        self.write("state", state)
        with mock.patch.object(foundry, "_remote_contains_push_intent") as remote_check:
            with self.assertRaises(foundry.BudgetError):
                foundry.begin_round(
                    self.root,
                    now=self.start,
                    reconcile_prior_push=True,
                    check_git=False,
                )
        remote_check.assert_not_called()
        after = self.load("state")
        self.assertEqual(
            after["pending_effect"]["effect_id"], "AEG-I-budget-safe-reconcile"
        )
        self.assertEqual(after["effect_events"], [])

    def test_failed_or_missing_oracle_cannot_be_success(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError):
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "FAILED",
                "REVIEW_FAILURE",
                now=self.start + timedelta(minutes=1),
            )
        self.assertEqual(self.load("state")["rounds_completed"], 0)

    def test_round_resource_record_distinguishes_config_observation_and_estimate(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        record = foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            model="gpt-5.6-terra",
            configured_model="gpt-5.6-terra",
            model_attestation="CLIENT_REPORTED_MODEL",
            call_method="CODEX_NATIVE_AUTOMATION",
            input_tokens="10",
            output_tokens="5",
            total_tokens="15",
            retry_count=1,
            compute_usd="0.25",
            compute_cost_basis_code="OBSERVED_ACCOUNT_CHARGE",
            market_estimate_usd="0.40",
            market_estimate_source_code="PUBLIC_PRICE_TABLE_2026_09_06",
            quota_observation_code="CLIENT_USAGE_AVAILABLE",
            now=self.start + timedelta(minutes=1),
        )
        self.assertEqual(record["record_schema_version"], 2)
        self.assertEqual(record["total_tokens"], "15")
        self.assertEqual(record["model_attestation"], "CLIENT_REPORTED_MODEL")
        self.assertEqual(record["market_estimate_usd"], "0.40")
        foundry.validate(self.root, check_git=False)

    def test_known_cost_without_basis_and_mismatched_tokens_fail_closed(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError):
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                compute_usd="0",
                now=self.start + timedelta(seconds=30),
            )
        with self.assertRaises(foundry.ConfigError):
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                input_tokens="10",
                output_tokens="5",
                total_tokens="99",
                now=self.start + timedelta(seconds=31),
            )

    def test_committed_round_ledger_is_append_only(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record round")
        rounds_path = self.root / "foundry" / "rounds.jsonl"
        record = json.loads(rounds_path.read_text(encoding="utf-8"))
        record["next_step_code"] = "REWRITTEN_HISTORY"
        foundry.atomic_write(
            rounds_path,
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        )
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("committed round ledger was rewritten", str(raised.exception))

    def test_worker_start_budget_includes_canary(self) -> None:
        events = []
        for index in range(6):
            events.append(
                foundry.register_worker(
                    self.root,
                    f"CANARY_{index}",
                    "TEST_MODEL",
                    now=self.start,
                )
            )
        self.assertEqual(len(events), 6)
        with self.assertRaises(foundry.BudgetError):
            foundry.register_worker(self.root, "CANARY_7", "TEST_MODEL", now=self.start)

    def test_worker_resource_receipt_records_call_tokens_retries_and_cost_basis(self) -> None:
        event = foundry.register_worker(
            self.root,
            "REVIEW",
            "gpt-5.6-terra",
            configured_model="gpt-5.6-terra",
            call_method="CODEX_MODEL_WORKER",
            now=self.start,
        )
        completed = foundry.finish_worker(
            self.root,
            event["event_id"],
            "PASSED",
            input_tokens="100",
            output_tokens="20",
            total_tokens="120",
            compute_usd="0.10",
            model_attestation="CLIENT_REPORTED_MODEL",
            retry_count=0,
            compute_cost_basis_code="OBSERVED_ACCOUNT_CHARGE",
            market_estimate_usd="0.15",
            market_estimate_source_code="PUBLIC_PRICE_TABLE_2026_09_06",
            now=self.start + timedelta(seconds=5),
        )
        self.assertEqual(completed["call_method"], "CODEX_MODEL_WORKER")
        self.assertEqual(completed["total_tokens"], "120")
        foundry.validate(self.root, check_git=False)

    def test_round_worker_total_is_inferred_from_linked_events_without_double_counting(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        event = foundry.register_worker(
            self.root,
            "REVIEW",
            "TEST_MODEL",
            round_id=claim["round_id"],
            now=self.start + timedelta(seconds=1),
        )
        foundry.finish_worker(
            self.root,
            event["event_id"],
            "PASSED",
            now=self.start + timedelta(seconds=2),
        )
        record = foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )
        self.assertEqual(record["worker_starts"], 2)
        state = self.load("state")
        self.assertEqual(
            state["counters_by_utc_day"]["2026-09-06"]["worker_starts"],
            2,
        )
        foundry.validate(self.root, check_git=False)

    def test_same_infrastructure_failure_twice_quarantines_only_its_channel(self) -> None:
        failure_codes = ("GITHUB_API_502", "GITHUB_API_503", "GITHUB_API_503")
        offsets = (timedelta(), timedelta(hours=12), timedelta(hours=24))
        for index, (failure_code, offset) in enumerate(zip(failure_codes, offsets)):
            if index:
                backlog = self.load("backlog")
                backlog["work_items"][0].update(
                    {"claim": None, "failure_code": None, "status": "READY"}
                )
                self.write("backlog", backlog)
            claim = foundry.begin_round(self.root, now=self.start + offset, check_git=False)
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "FAILURE",
                "FAILED",
                "RETRY_OR_QUARANTINE_PUBLIC_SOURCE_CHANNEL",
                failure_class="INFRASTRUCTURE",
                failure_code=failure_code,
                now=self.start + offset + timedelta(minutes=1),
            )
            channel = self.load("state")["channels"]["PUBLIC_GITHUB_READ"]
            expected_status = "QUARANTINED" if index == 2 else "ACTIVE"
            self.assertEqual(channel["status"], expected_status)
            self.assertEqual(
                channel["consecutive_infrastructure_failures"],
                2 if index == 2 else 1,
            )
        self.assertEqual(self.load("state")["pilot_status"], "ACTIVE")
        with self.assertRaises(foundry.NoWorkError):
            foundry.begin_round(
                self.root,
                now=self.start + timedelta(hours=36),
                check_git=False,
            )

    def test_auth_failure_pauses_only_affected_worker_channel(self) -> None:
        event = foundry.register_worker(
            self.root,
            "AUTH_CANARY",
            "TEST_MODEL",
            channel_code="MODEL_WORKER",
            now=self.start,
        )
        foundry.finish_worker(
            self.root,
            event["event_id"],
            "AUTH_FAILED",
            now=self.start + timedelta(seconds=1),
        )
        state = self.load("state")
        self.assertEqual(state["pilot_status"], "ACTIVE")
        self.assertEqual(state["channels"]["MODEL_WORKER"]["status"], "PAUSED")
        self.assertEqual(state["channels"]["PUBLIC_GITHUB_READ"]["status"], "ACTIVE")
        with self.assertRaises(foundry.PausedError):
            foundry.register_worker(
                self.root,
                "SECOND_AUTH_CANARY",
                "TEST_MODEL",
                channel_code="MODEL_WORKER",
                now=self.start + timedelta(seconds=2),
            )
        claim = foundry.begin_round(
            self.root,
            now=self.start + timedelta(minutes=1),
            check_git=False,
        )
        self.assertEqual(claim["channel_code"], "PUBLIC_GITHUB_READ")

    def test_unresolved_intent_blocks_finish_and_retry(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        intent = foundry.record_intent(
            self.root,
            claim["round_id"],
            "READ_PUBLIC_SOURCE",
            "PUBLIC_ISSUE_METADATA",
            now=self.start + timedelta(minutes=1),
        )
        with self.assertRaises(foundry.LeaseError):
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(minutes=2),
            )
        foundry.resolve_intent(
            self.root,
            intent["effect_id"],
            "COMPLETED",
            now=self.start + timedelta(minutes=3),
        )
        foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=4),
        )

    def test_maintenance_effect_keeps_sanitized_resolution_receipt(self) -> None:
        intent = foundry.record_maintenance_intent(
            self.root,
            "CREATE_OR_UPDATE_DRAFT_PR",
            "BOOTSTRAP_DRAFT_PR",
            now=self.start,
        )
        result = foundry.resolve_intent(
            self.root,
            intent["effect_id"],
            "COMPLETED",
            now=self.start + timedelta(seconds=1),
        )
        state = self.load("state")
        self.assertIsNone(state["pending_effect"])
        self.assertEqual(state["effect_events"][-1], result)

    def test_public_summary_never_reads_private_runtime_content(self) -> None:
        pilot, backlog, state = foundry.load_all(self.root)
        private = foundry.private_directory(self.root, pilot)
        secret_marker = "person@example.com /Users/private/work ghp_12345678901234567890"
        (private / "raw.log").write_text(secret_marker, encoding="utf-8")
        content = foundry.render_status(self.root, pilot, backlog, state, now=self.start)
        self.assertNotIn(secret_marker, content)
        audit = foundry.audit_public(self.root)
        self.assertTrue(audit["ok"])
        self.assertFalse(audit["scanned_private_directory"])

    def test_valid_experience_and_positive_transfer_drive_counts(self) -> None:
        backlog = self.add_valid_positive_transfer()
        foundry.validate(self.root, check_git=False)
        counts = foundry._counts(backlog)
        self.assertEqual(counts["behavior_verified"], 1)
        self.assertEqual(counts["release_review_experiences"], 1)
        self.assertEqual(counts["held_out_positive_transfers"], 1)

    def test_candidate_fields_cannot_spoof_experience_or_transfer_counts(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"][0]["release_review_status"] = "READY"
        backlog["candidates"][0]["transfer_outcome"] = "POSITIVE"
        backlog["candidates"][0]["behavior_verification"] = "PASSED"
        self.write("backlog", backlog)
        counts = foundry._counts(backlog)
        self.assertEqual(counts["release_review_experiences"], 0)
        self.assertEqual(counts["held_out_positive_transfers"], 0)
        self.assertEqual(counts["behavior_verified"], 0)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("candidate fields are not allowlisted", str(raised.exception))

    def test_committed_candidate_qualification_cannot_be_reclassified(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"][1]["qualification"] = "QUALIFIED"
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("committed candidate classification was rewritten", str(raised.exception))

    def test_behavior_verification_requires_an_independent_verifier(self) -> None:
        backlog = self.add_valid_positive_transfer()
        verification = backlog["behavior_verifications"][0]
        verification["verifier_code"] = verification["solver_code"]
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("independent verifier missing", str(raised.exception))

    def test_release_ready_experience_requires_verified_source_behavior(self) -> None:
        backlog = self.add_valid_positive_transfer()
        backlog["behavior_verifications"] = []
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("lacks independently verified sources", str(raised.exception))

    def test_verified_external_reuse_is_separate_from_behavior_verification(self) -> None:
        backlog, state = self.add_valid_external_reuse()
        foundry.validate(self.root, check_git=False)
        self.assertEqual(foundry._counts(backlog)["behavior_verified"], 1)
        self.assertEqual(foundry._verified_external_reuse_count(state), 1)
        self.assertEqual(foundry._external_user_evidence(state), (1, 1))

    def test_self_report_does_not_become_verified_user_or_reuse(self) -> None:
        state = self.load("state")
        state["external_users"] = [
            {
                "actor_class": "EXTERNAL",
                "evidence_digest_sha256": "a" * 64,
                "evidence_kind": "SELF_REPORT",
                "evidence_summary_codes": ["UNVERIFIED_SUCCESS_CLAIM"],
                "observed_at": "2026-09-06T08:04:00Z",
                "status": "SELF_REPORTED",
                "user_id": "AEG-U-001",
                "verifier_code": "UNVERIFIED",
            }
        ]
        self.write("state", state)
        foundry.validate(self.root, check_git=False)
        self.assertEqual(foundry._external_user_evidence(state), (0, 0))
        self.assertEqual(foundry._verified_external_reuse_count(state), 0)

    def test_internal_actor_cannot_be_registered_as_external_user(self) -> None:
        _, state = self.add_valid_external_reuse()
        state["external_users"][0]["actor_class"] = "FOUNDER"
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("non-external actor cannot be an external user", str(raised.exception))

    def test_terminal_external_reuse_cannot_be_rewritten(self) -> None:
        _, state = self.add_valid_external_reuse()
        foundry.validate(self.root, check_git=False)
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record external reuse")
        reuse = state["external_reuse_events"][0]
        reuse["outcome"] = "FAILURE"
        reuse["oracle_observation"] = "FAILURE"
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("terminal external_reuse_events record was rewritten", str(raised.exception))

    def test_release_ready_experience_requires_completed_independent_transfer(self) -> None:
        backlog = self.add_valid_positive_transfer()
        backlog["transfer_evaluations"] = []
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("lacks an independent completed transfer", str(raised.exception))

    def test_transfer_task_cannot_also_build_the_experience(self) -> None:
        backlog = self.add_valid_positive_transfer()
        backlog["experiences"][0]["builder_task_ids"].append("AEG-W-900")
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("transfer task used to build", str(raised.exception))

    def test_transfer_arms_require_distinct_context_workspace_and_environment(self) -> None:
        backlog = self.add_valid_positive_transfer()
        assisted = backlog["transfer_evaluations"][0]["assisted"]
        baseline = backlog["transfer_evaluations"][0]["baseline"]
        assisted["workspace_code"] = baseline["workspace_code"]
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("baseline and assisted isolation violated", str(raised.exception))

    def test_positive_transfer_requires_baseline_failure_and_assisted_success(self) -> None:
        backlog = self.add_valid_positive_transfer()
        assisted = backlog["transfer_evaluations"][0]["assisted"]
        assisted["oracle_observation"] = "FAILURE"
        assisted["attempts"][-1]["oracle_observation"] = "FAILURE"
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("POSITIVE transfer arm results disagree", str(raised.exception))

    def test_experience_artifact_rejects_unallowlisted_free_text(self) -> None:
        backlog = self.add_valid_positive_transfer()
        artifact_path = self.root / backlog["experiences"][0]["artifact_path"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["notes"] = "unstructured material must not enter a public Experience"
        foundry.atomic_write_json(artifact_path, artifact)
        backlog["experiences"][0]["artifact_sha256"] = foundry.sha256_bytes(
            artifact_path.read_bytes()
        )
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("artifact fields are not allowlisted", str(raised.exception))

    def test_experience_artifact_digest_is_immutable(self) -> None:
        backlog = self.add_valid_positive_transfer()
        backlog["experiences"][0]["artifact_sha256"] = "f" * 64
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("artifact digest mismatch", str(raised.exception))

    def test_non_string_transfer_target_fails_closed(self) -> None:
        backlog = self.add_valid_positive_transfer()
        backlog["transfer_evaluations"][0]["target_candidate_id"] = {"unexpected": "shape"}
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("qualified held-out candidate", str(raised.exception))

    def test_committed_experience_version_cannot_be_rewritten_with_a_new_digest(self) -> None:
        backlog = self.add_valid_positive_transfer()
        foundry.validate(self.root, check_git=False)
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record completed transfer")
        artifact_path = self.root / backlog["experiences"][0]["artifact_path"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["procedure_steps"][0]["action_code"] = "DIFFERENT_ACTION"
        foundry.atomic_write_json(artifact_path, artifact)
        backlog["experiences"][0]["artifact_sha256"] = foundry.sha256_bytes(
            artifact_path.read_bytes()
        )
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("committed Experience version was rewritten", str(raised.exception))

    def test_terminal_transfer_result_cannot_be_rewritten(self) -> None:
        backlog = self.add_valid_positive_transfer()
        foundry.validate(self.root, check_git=False)
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record completed transfer")
        transfer = backlog["transfer_evaluations"][0]
        transfer["outcome"] = "NEUTRAL"
        transfer["assisted"]["oracle_observation"] = "FAILURE"
        transfer["assisted"]["attempts"][-1]["oracle_observation"] = "FAILURE"
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("terminal transfer evaluation was rewritten", str(raised.exception))

    def test_preregistered_transfer_freeze_and_timestamp_fail_closed(self) -> None:
        backlog = self.add_valid_positive_transfer()
        transfer = backlog["transfer_evaluations"][0]
        transfer["status"] = "PREREGISTERED"
        transfer["outcome"] = "PENDING"
        transfer["all_attempts_retained"] = False
        backlog["experiences"][0]["release_review_status"] = "NOT_READY"
        next(item for item in backlog["work_items"] if item["task_id"] == "AEG-W-900")[
            "status"
        ] = "READY"
        for arm_name in ("baseline", "assisted"):
            transfer[arm_name]["attempts"] = []
            transfer[arm_name]["run_status"] = "PENDING"
            transfer[arm_name]["oracle_observation"] = "PENDING"
        self.write("backlog", backlog)
        foundry.validate(self.root, check_git=False)
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "preregister transfer")
        transfer["target_revision"] = "c" * 40
        transfer["preregistered_at"] = None
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("invalid preregistration time", str(raised.exception))
        self.assertIn("preregistered transfer freeze was rewritten", str(raised.exception))

    def test_blocked_or_wrong_channel_cannot_record_untrusted_execution_intent(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.record_intent(
                self.root,
                claim["round_id"],
                "CLONE_PUBLIC_REPOSITORY",
                "QUALIFIED_TARGET_CLONE",
                environment_id="AEG-E-001",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("requires a DISPOSABLE_RUNTIME round", str(raised.exception))
        self.assertIsNone(self.load("state")["pending_effect"])

    def test_verified_receipt_reactivates_runtime_channel_and_blocked_task(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        self.write("backlog", backlog)
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt())
        self.write("state", state)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertEqual(claim["task_id"], "AEG-W-002")
        self.assertEqual(claim["channel_code"], "DISPOSABLE_RUNTIME")
        self.assertIn(
            "CHANNEL_REACTIVATED_FROM_VERIFIED_RECEIPT",
            claim["runtime_availability"]["changes"],
        )
        self.assertEqual(
            self.load("state")["channels"]["DISPOSABLE_RUNTIME"]["status"],
            "ACTIVE",
        )

    def test_expired_receipt_does_not_reactivate_runtime_work(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["status"] = "COMPLETED"
        self.write("backlog", backlog)
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt())
        self.write("state", state)
        claim = foundry.begin_round(
            self.root,
            now=self.start + timedelta(days=2),
            check_git=False,
        )
        self.assertEqual(claim["channel_code"], "PUBLIC_GITHUB_READ")
        blocked = next(
            item for item in self.load("backlog")["work_items"] if item["task_id"] == "AEG-W-002"
        )
        self.assertEqual(blocked["status"], "BLOCKED_ENVIRONMENT")

    def test_untrusted_intent_requires_both_receipt_and_live_runtime_channel(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["channel_code"] = "DISPOSABLE_RUNTIME"
        self.write("backlog", backlog)
        state = self.load("state")
        state["channels"]["DISPOSABLE_RUNTIME"].update(
            {"status": "ACTIVE", "status_reason_code": None}
        )
        self.write("state", state)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        self.assertEqual(claim["channel_code"], "PUBLIC_GITHUB_READ")
        state = self.load("state")
        self.assertEqual(state["channels"]["DISPOSABLE_RUNTIME"]["status"], "BLOCKED_ENVIRONMENT")
        self.assertEqual(state["runtime_environment_claims"], [])
        state["runtime_environments"].append(self.runtime_receipt())
        state["channels"]["DISPOSABLE_RUNTIME"].update(
            {
                "status": "BLOCKED_ENVIRONMENT",
                "status_reason_code": "RUNTIME_REVOKED_BEFORE_EFFECT",
            }
        )
        active = {
            "channel_code": "DISPOSABLE_RUNTIME",
            "round_id": "AEG-R-TEST",
            "runtime_environment_ids": [],
        }
        with self.assertRaises(foundry.ConfigError) as blocked_channel:
            foundry._bind_disposable_runtime(
                state,
                active,
                "AEG-E-001",
                self.start + timedelta(seconds=2),
            )
        self.assertIn("channel is not ACTIVE", str(blocked_channel.exception))
        self.assertEqual(state["runtime_environment_claims"], [])

    def test_maintenance_cannot_record_untrusted_execution_intent(self) -> None:
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.record_maintenance_intent(
                self.root,
                "RUN_FROZEN_ORACLE",
                "OUT_OF_BAND_TARGET_TEST",
                now=self.start,
            )
        self.assertIn("active disposable-runtime round", str(raised.exception))
        self.assertIsNone(self.load("state")["pending_effect"])

    def test_verified_runtime_is_bound_once_and_reused_only_within_its_round(self) -> None:
        self.prepare_disposable_runtime()
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        clone = foundry.record_intent(
            self.root,
            first["round_id"],
            "CLONE_PUBLIC_REPOSITORY",
            "QUALIFIED_TARGET_CLONE",
            environment_id="AEG-E-001",
            now=self.start + timedelta(seconds=1),
        )
        state = self.load("state")
        self.assertEqual(clone["environment_id"], "AEG-E-001")
        self.assertEqual(state["active_round"]["runtime_environment_ids"], ["AEG-E-001"])
        self.assertEqual(len(state["runtime_environment_claims"]), 1)
        foundry.resolve_intent(
            self.root,
            clone["effect_id"],
            "COMPLETED",
            now=self.start + timedelta(seconds=2),
        )
        install = foundry.record_intent(
            self.root,
            first["round_id"],
            "INSTALL_PINNED_DEPENDENCIES",
            "PINNED_DEPENDENCY_SET",
            environment_id="AEG-E-001",
            now=self.start + timedelta(seconds=3),
        )
        self.assertEqual(len(self.load("state")["runtime_environment_claims"]), 1)
        foundry.resolve_intent(
            self.root,
            install["effect_id"],
            "COMPLETED",
            now=self.start + timedelta(seconds=4),
        )
        foundry.finish_round(
            self.root,
            first["round_id"],
            "SUCCESS",
            "PASSED",
            "NEXT",
            now=self.start + timedelta(minutes=1),
        )
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt("AEG-E-002"))
        self.write("state", state)
        backlog = self.load("backlog")
        backlog["work_items"][1].update(
            {"channel_code": "DISPOSABLE_RUNTIME", "status": "READY"}
        )
        self.write("backlog", backlog)
        second = foundry.begin_round(
            self.root,
            now=self.start + timedelta(hours=12),
            check_git=False,
        )
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.record_intent(
                self.root,
                second["round_id"],
                "CLONE_PUBLIC_REPOSITORY",
                "SECOND_QUALIFIED_TARGET_CLONE",
                environment_id="AEG-E-001",
                now=self.start + timedelta(hours=12, seconds=1),
            )
        self.assertIn("already consumed", str(raised.exception))

    def test_one_round_may_claim_multiple_distinct_disposable_runtimes(self) -> None:
        self.prepare_disposable_runtime()
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt("AEG-E-002"))
        self.write("state", state)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        for index, environment_id in enumerate(("AEG-E-001", "AEG-E-002"), 1):
            intent = foundry.record_intent(
                self.root,
                claim["round_id"],
                "CLONE_PUBLIC_REPOSITORY",
                f"ISOLATED_ARM_{index}",
                environment_id=environment_id,
                now=self.start + timedelta(seconds=index),
            )
            foundry.resolve_intent(
                self.root,
                intent["effect_id"],
                "COMPLETED",
                now=self.start + timedelta(seconds=index + 2),
            )
        state = self.load("state")
        self.assertEqual(
            state["active_round"]["runtime_environment_ids"],
            ["AEG-E-001", "AEG-E-002"],
        )
        self.assertEqual(len(state["runtime_environment_claims"]), 2)
        foundry.validate(self.root, check_git=False)

    def test_frozen_oracle_completion_requires_atomic_evidence_receipt(self) -> None:
        self.prepare_disposable_runtime()
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "REPRODUCTION"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        intent = foundry.record_intent(
            self.root,
            claim["round_id"],
            "RUN_FROZEN_ORACLE",
            "FROZEN_TARGET_ORACLE",
            environment_id="AEG-E-001",
            target_revision="a" * 40,
            now=self.start + timedelta(seconds=1),
        )
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.resolve_intent(
                self.root,
                intent["effect_id"],
                "COMPLETED",
                now=self.start + timedelta(seconds=2),
            )
        self.assertIn("requires command argv", str(raised.exception))
        self.assertEqual(self.load("state")["pending_effect"]["effect_id"], intent["effect_id"])
        receipt = foundry.resolve_intent(
            self.root,
            intent["effect_id"],
            "COMPLETED",
            command_argv=["python3", "frozen_oracle.py"],
            exit_code=1,
            oracle_observation="FAILURE",
            evidence_digest_sha256="e" * 64,
            evidence_summary_codes=["EXPECTED_FAILURE_REPRODUCED"],
            now=self.start + timedelta(seconds=3),
        )
        self.assertEqual(receipt["oracle_observation"], "FAILURE")
        self.assertEqual(receipt["target_revision"], "a" * 40)
        self.assertEqual(
            set(receipt),
            foundry.ORACLE_EFFECT_COMPLETED_KEYS,
        )
        foundry.validate(self.root, check_git=False)

    def test_reproduction_success_requires_failure_observation_receipt(self) -> None:
        self.prepare_disposable_runtime()
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "REPRODUCTION"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as missing:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "REPAIR_REPRODUCED_FAILURE",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("FAILURE receipt", str(missing.exception))
        for index, observation in enumerate(("SUCCESS", "FAILURE"), 1):
            intent = foundry.record_intent(
                self.root,
                claim["round_id"],
                "RUN_FROZEN_ORACLE",
                f"REPRODUCTION_ORACLE_{index}",
                environment_id="AEG-E-001",
                target_revision="a" * 40,
                now=self.start + timedelta(seconds=index + 1),
            )
            foundry.resolve_intent(
                self.root,
                intent["effect_id"],
                "COMPLETED",
                command_argv=["python3", "frozen_oracle.py"],
                exit_code=0 if observation == "SUCCESS" else 1,
                oracle_observation=observation,
                evidence_digest_sha256=("e" if observation == "SUCCESS" else "f") * 64,
                evidence_summary_codes=[f"OBSERVED_{observation}"],
                now=self.start + timedelta(seconds=index + 3),
            )
            if observation == "SUCCESS":
                with self.assertRaises(foundry.ConfigError) as wrong_observation:
                    foundry.finish_round(
                        self.root,
                        claim["round_id"],
                        "SUCCESS",
                        "PASSED",
                        "REPAIR_REPRODUCED_FAILURE",
                        now=self.start + timedelta(seconds=8),
                    )
                self.assertIn("FAILURE receipt", str(wrong_observation.exception))
        result = foundry.finish_round(
            self.root,
            claim["round_id"],
            "SUCCESS",
            "PASSED",
            "REPAIR_REPRODUCED_FAILURE",
            now=self.start + timedelta(seconds=9),
        )
        self.assertEqual(result["stage"], "REPRODUCTION")
        repair = next(
            item
            for item in self.load("backlog")["work_items"]
            if item.get("stage") == "REPAIR"
            and item.get("candidate_ids") == backlog["work_items"][0]["candidate_ids"]
        )
        self.assertEqual(repair["status"], "BLOCKED_ENVIRONMENT")
        self.assertEqual(
            self.load("state")["channels"]["DISPOSABLE_RUNTIME"]["status"],
            "BLOCKED_ENVIRONMENT",
        )

    def test_repair_success_requires_success_observation_receipt(self) -> None:
        self.prepare_disposable_runtime()
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "REPAIR"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        intent = foundry.record_intent(
            self.root,
            claim["round_id"],
            "RUN_FROZEN_ORACLE",
            "REPAIR_ORACLE",
            environment_id="AEG-E-001",
            target_revision="b" * 40,
            now=self.start + timedelta(seconds=1),
        )
        foundry.resolve_intent(
            self.root,
            intent["effect_id"],
            "COMPLETED",
            command_argv=["python3", "frozen_oracle.py"],
            exit_code=1,
            oracle_observation="FAILURE",
            evidence_digest_sha256="e" * 64,
            evidence_summary_codes=["REPAIR_DID_NOT_PASS"],
            now=self.start + timedelta(seconds=2),
        )
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "VERIFY_REPAIR",
                now=self.start + timedelta(seconds=3),
            )
        self.assertIn("SUCCESS receipt", str(raised.exception))

    def test_verification_success_requires_first_class_behavior_evidence(self) -> None:
        self.prepare_disposable_runtime()
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt("AEG-E-002"))
        self.write("state", state)
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "VERIFICATION"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("isolated behavior evidence", str(raised.exception))

    def test_transfer_success_requires_first_class_terminal_evidence(self) -> None:
        self.prepare_disposable_runtime()
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt("AEG-E-002"))
        self.write("state", state)
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "TRANSFER_EVALUATION"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("terminal transfer", str(raised.exception))

    def test_release_success_requires_experience_built_by_current_task(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "RELEASE_MATERIAL"
        self.write("backlog", backlog)
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "SUCCESS",
                "PASSED",
                "NEXT",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("Experience built by this task", str(raised.exception))

    def test_unknown_stage_is_rejected(self) -> None:
        backlog = self.load("backlog")
        backlog["work_items"][0]["stage"] = "UNCONTROLLED_STAGE"
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("invalid stage", str(raised.exception))

    def test_non_success_outcome_cannot_mark_task_completed(self) -> None:
        claim = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.finish_round(
                self.root,
                claim["round_id"],
                "FAILURE",
                "FAILED",
                "NEXT",
                task_status="COMPLETED",
                failure_class="TASK",
                now=self.start + timedelta(seconds=1),
            )
        self.assertIn("non-success outcome", str(raised.exception))

    def test_runtime_receipt_rejects_credentials_mounts_and_open_network_shape(self) -> None:
        state = self.load("state")
        receipt = self.runtime_receipt()
        receipt["model_credentials_present"] = True
        receipt["test_network_policy"] = "DENY_ALL"
        receipt["test_host_codes"] = ["PUBLIC_INTERNET"]
        state["runtime_environments"].append(receipt)
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("model_credentials_present", str(raised.exception))
        self.assertIn("invalid test network host codes", str(raised.exception))

    def test_committed_runtime_receipt_and_claim_ledgers_are_append_only(self) -> None:
        state = self.load("state")
        state["runtime_environments"].append(self.runtime_receipt())
        state["runtime_environment_claims"].append(
            {
                "claim_id": "AEG-EC-" + "A" * 32,
                "claimed_at": "2026-09-06T08:00:00Z",
                "environment_id": "AEG-E-001",
                "round_id": "AEG-R-20260906T080000Z-00000001",
            }
        )
        self.write("state", state)
        foundry.validate(self.root, check_git=False)
        self._git("add", "foundry")
        self._git("commit", "-q", "-m", "record runtime evidence")
        state["runtime_environments"][0]["evidence_digest_sha256"] = "e" * 64
        state["runtime_environment_claims"][0]["round_id"] = (
            "AEG-R-20260906T080100Z-00000002"
        )
        self.write("state", state)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("committed runtime_environments ledger was rewritten", str(raised.exception))
        self.assertIn(
            "committed runtime_environment_claims ledger was rewritten",
            str(raised.exception),
        )

    def test_duplicate_candidate_is_invalid(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"].append(dict(backlog["candidates"][0], candidate_id="AEG-C-999"))
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("duplicate candidate source", str(raised.exception))

    def test_pilot_contract_rejects_shifted_42_day_window(self) -> None:
        pilot = self.load("pilot")
        pilot["activation"] = {
            "starts_at": "2026-09-07T07:22:29Z",
            "ends_at": "2026-10-19T07:22:29Z",
        }
        self.write("pilot", pilot)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("fixed pilot control contract changed", str(raised.exception))

    def test_pilot_contract_rejects_target_downgrade(self) -> None:
        pilot = self.load("pilot")
        pilot["targets"]["qualified_tasks"] = 1
        pilot["targets"]["held_out_positive_transfers"] = 0
        self.write("pilot", pilot)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("fixed pilot control contract changed", str(raised.exception))

    def test_pilot_contract_rejects_authorization_expansion(self) -> None:
        pilot = self.load("pilot")
        pilot["authorization"]["external_communication"] = "AUTHORIZED"
        pilot["authorization"]["new_paid_cloud_usd"] = 100
        self.write("pilot", pilot)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("fixed pilot control contract changed", str(raised.exception))

    def test_mutating_entrypoint_rejects_pilot_contract_tampering_before_write(self) -> None:
        pilot = self.load("pilot")
        pilot["budgets"]["max_worker_starts_per_day"] = 999
        self.write("pilot", pilot)
        before = self.load("state")
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.register_worker(
                self.root,
                "BUDGET_BYPASS_ATTEMPT",
                "TEST_MODEL",
                now=self.start,
            )
        self.assertIn("fixed pilot control contract changed", str(raised.exception))
        self.assertEqual(self.load("state"), before)

    def test_pilot_contract_rejects_execution_model_schedule_or_extra_fields(self) -> None:
        mutations = (
            (("execution", "concurrency"), 2),
            (("model_policy", "automation_reasoning_effort"), "xhigh"),
            (("schedule", "cadence"), "PT1M"),
            (("authorization", "unreviewed_permission"), "ALLOWED"),
        )
        original = self.load("pilot")
        for path, value in mutations:
            with self.subTest(path=path):
                pilot = json.loads(json.dumps(original))
                pilot[path[0]][path[1]] = value
                self.write("pilot", pilot)
                with self.assertRaises(foundry.ConfigError) as raised:
                    foundry.validate(self.root, check_git=False)
                self.assertIn("fixed pilot control contract changed", str(raised.exception))
        self.write("pilot", original)


if __name__ == "__main__":
    unittest.main()
