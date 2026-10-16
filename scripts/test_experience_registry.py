import importlib.util
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_registry.py"
SPEC = importlib.util.spec_from_file_location("aeg_registry_builder", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ExperienceRegistryTest(unittest.TestCase):
    def setUp(self):
        self.records = json.loads(
            (ROOT / "experiences" / "registry.json").read_text(encoding="utf-8")
        )

    def test_generated_outputs_match_canonical_records(self):
        outputs = BUILDER.expected_outputs(self.records)
        self.assertEqual(len(outputs), 2 + 2 * len(self.records))
        for path, expected in outputs.items():
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(path.is_file())
                self.assertEqual(path.read_text(encoding="utf-8"), expected)

    def test_machine_index_has_stable_consistent_routes(self):
        index = json.loads(
            (ROOT / "experiences" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(index["experience_count"], len(self.records))
        self.assertEqual(
            [entry["id"] for entry in index["experiences"]],
            [record["id"] for record in self.records],
        )
        for record, entry in zip(self.records, index["experiences"]):
            self.assertEqual(entry["slug"], record["slug"])
            self.assertEqual(entry["summary"], record["summary"])
            self.assertEqual(entry["verification_status"], record["verification_status"])
            self.assertEqual(entry["detail_url"], f"/experiences/{record['slug']}/")
            self.assertEqual(entry["json_url"], f"/experiences/data/{record['slug']}.json")
            self.assertTrue((ROOT / entry["detail_url"].lstrip("/") / "index.html").is_file())
            self.assertTrue((ROOT / entry["json_url"].lstrip("/")).is_file())

    def test_human_details_include_every_required_surface(self):
        required_copy = (
            "Symptoms and error signature",
            "Check the boundary before reuse",
            "Known limitations",
            "Dependencies",
            "What did not work—and why",
            "Recovery steps",
            "Method and objective evidence",
            "Measured values and explicit unknowns",
            "Agent-ready instructions",
            "Copy Markdown",
            "Copy JSON",
            "Download JSON",
        )
        for record in self.records:
            page = ROOT / "experiences" / record["slug"] / "index.html"
            text = page.read_text(encoding="utf-8")
            with self.subTest(record=record["id"]):
                self.assertIn(record["title"], text)
                self.assertIn(record["verification_status"].replace("_", " "), text)
                for copy in required_copy:
                    self.assertIn(copy, text)

    def test_registry_does_not_promote_partial_candidates(self):
        published = {record["id"] for record in self.records}
        candidate_ids = set()
        for path in (ROOT / "experiences" / "candidates").glob("*.json"):
            candidate_ids.update(record["id"] for record in json.loads(path.read_text()))
        self.assertTrue(candidate_ids - published)
        self.assertTrue(all(record["verification"]["status"] == "passed" for record in self.records))

    def test_measurement_hooks_are_documented_and_exposed(self):
        script = (ROOT / "site.js").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "experience-registry.md").read_text(encoding="utf-8")
        for event in (
            "experience_search",
            "experience_view",
            "use_with_agent_copy",
            "json_download",
            "replay_feedback_open",
            "experience_submission_open",
        ):
            self.assertIn(event, script)
            self.assertIn(event, docs)
        self.assertIn("track: () => {}", script)
        self.assertIn("Search text is never included", docs)

    def test_issue_forms_preserve_privacy_and_no_execution_boundary(self):
        form_dir = ROOT / ".github" / "ISSUE_TEMPLATE"
        registry_forms = {
            "candidate-experience.yml",
            "experience-replay-failure.yml",
            "experience-replay-success.yml",
        }
        self.assertEqual(
            {form.name for form in form_dir.glob("*.yml")},
            registry_forms | {"learning-pack-feedback.yml"},
        )
        for name in sorted(registry_forms):
            form = form_dir / name
            text = form.read_text(encoding="utf-8")
            with self.subTest(form=form.name):
                self.assertTrue(text.startswith("name: "))
                self.assertIn("\nbody:\n", text)
                self.assertIn("experience_id", text)
                self.assertIn("Environment and version context", text)
                self.assertIn("Agent, model, harness, and reasoning context", text)
                self.assertIn("Objective verification evidence", text)
                self.assertIn("Permission to retain and publish sanitized information", text)
                self.assertIn("credentials", text)
                self.assertIn("executed automatically", text)

    def test_learning_pack_feedback_preserves_lightweight_and_privacy_contract(self):
        text = (ROOT / ".github" / "ISSUE_TEMPLATE" / "learning-pack-feedback.yml").read_text(
            encoding="utf-8"
        )
        self.assertTrue(text.startswith("name: "))
        self.assertIn("\nbody:\n", text)
        for notice in (
            "Which check did you use, what happened, and what did not apply?",
            "GitHub submission requires an account",
            "Your feedback will be public",
            "private code",
            "personal information",
            "credentials",
            "raw agent transcripts",
            "NOT_APPLICABLE",
            "NOT_CHECKED",
            "Read only / no check used",
            "No complete verification evidence or Registry submission is required",
        ):
            self.assertIn(notice, text)
        for number in range(1, 7):
            self.assertIn(f"- R19-{number:02d}\n", text)

        # Inspect this form's existing block structure without adding a YAML dependency.
        fields = {}
        for block in re.split(r"(?m)^  - type: ", text)[1:]:
            match = re.search(r"(?m)^    id: (\w+)$", block)
            if match:
                self.assertNotIn(match[1], fields)
                fields[match[1]] = block
        self.assertEqual(
            set(fields),
            {"check_id", "action_result", "public_information", "project", "environment", "agent_model", "logs"},
        )
        self.assertEqual(
            {name for name, block in fields.items() if re.search(r"(?m)^\s+required: true$", block)},
            {"check_id", "action_result", "public_information"},
        )
        self.assertIn("multiple: true", fields["check_id"])
        self.assertIn("checkboxes\n", fields["public_information"])
        for notice in ("submission is public", "private code", "personal information", "credentials", "raw agent transcripts"):
            self.assertIn(notice, fields["public_information"])
        self.assertNotIn("experience_id", fields)
        self.assertNotIn("Objective verification evidence", text)


if __name__ == "__main__":
    unittest.main()
