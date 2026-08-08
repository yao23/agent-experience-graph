#!/usr/bin/env python3

import copy
import json
from pathlib import Path
import unittest

from selection_gate import REQUIRED_SEARCH_KINDS
from selection_gate import evaluate_discovery


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "fork-only-linked-repair.json"


class SelectionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fork_only_repair_rejects_without_active_upstream_pr(self) -> None:
        self.assertEqual(self.record["upstreamActivePullRequests"], [])
        decision = evaluate_discovery(self.record)
        self.assertFalse(decision["eligible"])
        self.assertIn("public_prior_repair", decision["reasons"])
        self.assertEqual(
            decision["priorRepairs"][0]["url"],
            self.record["expected"]["repairUrl"],
        )

    def test_missing_discovery_surface_fails_closed(self) -> None:
        record = copy.deepcopy(self.record)
        record["searches"] = [
            search
            for search in record["searches"]
            if search["kind"] != REQUIRED_SEARCH_KINDS[0]
        ]
        decision = evaluate_discovery(record)
        self.assertFalse(decision["eligible"])
        self.assertIn("selection_evidence_incomplete", decision["reasons"])


if __name__ == "__main__":
    unittest.main()
