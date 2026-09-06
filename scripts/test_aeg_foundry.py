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
                "schema_version": 1,
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

    def add_valid_positive_transfer(self) -> dict:
        backlog = self.load("backlog")
        target_id = "AEG-C-011"
        target = next(
            item for item in backlog["candidates"] if item["candidate_id"] == target_id
        )
        target["category"] = "HELD_OUT_TRANSFER"
        target["qualification"] = "QUALIFIED"
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
        builder_task = next(
            item for item in backlog["work_items"] if item["task_id"] == "AEG-W-001"
        )
        builder_task["attempts"] = 1
        builder_task["status"] = "COMPLETED"
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

    def test_duplicate_start_is_rejected(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        with self.assertRaises(foundry.LeaseError) as raised:
            foundry.begin_round(self.root, now=self.start + timedelta(minutes=1), check_git=False)
        self.assertIn(first["round_id"], str(raised.exception))

    def test_expired_claim_is_recovered_then_reclaimed(self) -> None:
        first = foundry.begin_round(self.root, now=self.start, check_git=False)
        second = foundry.begin_round(
            self.root,
            now=self.start + timedelta(minutes=46),
            check_git=False,
        )
        self.assertNotEqual(first["round_id"], second["round_id"])
        self.assertEqual(second["recovery"]["resulting_task_status"], "READY")
        self.assertEqual(second["task_id"], "AEG-W-001")

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
        self.assertIn("- Human decision queue: `NONE`", content)
        self.assertIn("not a held-out positive transfer", content)

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
        self.write("state", state)
        with self.assertRaises(foundry.BudgetError):
            foundry.begin_round(self.root, now=self.start, check_git=False)

    def test_budget_block_leaves_committed_push_intent_for_a_later_eligible_run(self) -> None:
        state = self.load("state")
        state["counters_by_utc_day"] = {
            "2026-09-06": {"round_starts": 2, "worker_starts": 3}
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
        state = self.load("state")
        state["rounds_started"] = 0
        state["counters_by_utc_day"] = {
            "2026-09-06": {"round_starts": 2, "worker_starts": 2}
        }
        self.write("state", state)
        with self.assertRaises(foundry.BudgetError):
            foundry.begin_round(self.root, now=self.start, check_git=False)

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
        self.assertEqual(counts["release_review_experiences"], 1)
        self.assertEqual(counts["held_out_positive_transfers"], 1)

    def test_candidate_fields_cannot_spoof_experience_or_transfer_counts(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"][0]["release_review_status"] = "READY"
        backlog["candidates"][0]["transfer_outcome"] = "POSITIVE"
        self.write("backlog", backlog)
        foundry.validate(self.root, check_git=False)
        counts = foundry._counts(backlog)
        self.assertEqual(counts["release_review_experiences"], 0)
        self.assertEqual(counts["held_out_positive_transfers"], 0)

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

    def test_duplicate_candidate_is_invalid(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"].append(dict(backlog["candidates"][0], candidate_id="AEG-C-999"))
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("duplicate candidate source", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
