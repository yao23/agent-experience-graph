import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_registry.py"
SPEC = importlib.util.spec_from_file_location("aeg_registry_builder", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ExperienceRegistryTest(unittest.TestCase):
    def setUp(self):
        self.records = json.loads(
            (ROOT / "experiences" / "verified.json").read_text(encoding="utf-8")
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
        forms = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
        self.assertEqual(len(forms), 3)
        for form in forms:
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


if __name__ == "__main__":
    unittest.main()
