#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "isolation_controller.py"


class IsolationControllerTests(unittest.TestCase):
    def test_all_frozen_arm_envelopes_exclude_evaluator_data(self):
        manifest = json.loads((HERE / "manifest.json").read_text())
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for task in manifest["tasks"]:
                for replicate in (1, 2, 3):
                    for arm in ("control", "treatment"):
                        output = root / f"{task['id']}-{replicate}-{arm}"
                        result = subprocess.run(
                            ["python3", str(SCRIPT), "package", "--task-id", task["id"], "--replicate", str(replicate), "--arm", arm, "--output", str(output)],
                            text=True, capture_output=True,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        envelope = json.loads((output / "arm.json").read_text())
                        serialized = json.dumps(envelope)
                        self.assertNotIn(task["transfer"]["fixedCommit"], serialized)
                        self.assertNotIn(task["transfer"]["humanPatchSha256"], serialized)
                        for other in manifest["tasks"]:
                            if other["id"] != task["id"]:
                                self.assertNotIn(other["id"], serialized)

    def test_probe_rejects_actions_credentials(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw) / "bundle"
            subprocess.run(["python3", str(SCRIPT), "package", "--task-id", "nt-01-scrapy-cookiejar-adapter", "--replicate", "1", "--arm", "control", "--output", str(bundle)], check=True, capture_output=True)
            result = subprocess.run(
                ["python3", str(bundle / "isolation_controller.py"), "probe", "--bundle", str(bundle), "--attestation", str(Path(raw) / "attestation.json")],
                env={"PATH": "/usr/bin:/bin", "HOME": str(Path(raw) / "home"), "TMPDIR": str(Path(raw) / "tmp"), "AEG_RUNNER_TEMP_ROOT": raw, "AEG_WRITABLE_CACHE": str(Path(raw) / "cache"), "GITHUB_TOKEN": "sentinel"},
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("credential", result.stderr)


if __name__ == "__main__":
    unittest.main()
