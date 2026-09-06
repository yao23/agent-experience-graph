#!/usr/bin/env python3
"""Focused synthetic regression tests for runtime-canary probe semantics."""

from __future__ import annotations

import errno
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_canary as canary


def raises(error: OSError):
    def operation(_path: Path):
        raise error

    return operation


class PathObservationTests(unittest.TestCase):
    def test_absent_fixture_is_distinct(self) -> None:
        observation = canary.observe_path(
            Path("/synthetic/absent"),
            raises(FileNotFoundError(errno.ENOENT, "synthetic absent")),
        )
        self.assertEqual(observation["state"], canary.PATH_ABSENT)

    def test_present_fixture_is_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "present"
            fixture.write_text("synthetic\n", encoding="utf-8")
            observation = canary.observe_path(fixture)
        self.assertEqual(observation["state"], canary.PATH_PRESENT)

    def test_access_denied_fixture_is_unknown_presence(self) -> None:
        observation = canary.observe_path(
            Path("/synthetic/denied"),
            raises(PermissionError(errno.EACCES, "synthetic denied")),
        )
        self.assertEqual(observation["state"], canary.PATH_ACCESS_DENIED)
        self.assertFalse(observation["presence_known"])
        self.assertFalse(canary.requirement_absent([observation]))

    def test_unexpected_io_fixture_is_probe_error(self) -> None:
        observation = canary.observe_path(
            Path("/synthetic/io-error"),
            raises(OSError(errno.EIO, "synthetic io failure")),
        )
        self.assertEqual(observation["state"], canary.PATH_PROBE_ERROR)
        self.assertFalse(canary.requirement_inaccessible([observation], True))

    def test_access_denied_supports_only_attested_inaccessibility(self) -> None:
        observation = {
            "path": "/synthetic/denied",
            "state": canary.PATH_ACCESS_DENIED,
            "presence_known": False,
        }
        self.assertFalse(canary.requirement_inaccessible([observation], False))
        self.assertTrue(canary.requirement_inaccessible([observation], True))
        self.assertFalse(canary.requirement_absent([observation]))


class OperationSemanticsTests(unittest.TestCase):
    def test_expected_and_unexpected_write_errors_are_distinct(self) -> None:
        self.assertEqual(
            canary.classify_write_error(OSError(errno.EROFS, "synthetic read only")),
            "READ_ONLY",
        )
        self.assertEqual(
            canary.classify_write_error(PermissionError(errno.EPERM, "synthetic denied")),
            canary.PATH_ACCESS_DENIED,
        )
        self.assertEqual(
            canary.classify_write_error(OSError(errno.ENOENT, "synthetic wrong path")),
            canary.PATH_PROBE_ERROR,
        )
        self.assertEqual(
            canary.classify_write_error(OSError(errno.EIO, "synthetic io failure")),
            canary.PATH_PROBE_ERROR,
        )

    def test_work_directory_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            observation = canary.work_round_trip(Path(directory))
        self.assertEqual(observation["state"], "READ_WRITE_SUCCEEDED")
        self.assertTrue(observation["round_trip"])

    def test_completed_probe_is_retained_when_later_work_does_not_run(self) -> None:
        probes = canary.initial_probes()
        canary.record_probe(probes, canary.PROBE_NAMES[0], canary.PROBE_PASS, {"fixture": True})
        self.assertEqual(probes[0]["status"], canary.PROBE_PASS)
        self.assertEqual(probes[1]["status"], canary.PROBE_NOT_RUN)
        self.assertFalse(canary.all_required_probes_passed(probes))

    def test_short_timeout_terminates_and_reaps_process(self) -> None:
        observation = canary.timeout_termination_observation(timeout_seconds=0.02)
        self.assertEqual(observation["state"], "TIMED_OUT_AND_REAPED")
        self.assertTrue(observation["timed_out"])
        self.assertTrue(observation["reaped"])

    def test_replay_contract_rejects_missing_cases(self) -> None:
        report = {
            "status": "PASS",
            "summary": {
                "essential_case_count": 13,
                "executed_case_count": 12,
                "matching_case_count": 12,
                "all_essential_checks_executed": False,
                "baseline_escape_defect_observed": True,
                "fixed_escape_rejection_observed": True,
                "legitimate_cases_preserved": True,
            },
            "observed_replay": {"cases": [{"id": f"case-{index}"} for index in range(12)]},
            "source_identity": {"runtime_observed": ["baseline", "fixed"]},
        }
        passed, observation = canary.assess_replay(report, 0)
        self.assertFalse(passed)
        self.assertIn("CASE_COUNT_NOT_13", observation["contract_errors"])


if __name__ == "__main__":
    unittest.main()
