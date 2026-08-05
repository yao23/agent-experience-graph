#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


RUNNER_PATH = Path(__file__).with_name("run_experiment.py")
SPEC = importlib.util.spec_from_file_location("aeg_repair_lab_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class EventSummaryTest(unittest.TestCase):
    def test_counts_completed_commands_once_and_only_real_test_invocations(self):
        inspect = "/bin/zsh -lc \"sed -n '1,200p' test_bug.py\""
        test = "/bin/zsh -lc 'python3 test_bug.py'"
        combined = "/bin/zsh -lc 'python3 test_bug.py && git diff --check'"
        events = [
            {"type": "item.started", "item": {"type": "command_execution", "command": inspect}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": inspect}},
            {"type": "item.started", "item": {"type": "command_execution", "command": test}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": test}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": combined}},
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 50},
            },
        ]

        summary = RUNNER.summarize_events(events, "python3 test_bug.py")

        self.assertEqual(summary["commandCount"], 3)
        self.assertEqual(summary["testCommandCount"], 2)
        self.assertEqual(summary["nonCachedInputTokens"], 200)
        self.assertEqual(summary["totalNonCachedTokens"], 250)

    def test_does_not_count_search_or_file_inspection_as_a_test(self):
        commands = [
            "/bin/zsh -lc \"rg -n 'python3 test_bug.py' ISSUE.md\"",
            "/bin/zsh -lc \"sed -n '1,200p' test_bug.py\"",
            "/bin/zsh -lc \"python3 -m py_compile test_bug.py\"",
        ]
        self.assertEqual(
            RUNNER.count_command_invocations(commands, "python3 test_bug.py"),
            0,
        )

    def test_records_pre_edit_message_first_repair_path_and_inspected_files(self):
        events = [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "first approach"}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "sed -n '1,200p' rpc.py"}},
            {"type": "item.completed", "item": {"type": "file_change", "changes": [{"path": "/tmp/arm/rpc.py", "kind": "update"}]}},
        ]
        summary = RUNNER.summarize_events(events, "python3 test_bug.py", ["ISSUE.md", "rpc.py", "test_bug.py"])
        self.assertEqual(summary["preEditAgentMessages"], ["first approach"])
        self.assertEqual(summary["firstRepairPaths"], ["rpc.py"])
        self.assertEqual(summary["filesInspected"], ["rpc.py"])


class AggregateTest(unittest.TestCase):
    def make_trial(self, baseline, assisted):
        def arm(duration, commands, tokens):
            return {
                "durationMs": duration,
                "verification": {"passed": True},
                "events": {
                    "commandCount": commands,
                    "testCommandCount": 2,
                    "totalNonCachedTokens": tokens,
                },
            }

        return {"arms": {"baseline": arm(*baseline), "assisted": arm(*assisted)}}

    def test_requires_three_trials_before_claiming_improvement(self):
        aggregate = RUNNER.aggregate_trials([
            self.make_trial((100, 5, 500), (80, 4, 450)),
        ])
        self.assertEqual(aggregate["verdict"], "insufficient-trials")

    def test_uses_paired_medians_for_efficiency_verdict(self):
        trials = [
            self.make_trial((100, 5, 500), (80, 4, 450)),
            self.make_trial((120, 6, 520), (90, 5, 480)),
            self.make_trial((110, 5, 510), (95, 5, 470)),
        ]
        aggregate = RUNNER.aggregate_trials(trials)
        self.assertEqual(aggregate["verdict"], "assisted-improved-efficiency")
        self.assertEqual(aggregate["pairedMedianDelta"]["durationMs"], -20)
        self.assertEqual(aggregate["pairedMedianDelta"]["totalNonCachedTokens"], -40)

    def test_reports_mixed_signal_when_token_regression_is_material(self):
        trials = [
            self.make_trial((100, 5, 500), (80, 4, 700)),
            self.make_trial((120, 6, 520), (90, 5, 720)),
            self.make_trial((110, 5, 510), (95, 4, 710)),
        ]
        aggregate = RUNNER.aggregate_trials(trials)
        self.assertEqual(aggregate["verdict"], "mixed-efficiency-signal")


class PromptTest(unittest.TestCase):
    def test_assisted_prompt_injects_retrieved_experience_without_workspace_file(self):
        task = RUNNER.TASKS["fastapi-nested-response"]
        prompt = RUNNER.prompt_for("assisted", task)
        self.assertIn("AEG retrieved a compact, verified recovery capsule", prompt)
        self.assertIn("Recursively apply the existing field-cloning operation", prompt)
        self.assertNotIn("AEG_EXPERIENCE.json", prompt)

    def test_capsule_stays_small(self):
        task = RUNNER.TASKS["fastapi-nested-response"]
        capsule = RUNNER.experience_prompt(task["experience"])
        self.assertLess(len(capsule), 1400)

    def test_verified_capsule_comes_from_promoted_library(self):
        task = RUNNER.TASKS["protocol-resource-delegation"]
        capsule = RUNNER.experience_prompt(task["experience"], task["experienceId"])
        self.assertIn("trace-2026-08-03-tr-04-tornado-nodelay", capsule)
        self.assertIn("ownership boundary", capsule)
        self.assertLess(len(capsule), 1800)

    def test_failure_aware_capsule_is_concise_and_structured(self):
        task = RUNNER.TASKS["rpc-upgrade-interactive-mode"]
        capsule = RUNNER.experience_prompt(task["experience"], task["experienceId"])
        self.assertIn("Known failed approach:", capsule)
        self.assertIn("Recovery:", capsule)
        self.assertIn("Validated outcome:", capsule)
        self.assertLess(len(capsule), 1400)


if __name__ == "__main__":
    unittest.main()
