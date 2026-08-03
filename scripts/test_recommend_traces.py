#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("recommend_traces.py")
SPEC = importlib.util.spec_from_file_location("aeg_recommender", SCRIPT_PATH)
RECOMMENDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOMMENDER)
VERIFIED = SCRIPT_PATH.parents[1] / "experiences" / "verified.json"


class VerifiedExperienceRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = RECOMMENDER.load_traces(VERIFIED)

    def assert_retrieved(self, task):
        result = RECOMMENDER.recommend({"task": task}, self.traces, limit=5, min_score=0.05)
        self.assertTrue(result["matches"], task)
        match = result["matches"][0]
        self.assertEqual(match["id"], "trace-2026-08-03-repair-lab-ci-v0.1.3")
        self.assertGreaterEqual(match["score"], 0.05)
        self.assertTrue(
            any(item["field"] == "reuse.recommendedFor" for item in match["evidence"]),
            match["evidence"],
        )

    def test_repairs_duplicated_jsonl_metrics(self):
        self.assert_retrieved("repair duplicated JSONL event metrics")

    def test_adds_ci_for_agent_experiment_fixtures(self):
        self.assert_retrieved("add CI for agent experiment fixtures")

    def test_publishes_verified_reusable_experience(self):
        self.assert_retrieved("publish a verified reusable experience")

    def test_unrelated_query_is_rejected(self):
        result = RECOMMENDER.recommend(
            {"task": "optimize watercolor pigment drying schedule"},
            self.traces,
            limit=5,
            min_score=0.05,
        )
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["recommended_skills"], [])
        self.assertEqual(result["recommended_tools"], [])
        self.assertEqual(result["lessons"], [])

    def test_constraints_only_score_when_the_query_supplies_constraints(self):
        trace = {
            "id": "constraints-only",
            "task": "unrelated",
            "outcome": "success",
            "constraints": ["must run without network access"],
        }
        score_without, _, evidence_without = RECOMMENDER.trace_score(
            {"task": "network access"}, trace
        )
        score_with, _, evidence_with = RECOMMENDER.trace_score(
            {"task": "unrelated", "constraints": ["without network access"]}, trace
        )
        self.assertEqual(score_without, 0)
        self.assertFalse(any(item["field"] == "constraints" for item in evidence_without))
        self.assertGreater(score_with, score_without)
        self.assertTrue(any(item["field"] == "constraints" for item in evidence_with))


if __name__ == "__main__":
    unittest.main()
