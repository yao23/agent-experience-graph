import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path


HERE = Path(__file__).resolve().parent
SUBSTRATE = HERE.parent


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


controller = import_file("aeg_substrate_controller", SUBSTRATE / "controller.py")
worker = import_file("aeg_substrate_worker", SUBSTRATE / "container_worker.py")


class FakeRuntime:
    def __init__(self, arm_root):
        self.mount_roots = {"container": Path(arm_root)}
        self.calls = []

    def exec(self, container_id, arguments, input_text=None, timeout=120, check=True):
        self.calls.append((container_id, arguments, input_text, timeout, check))
        if arguments[0] == "inspect":
            return {"path": arguments[2], "content": "value\n"}
        if arguments[0] == "run":
            argv = json.loads(arguments[2])
            return {"argv": argv, "exit_code": 0, "stdout": "ok\n", "stderr": ""}
        if arguments[0] == "visible-test":
            return {"argv": ["python3", "-m", "unittest"], "exit_code": 0, "stdout": "ok\n", "stderr": ""}
        if arguments[0] == "apply-patch":
            return {"files_changed": ["module.py"]}
        if arguments[0] == "snapshot":
            return {"sha256": "a" * 64, "files": ["module.py"], "bytes": 32}
        raise AssertionError(arguments)


class SubstrateConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.policy = controller.load_json(controller.POLICY)
        self.manifest = controller.load_json(controller.MANIFEST)

    def test_frozen_configuration_and_order_validate(self):
        result = controller.validate_configuration()
        self.assertEqual(result["manifest_sha256"], "95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9")
        self.assertEqual(result["execution_plan_sha256"], "6e6a3b75102d03d804cf0b8e1f51b3b1194fe5e1c39802b9d0cc64043bb9582a")
        self.assertEqual(result["arms"], 12)

    def test_docker_arguments_are_hardened_and_secret_free(self):
        runtime = controller.DockerRuntime("test-image", self.policy)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "task").mkdir()
            (root / "arm.json").write_text("{}\n", encoding="utf-8")
            args = runtime.security_args(root, "test-container")
        joined = " ".join(args)
        self.assertIn("--network none", joined)
        self.assertNotIn("--pid", args)
        self.assertNotIn("--pid host", joined)
        self.assertIn("--read-only", args)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("--security-opt no-new-privileges:true", joined)
        self.assertIn("--pids-limit 64", joined)
        self.assertIn("--memory 536870912", joined)
        self.assertIn("--memory-swap 536870912", joined)
        self.assertIn("--cpus 1", joined)
        self.assertEqual(args.count("--mount"), 0)
        self.assertEqual(args.count("--tmpfs"), 2)
        self.assertIn("/workspace:rw,nosuid,nodev,size=33554432", joined)
        self.assertNotIn("docker.sock", joined)
        self.assertNotIn("OPENAI_API_KEY", joined)
        self.assertNotIn("GITHUB_TOKEN", joined)

    def test_host_tool_subprocess_environment_is_credential_scrubbed(self):
        with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "fake-model-secret",
            "GITHUB_TOKEN": "fake-github-secret",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "fake-actions-secret",
            "AEG_RAW_OUTPUT_CERT_PEM": "fake-public-cert",
        }):
            result = controller.run(["/usr/bin/env"])
        self.assertNotIn("fake-model-secret", result.stdout)
        self.assertNotIn("fake-github-secret", result.stdout)
        self.assertNotIn("fake-actions-secret", result.stdout)
        self.assertNotIn("fake-public-cert", result.stdout)

    def test_bridge_exposes_exactly_four_strict_tools(self):
        tools = controller.function_tools()
        self.assertEqual(
            [item["name"] for item in tools],
            ["inspect_file", "run_command", "apply_patch", "run_visible_tests"],
        )
        for item in tools:
            self.assertTrue(item["strict"])
            self.assertFalse(item["parameters"]["additionalProperties"])

    def test_budget_guard_enforces_command_token_cost_and_disk_ceilings(self):
        guard = controller.BudgetGuard(
            self.policy,
            {"wall_time_seconds": 900, "max_completed_commands": 1, "max_attempts": 3},
        )
        guard.add_command()
        with self.assertRaisesRegex(controller.ControllerError, "command"):
            guard.add_command()
        with self.assertRaisesRegex(controller.ControllerError, "workspace"):
            guard.check_workspace(self.policy["container"]["workspace_bytes"] + 1)
        token_guard = controller.BudgetGuard(
            self.policy,
            {"wall_time_seconds": 900, "max_completed_commands": 40, "max_attempts": 3},
        )
        with self.assertRaisesRegex(controller.ControllerError, "token"):
            token_guard.add_usage({"input_tokens": self.policy["safety_ceiling"]["max_total_tokens"] + 1})
        cost_guard = controller.BudgetGuard(
            self.policy,
            {"wall_time_seconds": 900, "max_completed_commands": 40, "max_attempts": 3},
        )
        with self.assertRaisesRegex(controller.ControllerError, "cost"):
            cost_guard.add_usage({"output_tokens": 2_000_000})


class ToolBridgeTests(unittest.TestCase):
    def setUp(self):
        self.raw = tempfile.TemporaryDirectory()
        self.root = Path(self.raw.name)
        controller.write_json(self.root / "arm.json", {"public_test_command": "python3 -m unittest -v test_public.py"})
        self.runtime = FakeRuntime(self.root)
        self.bridge = controller.ToolBridge(
            self.runtime,
            "container",
            controller.load_json(controller.POLICY),
            {"wall_time_seconds": 900, "max_completed_commands": 40, "max_attempts": 3},
            public_test_command="python3 -m unittest -v test_public.py",
        )

    def tearDown(self):
        self.raw.cleanup()

    def test_registered_test_via_run_command_is_measured(self):
        result = self.bridge.call("run_command", {"command": "python3 -m unittest -v test_public.py"})
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(self.bridge.guard.commands, 1)
        self.assertEqual(self.bridge.tests, [{
            "command": "python3 -m unittest -v test_public.py",
            "scope": "agent",
            "passed": True,
        }])

    def test_unknown_tool_and_arguments_are_rejected(self):
        with self.assertRaisesRegex(controller.ControllerError, "unknown"):
            self.bridge.call("shell", {"command": "id"})
        with self.assertRaisesRegex(controller.ControllerError, "invalid"):
            self.bridge.call("inspect_file", {"path": "module.py", "extra": True})

    def test_attempts_count_unique_workspace_snapshots(self):
        patch = "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-old\n+new\n"
        self.bridge.call("apply_patch", {"patch": patch})
        self.bridge.call("apply_patch", {"patch": patch})
        self.assertEqual(len(self.bridge.attempt_hashes), 1)


class WorkerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.raw = tempfile.TemporaryDirectory()
        self.root = Path(self.raw.name)
        self.task = self.root / "task"
        self.task.mkdir()
        self.arm = self.root / "arm.json"
        self.arm.write_text(json.dumps({"public_test_command": "python3 -m unittest -v test_public.py"}), encoding="utf-8")
        self.originals = worker.ROOT, worker.TASK, worker.ARM, worker.BASELINE
        worker.ROOT, worker.TASK, worker.ARM, worker.BASELINE = self.root, self.task, self.arm, self.root / "baseline"

    def tearDown(self):
        worker.ROOT, worker.TASK, worker.ARM, worker.BASELINE = self.originals
        self.raw.cleanup()

    def test_patch_applies_only_to_existing_production_file(self):
        module = self.task / "module.py"
        module.write_text("old\n", encoding="utf-8")
        patch = "diff --git a/module.py b/module.py\nindex 1111111..2222222 100644\n--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-old\n+new\n"
        self.assertEqual(worker.parse_and_apply_patch(patch, 4096), ["module.py"])
        self.assertEqual(module.read_text(encoding="utf-8"), "new\n")

    def test_patch_rejects_tests_traversal_symlink_and_duplicate_target(self):
        (self.task / "test_public.py").write_text("old\n", encoding="utf-8")
        protected = "--- a/test_public.py\n+++ b/test_public.py\n@@ -1 +1 @@\n-old\n+new\n"
        with self.assertRaisesRegex(worker.WorkerError, "protected"):
            worker.parse_and_apply_patch(protected, 4096)
        traversal = "--- a/../outside.py\n+++ b/../outside.py\n@@ -1 +1 @@\n-old\n+new\n"
        with self.assertRaisesRegex(worker.WorkerError, "outside"):
            worker.parse_and_apply_patch(traversal, 4096)
        outside = self.root / "outside.py"
        outside.write_text("old\n", encoding="utf-8")
        (self.task / "link.py").symlink_to(outside)
        symlink = "--- a/link.py\n+++ b/link.py\n@@ -1 +1 @@\n-old\n+new\n"
        with self.assertRaisesRegex(worker.WorkerError, "escapes|symlink"):
            worker.parse_and_apply_patch(symlink, 4096)
        module = self.task / "module.py"
        module.write_text("old\n", encoding="utf-8")
        duplicate = (
            "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-old\n+one\n"
            "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-old\n+two\n"
        )
        with self.assertRaisesRegex(worker.WorkerError, "only once"):
            worker.parse_and_apply_patch(duplicate, 4096)

    def test_command_allowlist_and_environment(self):
        result = worker.run_registered(["python3", "--version"], 10)
        self.assertEqual(result["exit_code"], 0)
        with self.assertRaisesRegex(worker.WorkerError, "allowlisted"):
            worker.run_registered(["sh", "-c", "env"], 10)

    def test_baseline_export_includes_only_modified_production_file(self):
        module = self.task / "module.py"
        module.write_text("old\n", encoding="utf-8")
        (self.task / "ISSUE.md").write_text("protected\n", encoding="utf-8")
        worker.create_baseline()
        module.write_text("new\n", encoding="utf-8")
        result = worker.export_workspace_patch(4096)
        self.assertEqual(result["files_changed"], ["module.py"])
        self.assertIn("--- a/module.py", result["patch"])
        self.assertNotIn("ISSUE.md", result["patch"])
        (self.task / "new.py").write_text("new\n", encoding="utf-8")
        with self.assertRaisesRegex(worker.WorkerError, "creation"):
            worker.export_workspace_patch(4096)


class ModelAndEncryptionTests(unittest.TestCase):
    def setUp(self):
        self.policy = controller.load_json(controller.POLICY)
        self.raw = tempfile.TemporaryDirectory()
        self.root = Path(self.raw.name)
        controller.write_json(self.root / "arm.json", {"public_test_command": "python3 --version"})
        self.runtime = FakeRuntime(self.root)
        self.bridge = controller.ToolBridge(
            self.runtime,
            "container",
            self.policy,
            {"wall_time_seconds": 900, "max_completed_commands": 40, "max_attempts": 3},
            public_test_command="python3 --version",
        )

    def tearDown(self):
        self.raw.cleanup()

    def test_model_client_runs_tools_on_bridge_and_retains_telemetry(self):
        class FakeClient(controller.ResponsesModelClient):
            def __init__(inner, *args, **kwargs):
                super().__init__(*args, **kwargs)
                inner.payloads = []

            def request(inner, payload):
                inner.payloads.append(payload)
                if len(inner.payloads) == 1:
                    return {
                        "output": [{
                            "type": "function_call",
                            "name": "inspect_file",
                            "call_id": "call-1",
                            "arguments": json.dumps({"path": "CANARY.txt"}),
                        }],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    }
                return {
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": "complete"}]}],
                    "usage": {"input_tokens": 8, "output_tokens": 3},
                }

        raw_path = self.root / "raw.jsonl"
        client = FakeClient("host-secret", "gpt-5.6-sol", self.policy, self.bridge, raw_path)
        result = client.run("canary", forced_first_tool="inspect_file")
        self.assertEqual(result, "complete")
        self.assertEqual(self.bridge.files_inspected, {"CANARY.txt"})
        self.assertEqual(self.bridge.guard.telemetry()["input_tokens"], 18)
        self.assertTrue(all(payload["store"] is False for payload in client.payloads))
        self.assertNotIn("host-secret", json.dumps(client.payloads))

    def test_missing_certificate_deletes_plaintext(self):
        raw_path = self.root / "private.jsonl"
        raw_path.write_text("secret\n", encoding="utf-8")
        with self.assertRaisesRegex(controller.ControllerError, "certificate"):
            controller.encrypted_raw_output(raw_path, self.root / "raw.p7m", "")
        self.assertFalse(raw_path.exists())

    @unittest.skipUnless(shutil.which("openssl"), "openssl is required")
    def test_encrypted_raw_output_round_trip_and_plaintext_removal(self):
        cert = self.root / "cert.pem"
        key = self.root / "key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-subj", "/CN=aeg-test", "-days", "1",
        ], check=True, capture_output=True)
        raw_path = self.root / "private.jsonl"
        encrypted = self.root / "private.p7m"
        decrypted = self.root / "decrypted.jsonl"
        raw_path.write_text("private model output\n", encoding="utf-8")
        self.assertTrue(controller.encrypted_raw_output(raw_path, encrypted, cert.read_text(encoding="utf-8")))
        self.assertFalse(raw_path.exists())
        subprocess.run([
            "openssl", "cms", "-decrypt", "-binary", "-inform", "DER",
            "-in", str(encrypted), "-recip", str(cert), "-inkey", str(key), "-out", str(decrypted),
        ], check=True, capture_output=True)
        self.assertEqual(decrypted.read_text(encoding="utf-8"), "private model output\n")

    def test_historical_path_detection_uses_registered_patterns(self):
        pair = controller.fixture_pair(controller.load_json(controller.MANIFEST), "s1-02-fastapi-pydantic")
        repeated = controller.repeated_historical_paths(pair, "field.type_ is list")
        self.assertEqual(repeated, ["special_case_list_only"])

    def test_assumption_sanitizer_retains_no_agent_evidence(self):
        pair = controller.fixture_pair(controller.load_json(controller.MANIFEST), "s1-02-fastapi-pydantic")
        agent_result = {
            "environment_assumptions_checked": [{
                "assumption": pair["environment_assumptions"][0],
                "checked": True,
                "evidence": "PRIVATE RAW MODEL EVIDENCE",
            }]
        }
        sanitized = controller.sanitized_assumption_metrics(pair, agent_result)
        self.assertTrue(sanitized[0]["checked"])
        self.assertNotIn("PRIVATE RAW MODEL EVIDENCE", json.dumps(sanitized))
        self.assertEqual(len(sanitized), len(pair["environment_assumptions"]))


if __name__ == "__main__":
    unittest.main()
