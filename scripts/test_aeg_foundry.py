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

    def test_daily_and_total_budgets_fail_closed(self) -> None:
        state = self.load("state")
        state["rounds_started"] = 84
        self.write("state", state)
        with self.assertRaises(foundry.BudgetError):
            foundry.begin_round(self.root, now=self.start, check_git=False)
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

    def test_duplicate_candidate_is_invalid(self) -> None:
        backlog = self.load("backlog")
        backlog["candidates"].append(dict(backlog["candidates"][0], candidate_id="AEG-C-999"))
        self.write("backlog", backlog)
        with self.assertRaises(foundry.ConfigError) as raised:
            foundry.validate(self.root, check_git=False)
        self.assertIn("duplicate candidate source", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
