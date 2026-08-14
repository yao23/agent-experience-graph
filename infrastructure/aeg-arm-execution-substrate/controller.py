#!/usr/bin/env python3
"""Host-only controller for disposable AEG repair and evaluator containers."""

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BENCH = REPO / "experiments" / "situated-experience-benchmark-v1"
MANIFEST = BENCH / "s1-manifest.json"
PLAN = BENCH / "execution" / "s1-execution-plan.json"
POLICY = HERE / "policy.json"
CANARY_SCHEMA = HERE / "schemas" / "canary-result.schema.json"
ARM_RESULT_SCHEMA = BENCH / "schemas" / "arm-result.schema.json"
AGENT_RESULT_SCHEMA = BENCH / "schemas" / "agent-result.schema.json"
WORKFLOW = REPO / ".github" / "workflows" / "aeg-arm-execution-substrate.yml"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"


class ControllerError(RuntimeError):
    pass


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schema_validate(instance, schema_path, label):
    validator = Draft202012Validator(load_json(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        rendered = "; ".join(f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors)
        raise ControllerError(f"{label} schema invalid: {rendered}")


def scrubbed_host_environment():
    sensitive_fragments = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "CREDENTIAL")
    return {
        name: value
        for name, value in os.environ.items()
        if name not in {"OPENAI_API_KEY", "GITHUB_TOKEN", "AEG_RAW_OUTPUT_CERT_PEM"}
        and not name.startswith("ACTIONS_")
        and not any(fragment in name.upper() for fragment in sensitive_fragments)
    }


def run(args, cwd=None, input_text=None, timeout=120, check=True, env=None):
    result = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        env=scrubbed_host_environment() if env is None else env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        raise ControllerError(result.stderr.strip() or result.stdout.strip() or f"command failed: {args[0]}")
    return result


def encoded_sanitized_bundle(task_root, max_bytes):
    task_root = Path(task_root)
    entries = [task_root / "arm.json", task_root / "task"]
    entries.extend(sorted((task_root / "task").rglob("*")))
    total = 0
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        for path in entries:
            if path.is_symlink():
                raise ControllerError("container bundle contains a symlink")
            if not path.is_dir() and not path.is_file():
                raise ControllerError("container bundle contains a non-regular entry")
            if path.is_file():
                total += path.stat().st_size
            if total > max_bytes:
                raise ControllerError("container bundle exceeds the workspace ceiling")
            relative = path.relative_to(task_root).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            info.mode = 0o755 if path.is_dir() else 0o644
            if path.is_file():
                with path.open("rb") as handle:
                    archive.addfile(info, handle)
            else:
                archive.addfile(info)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def expected_arm_ids(manifest):
    values = []
    for pair in manifest["pairs"]:
        for replicate, order in enumerate(manifest["protocol"]["arm_orders"][pair["pair_id"]], 1):
            for mode in order:
                values.append(f"{pair['pair_id']}--r{replicate:02d}--{mode}")
    return values


def validate_configuration():
    policy = load_json(POLICY)
    manifest = load_json(MANIFEST)
    plan = load_json(PLAN)
    expected_manifest = policy["benchmark"]["manifest_sha256"]
    expected_plan = policy["benchmark"]["execution_plan_sha256"]
    if sha256_file(MANIFEST) != expected_manifest:
        raise ControllerError("frozen manifest hash differs from substrate policy")
    if sha256_file(PLAN) != expected_plan:
        raise ControllerError("frozen execution-plan hash differs from substrate policy")
    if manifest["protocol"]["model"] != policy["benchmark"]["model"]:
        raise ControllerError("model differs from frozen manifest")
    if policy["bridge"]["max_model_turns"] <= manifest["protocol"]["budget"]["max_completed_commands"]:
        raise ControllerError("model-turn safety ceiling would reduce the frozen command budget")
    plan_ids = [item["arm_id"] for item in plan["arms"]]
    if plan_ids != expected_arm_ids(manifest) or plan["arm_count"] != 12:
        raise ControllerError("tracked execution plan differs from frozen arm order")
    dockerfile = (HERE / "Dockerfile").read_text(encoding="utf-8")
    if f"FROM {policy['base_image']}" not in dockerfile:
        raise ControllerError("Dockerfile base image is not the pinned policy image")
    if WORKFLOW.exists():
        workflow_text = WORKFLOW.read_text(encoding="utf-8")
        workflow_coordinates = re.findall(
            r"- sequence:\s*(\d+)\s+arm_id:\s*(s1-[a-z0-9-]+--r\d{2}--(?:control|aeg-assisted))",
            workflow_text,
        )
        if workflow_coordinates != [(str(index), arm_id) for index, arm_id in enumerate(plan_ids, 1)]:
            raise ControllerError("workflow matrix differs from the frozen arm order")
    result = run(["python3", str(BENCH / "run_benchmark.py"), "validate"], cwd=REPO)
    return {
        "status": "valid",
        "substrate_id": policy["substrate_id"],
        "manifest_sha256": expected_manifest,
        "execution_plan_sha256": expected_plan,
        "arms": len(plan_ids),
        "benchmark_validation": json.loads(result.stdout)["status"],
    }


class BudgetGuard:
    def __init__(self, policy, arm_budget):
        self.policy = policy
        self.arm_budget = arm_budget
        self.started = time.monotonic()
        self.commands = 0
        self.tool_turns = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.cost_usd = 0.0

    def check_wall(self):
        if time.monotonic() - self.started > self.arm_budget["wall_time_seconds"]:
            raise ControllerError("wall-time budget exceeded")

    def add_tool_turn(self):
        self.check_wall()
        self.tool_turns += 1
        if self.tool_turns > self.policy["bridge"]["max_model_turns"]:
            raise ControllerError("model tool-turn limit exceeded")

    def add_command(self):
        self.check_wall()
        self.commands += 1
        if self.commands > self.arm_budget["max_completed_commands"]:
            raise ControllerError("completed-command budget exceeded")

    def add_usage(self, usage):
        self.check_wall()
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        details = usage.get("input_tokens_details") or {}
        cached = int(details.get("cached_tokens") or 0)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cached_tokens += min(cached, input_tokens)
        uncached = max(input_tokens - cached, 0)
        prices = self.policy["pricing_usd_per_million_tokens"]
        self.cost_usd += (
            uncached * prices["input"]
            + cached * prices["cached_input"]
            + output_tokens * prices["output"]
        ) / 1_000_000
        ceiling = self.policy["safety_ceiling"]
        if self.input_tokens + self.output_tokens > ceiling["max_total_tokens"]:
            raise ControllerError("token safety ceiling exceeded")
        if self.cost_usd > ceiling["max_cost_usd"]:
            raise ControllerError("cost safety ceiling exceeded")

    def check_workspace(self, size):
        if size > self.policy["container"]["workspace_bytes"]:
            raise ControllerError("workspace disk ceiling exceeded")

    def telemetry(self):
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_tokens,
            "estimated_cost_usd": round(self.cost_usd, 8),
        }


class DockerRuntime:
    def __init__(self, image, policy):
        self.image = image
        self.policy = policy

    def security_args(self, task_root, name):
        limits = self.policy["container"]
        return [
            "docker", "run", "--detach", "--name", name,
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", str(limits["pids_limit"]),
            "--memory", str(limits["memory_bytes"]),
            "--memory-swap", str(limits["memory_bytes"]),
            "--cpus", str(limits["cpus"]),
            "--ulimit", "nofile=256:256",
            "--ipc", "private",
            "--hostname", "aeg-repair",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--tmpfs", f"/tmp:rw,noexec,nosuid,nodev,size={limits['tmpfs_bytes']}",
            "--tmpfs", f"/workspace:rw,nosuid,nodev,size={limits['workspace_bytes']},mode=0700,uid={os.getuid()},gid={os.getgid()}",
            self.image,
            "hold",
        ]

    def start(self, task_root, prefix="aeg-repair"):
        task_root = Path(task_root)
        entries = {path.name for path in task_root.iterdir()}
        if entries != {"arm.json", "task"}:
            raise ControllerError(f"container mount entries differ from allowlist: {sorted(entries)}")
        name = f"{prefix}-{uuid.uuid4().hex[:12]}"
        result = run(self.security_args(task_root, name))
        container_id = result.stdout.strip()
        if not container_id:
            raise ControllerError("Docker did not return a container id")
        try:
            payload = encoded_sanitized_bundle(task_root, self.policy["container"]["workspace_bytes"])
            self.exec(
                container_id,
                ["import-bundle", "--max-bytes", str(self.policy["container"]["workspace_bytes"])],
                input_text=payload,
            )
            self.exec(container_id, ["baseline-create"])
        except Exception:
            self.remove(container_id)
            raise
        return container_id

    def worker_command(self, container_id, arguments):
        env = self.policy["container"]["allowed_process_environment"]
        assignments = [f"{key}={value}" for key, value in sorted(env.items())]
        return [
            "docker", "exec", "--interactive", container_id, "/usr/bin/env", "-i", *assignments,
            "python3", "/opt/aeg/container_worker.py", *arguments,
        ]

    def exec(self, container_id, arguments, input_text=None, timeout=120, check=True):
        try:
            result = run(self.worker_command(container_id, arguments), input_text=input_text, timeout=timeout, check=check)
        except subprocess.TimeoutExpired:
            run(["docker", "kill", container_id], timeout=30, check=False)
            raise
        if check:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                raise ControllerError("container worker returned invalid JSON") from None
        return result

    def security_attestation(self, container_id):
        inspected = run(["docker", "inspect", container_id])
        value = json.loads(inspected.stdout)[0]
        host = value["HostConfig"]
        expected = self.policy["container"]
        passed = (
            host.get("NetworkMode") == "none"
            and host.get("PidMode") in (None, "")
            and host.get("ReadonlyRootfs") is True
            and set(host.get("CapDrop") or []) == {"ALL"}
            and "no-new-privileges:true" in (host.get("SecurityOpt") or [])
            and int(host.get("PidsLimit") or 0) == expected["pids_limit"]
            and int(host.get("Memory") or 0) == expected["memory_bytes"]
            and int(host.get("NanoCpus") or 0) == int(expected["cpus"] * 1_000_000_000)
            and not any("docker.sock" in mount.get("Source", "") for mount in value.get("Mounts", []))
            and not value.get("Mounts")
            and not host.get("Binds")
            and set((host.get("Tmpfs") or {}).keys()) == {"/tmp", "/workspace"}
        )
        return passed

    def image_id(self):
        result = run(["docker", "image", "inspect", self.image, "--format", "{{.Id}}"])
        return result.stdout.strip() or None

    def remove(self, container_id):
        run(["docker", "rm", "--force", container_id], check=False)


class ToolBridge:
    def __init__(self, runtime, container_id, policy, arm_budget, public_test_command=None):
        self.runtime = runtime
        self.container_id = container_id
        self.policy = policy
        self.public_test_argv = shlex.split(public_test_command) if public_test_command else None
        self.guard = BudgetGuard(policy, arm_budget)
        self.files_inspected = set()
        self.tests = []
        self.attempt_hashes = []
        self.tool_events = []

    def _record(self, name, arguments, result):
        self.tool_events.append({"tool": name, "arguments": arguments, "result": result})

    def call(self, name, arguments):
        self.guard.add_tool_turn()
        allowed = set(self.policy["bridge"]["allowed_tools"])
        if name not in allowed or not isinstance(arguments, dict):
            raise ControllerError("model requested an unknown tool")
        if name == "inspect_file":
            if set(arguments) != {"path"} or not isinstance(arguments["path"], str):
                raise ControllerError("inspect_file arguments are invalid")
            result = self.runtime.exec(
                self.container_id,
                ["inspect", "--path", arguments["path"], "--limit", str(self.policy["bridge"]["max_file_read_bytes"])],
            )
            self.files_inspected.add(result["path"])
        elif name == "run_command":
            if set(arguments) != {"command"} or not isinstance(arguments["command"], str):
                raise ControllerError("run_command arguments are invalid")
            self.guard.add_command()
            argv = shlex.split(arguments["command"])
            result = self.runtime.exec(
                self.container_id,
                ["run", "--argv-json", json.dumps(argv), "--timeout", "120"],
                timeout=125,
            )
            if self.public_test_argv is not None and result.get("argv") == self.public_test_argv:
                self.tests.append({"command": arguments["command"], "scope": "agent", "passed": result["exit_code"] == 0})
        elif name == "run_visible_tests":
            if arguments:
                raise ControllerError("run_visible_tests accepts no arguments")
            self.guard.add_command()
            result = self.runtime.exec(self.container_id, ["visible-test", "--timeout", "120"], timeout=125)
            self.tests.append({"command": "registered visible test", "scope": "agent", "passed": result["exit_code"] == 0})
        else:
            if set(arguments) != {"patch"} or not isinstance(arguments["patch"], str):
                raise ControllerError("apply_patch arguments are invalid")
            if len(arguments["patch"].encode()) > self.policy["bridge"]["max_patch_bytes"]:
                raise ControllerError("patch exceeds bridge limit")
            result = self.runtime.exec(
                self.container_id,
                ["apply-patch", "--max-bytes", str(self.policy["bridge"]["max_patch_bytes"])],
                input_text=arguments["patch"],
            )
            snapshot = self.runtime.exec(self.container_id, ["snapshot"])
            self.guard.check_workspace(snapshot["bytes"])
            if snapshot["sha256"] not in self.attempt_hashes:
                if len(self.attempt_hashes) >= self.guard.arm_budget["max_attempts"]:
                    raise ControllerError("repair-attempt budget exceeded")
                self.attempt_hashes.append(snapshot["sha256"])
        serialized = json.dumps(result, sort_keys=True)
        if len(serialized.encode()) > self.policy["bridge"]["max_tool_output_bytes"]:
            raise ControllerError("tool output exceeds bridge limit")
        self._record(name, {key: "<patch>" if key == "patch" else value for key, value in arguments.items()}, result)
        return result


def function_tools():
    return [
        {
            "type": "function",
            "name": "inspect_file",
            "description": "Read one relative file or list one relative directory inside the repair task workspace.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_command",
            "description": "Run an allowlisted diagnostic or registered visible-test command inside the repair container.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "apply_patch",
            "description": "Apply a unified diff to existing production files inside the repair workspace. Tests and task inputs are protected.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"patch": {"type": "string"}},
                "required": ["patch"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_visible_tests",
            "description": "Run the envelope's registered visible test command inside the repair container.",
            "strict": True,
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    ]


def output_text(response):
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    values = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                values.append(content["text"])
    return "".join(values)


class ResponsesModelClient:
    def __init__(self, api_key, model, policy, bridge, raw_path):
        if not api_key:
            raise ControllerError("host model credential is unavailable")
        self.api_key = api_key
        self.model = model
        self.policy = policy
        self.bridge = bridge
        self.raw_path = Path(raw_path)
        self.raw_path.parent.mkdir(parents=True, exist_ok=True)

    def request(self, payload):
        request = urllib.request.Request(
            OPENAI_ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:1000]
            raise ControllerError(f"model API request failed with HTTP {error.code}: {detail}") from None
        except urllib.error.URLError as error:
            raise ControllerError(f"model API request failed: {error.reason}") from None

    def run(self, prompt, final_schema=None, forced_first_tool=None):
        conversation = [{"role": "user", "content": prompt}]
        final = ""
        for turn in range(self.policy["bridge"]["max_model_turns"]):
            payload = {
                "model": self.model,
                "input": conversation,
                "tools": function_tools(),
                "parallel_tool_calls": False,
                "store": False,
                "max_output_tokens": self.policy["safety_ceiling"]["max_output_tokens_per_response"],
            }
            if turn == 0 and forced_first_tool:
                payload["tool_choice"] = {"type": "function", "name": forced_first_tool}
            if final_schema:
                payload["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": "agent_result",
                        "strict": True,
                        "schema": final_schema,
                    }
                }
            response = self.request(payload)
            self.bridge.guard.add_usage(response.get("usage") or {})
            with self.raw_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"kind": "model_response", "value": response}, sort_keys=True) + "\n")
            calls = [item for item in response.get("output", []) if item.get("type") == "function_call"]
            conversation.extend(response.get("output", []))
            if not calls:
                final = output_text(response)
                break
            for call in calls:
                try:
                    arguments = json.loads(call.get("arguments") or "{}")
                except json.JSONDecodeError:
                    raise ControllerError("model returned invalid tool arguments") from None
                result = self.bridge.call(call.get("name"), arguments)
                with self.raw_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"kind": "tool_result", "call_id": call.get("call_id"), "value": result}, sort_keys=True) + "\n")
                conversation.append({
                    "type": "function_call_output",
                    "call_id": call.get("call_id"),
                    "output": json.dumps(result, sort_keys=True),
                })
        else:
            raise ControllerError("model turn limit exceeded")
        if not final:
            raise ControllerError("model returned no final output")
        return final


def encrypted_raw_output(raw_path, encrypted_path, certificate_pem):
    raw_path = Path(raw_path)
    encrypted_path = Path(encrypted_path)
    try:
        if not certificate_pem or "BEGIN CERTIFICATE" not in certificate_pem:
            raise ControllerError("raw-output public certificate is unavailable")
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="aeg-public-cert-") as raw:
            cert = Path(raw) / "recipient.pem"
            cert.write_text(certificate_pem, encoding="utf-8")
            run([
                "openssl", "cms", "-encrypt", "-binary", "-aes-256-cbc",
                "-in", str(raw_path), "-out", str(encrypted_path), "-outform", "DER", str(cert),
            ])
        return encrypted_path.is_file() and encrypted_path.stat().st_size > 0
    finally:
        raw_path.unlink(missing_ok=True)


def stage_root(source, destination, arm):
    destination = Path(destination)
    if destination.exists():
        raise ControllerError("container staging root already exists")
    destination.mkdir(parents=True)
    shutil.copyfile(arm, destination / "arm.json")
    shutil.copytree(source, destination / "task")
    return destination


def fixture_pair(manifest, pair_id):
    for pair in manifest["pairs"]:
        if pair["pair_id"] == pair_id:
            return pair
    raise ControllerError(f"unknown pair: {pair_id}")


def minimal_arm(command):
    return {"public_test_command": command}


def revalidate_fixtures(image, output):
    validation = validate_configuration()
    policy = load_json(POLICY)
    manifest = load_json(MANIFEST)
    runtime = DockerRuntime(image, policy)
    details = []
    failures = patches = 0
    for pair in manifest["pairs"]:
        for stage in ("source", "transfer"):
            stage_root_path = BENCH / "fixtures" / pair["pair_id"] / stage
            seed_name = "buggy" if stage == "source" else "agent"
            command = pair["source_public_test_command"] if stage == "source" else pair["public_test_command"]
            pattern = pair["source_initial_failure_pattern"] if stage == "source" else pair["initial_failure_pattern"]
            with tempfile.TemporaryDirectory(prefix="aeg-fixture-container-") as raw:
                root = Path(raw) / "repair"
                root.mkdir()
                write_json(root / "arm.json", minimal_arm(command))
                shutil.copytree(stage_root_path / seed_name, root / "task")
                container = runtime.start(root, prefix="aeg-fixture-buggy")
                try:
                    initial = runtime.exec(container, ["visible-test", "--timeout", "120"], timeout=125)
                    combined = initial["stdout"] + "\n" + initial["stderr"]
                    if initial["exit_code"] == 0 or not re.search(pattern, combined, re.IGNORECASE | re.DOTALL):
                        raise ControllerError(f"{pair['pair_id']} {stage} did not fail for the registered reason in the pinned image")
                    failures += 1
                finally:
                    runtime.remove(container)
            with tempfile.TemporaryDirectory(prefix="aeg-evaluator-container-") as raw:
                root = Path(raw) / "evaluator"
                root.mkdir()
                write_json(root / "arm.json", minimal_arm(pair["hidden_test_command"]))
                shutil.copytree(stage_root_path / seed_name, root / "task")
                shutil.copyfile(stage_root_path / "evaluator" / "test_hidden.py", root / "task" / "test_hidden.py")
                container = runtime.start(root, prefix="aeg-fixture-evaluator")
                try:
                    patch_text = (stage_root_path / "evaluator" / "human.patch").read_text(encoding="utf-8")
                    runtime.exec(container, ["apply-patch", "--max-bytes", str(policy["bridge"]["max_patch_bytes"])], input_text=patch_text)
                    evaluated = runtime.exec(container, ["visible-test", "--timeout", "120"], timeout=125)
                    if evaluated["exit_code"] != 0:
                        raise ControllerError(f"{pair['pair_id']} {stage} human patch failed in the pinned evaluator container")
                    patches += 1
                finally:
                    runtime.remove(container)
            details.append({"pair_id": pair["pair_id"], "stage": stage, "buggy_failure_matched": True, "human_patch_passed": True})
    record = {
        "schema_version": "1.0.0",
        "substrate_id": policy["substrate_id"],
        "manifest_sha256": validation["manifest_sha256"],
        "base_image": policy["base_image"],
        "runtime_image_id": runtime.image_id(),
        "buggy_failures": failures,
        "human_patches_passed": patches,
        "details": details,
    }
    write_json(output, record)
    return record


def canary_arm_root(raw, mode):
    root = Path(raw) / f"canary-{mode}"
    root.mkdir()
    write_json(root / "arm.json", minimal_arm("python3 --version"))
    task = root / "task"
    task.mkdir()
    (task / "CANARY.txt").write_text("non-benchmark substrate canary\n", encoding="utf-8")
    return root


def security_canary(runtime, policy, root, forbidden_paths):
    container = runtime.start(root, prefix="aeg-security-canary")
    try:
        attested = runtime.security_attestation(container)
        probe = runtime.exec(container, ["canary-probe", "--forbidden-json", json.dumps(forbidden_paths)])
        attempts = probe["attempts"]
        attempts.append({"id": "container_security_configuration", "passed": attested, "reason": "Docker inspect matches the frozen security policy"})
        pids = runtime.exec(container, ["stress-pids", "--count", "96"], timeout=30)
        attempts.append({"id": "process_limit", "passed": bool(pids["blocked"] and pids["started"] < 96), "reason": "pids-limit rejected excess child processes"})
        memory = runtime.exec(container, ["stress-memory", "--bytes", str(policy["container"]["memory_bytes"] + 268435456)], timeout=30, check=False)
        attempts.append({"id": "memory_limit", "passed": memory.returncode != 0, "reason": "memory cgroup rejected an over-limit allocation"})
        disk = runtime.exec(container, ["stress-disk", "--bytes", str(policy["container"]["workspace_bytes"] * 2)], timeout=30)
        attempts.append({"id": "workspace_tmpfs_limit", "passed": bool(disk["blocked"] and disk["written"] < disk["requested"]), "reason": "workspace tmpfs rejected a write above its hard size limit"})
        wall_blocked = False
        try:
            runtime.exec(container, ["sleep", "--seconds", "5"], timeout=1, check=False)
        except subprocess.TimeoutExpired:
            wall_blocked = True
        attempts.append({"id": "wall_time_limit", "passed": wall_blocked, "reason": "controller timeout killed the over-time repair container"})
        arm_budget = {"wall_time_seconds": 900, "max_completed_commands": 40, "max_attempts": 3}
        guard = BudgetGuard(policy, arm_budget)
        command_passed = False
        try:
            for _ in range(41):
                guard.add_command()
        except ControllerError:
            command_passed = True
        attempts.append({"id": "command_limit", "passed": command_passed, "reason": "controller rejected command 41"})
        token_guard = BudgetGuard(policy, arm_budget)
        token_passed = False
        try:
            token_guard.add_usage({"input_tokens": policy["safety_ceiling"]["max_total_tokens"] + 1, "output_tokens": 0})
        except ControllerError:
            token_passed = True
        attempts.append({"id": "token_limit", "passed": token_passed, "reason": "controller rejected usage above the token ceiling"})
        cost_guard = BudgetGuard(policy, arm_budget)
        cost_passed = False
        try:
            cost_guard.add_usage({"input_tokens": 0, "output_tokens": 2_000_000})
        except ControllerError:
            cost_passed = True
        attempts.append({"id": "cost_limit", "passed": cost_passed, "reason": "controller rejected usage above the cost ceiling"})
        disk_passed = False
        try:
            guard.check_workspace(policy["container"]["workspace_bytes"] + 1)
        except ControllerError:
            disk_passed = True
        attempts.append({"id": "disk_limit", "passed": disk_passed, "reason": "controller rejected a workspace above the disk ceiling"})
        return attempts, attested
    finally:
        runtime.remove(container)


def canary_sanitized_result():
    return {
        "schema_version": "1.0.0",
        "benchmark_id": "situated-experience-benchmark-v1",
        "family": "S1",
        "pair_id": "non-benchmark-substrate-canary",
        "replicate": 1,
        "mode": "control",
        "evaluation_status": "evaluated",
        "input_hashes": {"arm": "0" * 64, "task": "1" * 64, "manifest": "2" * 64},
        "budget": {"wall_time_seconds": 60, "max_completed_commands": 4, "max_attempts": 1},
        "regression_free_success": True,
        "attempts": 1,
        "completed_commands": 1,
        "tests_run": [{"command": "non-benchmark evaluator canary", "scope": "hidden", "passed": True}],
        "files_inspected": ["module.py"],
        "files_changed": ["module.py"],
        "patch_size": {"added_lines": 1, "deleted_lines": 1, "files": 1},
        "wall_time_ms": 1,
        "tokens": {"input": 0, "output": 0, "unavailable_reason": None},
        "failed_historical_paths_repeated": [],
        "environment_assumptions_checked": [{"assumption": "canary only", "checked": True, "evidence": "separate evaluator passed"}],
        "experiences": [{"experience_id": None, "disposition": "abstained", "reason": "non-benchmark canary"}],
        "negative_transfer": None,
        "evaluator_findings": ["non-benchmark hidden evaluator passed after repair termination"],
        "limitations": ["synthetic substrate canary; not a benchmark arm or outcome"],
    }


def functional_boundary_canary(runtime, policy, raw):
    attempts = []
    repair_root = Path(raw) / "functional-repair"
    repair_root.mkdir()
    write_json(repair_root / "arm.json", minimal_arm("python3 --version"))
    task = repair_root / "task"
    task.mkdir()
    (task / "module.py").write_text("VALUE = 'old'\n", encoding="utf-8")
    (task / "ISSUE.md").write_text("protected canary input\n", encoding="utf-8")
    repair = runtime.start(repair_root, prefix="aeg-functional-repair")
    exported = None
    try:
        bridge = ToolBridge(
            runtime,
            repair,
            policy,
            {"wall_time_seconds": 60, "max_completed_commands": 4, "max_attempts": 1},
            public_test_command="python3 --version",
        )
        bridge.call("inspect_file", {"path": "module.py"})
        bridge.call("apply_patch", {"patch": "--- a/module.py\n+++ b/module.py\n@@ -1 +1 @@\n-VALUE = 'old'\n+VALUE = 'new'\n"})
        bridge.call("run_visible_tests", {})
        exported = runtime.exec(
            repair,
            ["export-patch", "--max-bytes", str(policy["bridge"]["max_patch_bytes"])],
        )
    finally:
        runtime.remove(repair)
    patch_ok = (
        exported is not None
        and exported["files_changed"] == ["module.py"]
        and "+VALUE = 'new'" in exported["patch"]
        and "ISSUE.md" not in exported["patch"]
    )
    attempts.append({"id": "patch_export_allowlist", "passed": patch_ok, "reason": "only the bridge-modified production file was exported"})
    terminated = run(["docker", "inspect", repair], check=False).returncode != 0

    evaluator_root = Path(raw) / "functional-evaluator"
    evaluator_root.mkdir()
    write_json(evaluator_root / "arm.json", minimal_arm("python3 -m unittest -v test_hidden.py"))
    evaluator_task = evaluator_root / "task"
    evaluator_task.mkdir()
    (evaluator_task / "module.py").write_text("VALUE = 'new'\n", encoding="utf-8")
    (evaluator_task / "test_hidden.py").write_text(
        "import unittest\nimport module\n\nclass HiddenCanary(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(module.VALUE, 'new')\n",
        encoding="utf-8",
    )
    evaluator = runtime.start(evaluator_root, prefix="aeg-functional-evaluator")
    try:
        evaluated = runtime.exec(evaluator, ["visible-test", "--timeout", "30"], timeout=35)
    finally:
        runtime.remove(evaluator)
    evaluator_ok = terminated and evaluator != repair and evaluated["exit_code"] == 0
    attempts.append({"id": "repair_termination_before_evaluator", "passed": evaluator_ok, "reason": "repair container was absent before the distinct hidden evaluator started"})

    schema_ok = True
    try:
        schema_validate(canary_sanitized_result(), ARM_RESULT_SCHEMA, "canary sanitized result")
    except ControllerError:
        schema_ok = False
    attempts.append({"id": "sanitizer_measurement_schema", "passed": schema_ok, "reason": "approved canary metrics validate against the frozen arm-result schema"})
    return attempts


def live_model_canary(runtime, policy, api_key, raw_path):
    aggregate = {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}
    modes = {}
    tool_call_in_container = True
    with tempfile.TemporaryDirectory(prefix="aeg-live-model-canary-") as raw:
        for mode in ("control", "treatment"):
            root = canary_arm_root(raw, mode)
            container = runtime.start(root, prefix=f"aeg-model-{mode}")
            try:
                bridge = ToolBridge(
                    runtime,
                    container,
                    policy,
                    {"wall_time_seconds": 180, "max_completed_commands": 40, "max_attempts": 3},
                    public_test_command="python3 --version",
                )
                client = ResponsesModelClient(api_key, policy["benchmark"]["model"], policy, bridge, raw_path)
                prompt = (
                    "This is a non-benchmark security canary. Use inspect_file on CANARY.txt exactly once, "
                    f"then report that the {mode} telemetry canary completed. Do not propose or apply a repair."
                )
                client.run(prompt, forced_first_tool="inspect_file")
                telemetry = bridge.guard.telemetry()
                modes[mode] = telemetry["input_tokens"] > 0 and telemetry["output_tokens"] > 0
                aggregate["input_tokens"] += telemetry["input_tokens"]
                aggregate["output_tokens"] += telemetry["output_tokens"]
                aggregate["estimated_cost_usd"] += telemetry["estimated_cost_usd"]
                tool_call_in_container = tool_call_in_container and any(event["tool"] == "inspect_file" for event in bridge.tool_events)
            finally:
                runtime.remove(container)
    aggregate["estimated_cost_usd"] = round(aggregate["estimated_cost_usd"], 8)
    return modes, tool_call_in_container, aggregate


def canary(image, fixture_record_path, output, encrypted_output):
    validate_configuration()
    policy = load_json(POLICY)
    fixture = load_json(fixture_record_path)
    runtime = DockerRuntime(image, policy)
    credential_present = bool(os.environ.get("OPENAI_API_KEY"))
    certificate = os.environ.get(policy["raw_output"]["public_certificate_environment"], "")
    raw_path = Path(tempfile.mkdtemp(prefix="aeg-canary-private-")) / "raw.jsonl"
    raw_path.write_text("", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="aeg-substrate-canary-") as raw:
        host_private = Path(raw) / "controller-private"
        other_arm = Path(raw) / "other-synthetic-arm"
        host_private.mkdir()
        other_arm.mkdir()
        (host_private / "controller-sentinel").write_text("controller-only\n", encoding="utf-8")
        (host_private / "human.patch").write_text("controller-only\n", encoding="utf-8")
        (host_private / "test_hidden.py").write_text("controller-only\n", encoding="utf-8")
        (host_private / "prior-transcript.jsonl").write_text("controller-only\n", encoding="utf-8")
        (other_arm / "sentinel").write_text("other-arm-only\n", encoding="utf-8")
        probe_root = canary_arm_root(raw, "security")
        attempts, security_matches = security_canary(
            runtime,
            policy,
            probe_root,
            [str(host_private), str(other_arm), "/github/workspace/controller-sentinel"],
        )
        attempts.extend(functional_boundary_canary(runtime, policy, raw))
    modes = {"control": False, "treatment": False}
    tool_inside = False
    telemetry = {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}
    model_error = None
    if credential_present:
        try:
            modes, tool_inside, telemetry = live_model_canary(runtime, policy, os.environ["OPENAI_API_KEY"], raw_path)
        except ControllerError as error:
            model_error = str(error)
    else:
        model_error = "host model credential is unavailable"
    encrypted = False
    if raw_path.exists():
        try:
            encrypted = encrypted_raw_output(raw_path, encrypted_output, certificate)
        except ControllerError as error:
            model_error = model_error or str(error)
    fixture_passed = fixture.get("buggy_failures") == 4 and fixture.get("human_patches_passed") == 4
    passed = (
        all(item["passed"] for item in attempts)
        and security_matches
        and credential_present
        and modes["control"]
        and modes["treatment"]
        and tool_inside
        and fixture_passed
        and encrypted
        and not raw_path.exists()
    )
    status = "passed" if passed else ("blocked" if not credential_present or not certificate else "failed")
    if model_error:
        attempts.append({"id": "model_or_encryption_boundary", "passed": False, "reason": model_error})
    attempt_evidence = {item["id"]: item["passed"] for item in attempts}
    record = {
        "schema_version": "1.0.0",
        "substrate_id": policy["substrate_id"],
        "status": status,
        "runner": {
            "label": policy["runner_label"],
            "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
        },
        "container": {
            "base_image": policy["base_image"],
            "runtime_image_id": runtime.image_id(),
            "security_configuration_matches": security_matches,
        },
        "credential_boundary": {
            "credential_present_in_controller": credential_present,
            "credential_present_in_repair": not attempt_evidence.get("api_key", False),
            "github_token_present_in_repair": not attempt_evidence.get("github_token", False),
        },
        "attempts": attempts,
        "fixture_revalidation": {
            "buggy_failures": int(fixture.get("buggy_failures", 0)),
            "human_patches_passed": int(fixture.get("human_patches_passed", 0)),
        },
        "model_boundary": {
            "model": policy["benchmark"]["model"],
            "control_telemetry": modes["control"],
            "treatment_telemetry": modes["treatment"],
            "tool_call_executed_in_container": tool_inside,
            "input_tokens": telemetry["input_tokens"],
            "output_tokens": telemetry["output_tokens"],
            "estimated_cost_usd": telemetry["estimated_cost_usd"],
        },
        "raw_output": {
            "encrypted": encrypted,
            "plaintext_removed": not raw_path.exists(),
            "format": policy["raw_output"]["format"],
        },
        "benchmark_arms_executed": 0,
    }
    schema_validate(record, CANARY_SCHEMA, "canary result")
    write_json(output, record)
    if status != "passed":
        raise ControllerError(f"hosted canary is {status}")
    return record


def render_frozen_prompt(envelope):
    spec = importlib.util.spec_from_file_location("frozen_arm_worker", BENCH / "arm_worker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_prompt(envelope)


def audit_frozen_bundle(manifest, pair, bundle, replicate, mode):
    spec = importlib.util.spec_from_file_location("frozen_benchmark_runner", BENCH / "run_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run = lambda args, cwd=None, timeout=120, env=None, input_text=None: run(
        args,
        cwd=cwd,
        input_text=input_text,
        timeout=timeout,
        check=False,
        env=scrubbed_host_environment() if env is None else env,
    )
    bundle = Path(bundle)
    module.audit_bundle(manifest, pair, bundle)
    if module.tree_sha256(bundle / "workspace") != pair["agent_fixture_sha256"]:
        raise ControllerError("arm workspace differs from the frozen agent fixture")
    with tempfile.TemporaryDirectory(prefix="aeg-expected-arm-") as raw:
        expected_bundle = Path(raw) / "expected"
        module.package_arm(manifest, pair, replicate, mode, expected_bundle)
        if load_json(bundle / "arm.json") != load_json(expected_bundle / "arm.json"):
            raise ControllerError("sanitized arm envelope differs from the frozen package")
    return {"arm_id": f"{pair['pair_id']}--r{replicate:02d}--{mode}", "status": "passed"}


def patch_stats(diff_text):
    added = deleted = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def repeated_historical_paths(pair, evidence):
    return [
        item["id"]
        for item in pair["historical_failure_paths"]
        if re.search(item["pattern"], evidence, re.IGNORECASE | re.DOTALL)
    ]


def sanitized_assumption_metrics(pair, agent_result):
    reported = {
        item.get("assumption"): bool(item.get("checked"))
        for item in agent_result.get("environment_assumptions_checked", [])
        if isinstance(item, dict) and item.get("assumption") in pair["environment_assumptions"]
    }
    return [
        {
            "assumption": assumption,
            "checked": reported.get(assumption, False),
            "evidence": (
                "agent structured result marked this preregistered assumption checked; raw evidence retained encrypted"
                if reported.get(assumption, False)
                else "agent did not mark this preregistered assumption checked"
            ),
        }
        for assumption in pair["environment_assumptions"]
    ]


def arm_coordinate(arm_id):
    match = re.fullmatch(r"(s1-[a-z0-9-]+)--r(\d{2})--(control|aeg-assisted)", arm_id)
    if not match:
        raise ControllerError("arm id is invalid")
    return match.group(1), int(match.group(2)), match.group(3)


def execute_arm(image, bundle, arm_id, sequence, sanitized_output, encrypted_output):
    policy = load_json(POLICY)
    manifest = load_json(MANIFEST)
    plan = load_json(PLAN)
    validate_configuration()
    plan_ids = [item["arm_id"] for item in plan["arms"]]
    if arm_id not in plan_ids:
        raise ControllerError("arm is not in the frozen plan")
    if sequence != plan_ids.index(arm_id) + 1:
        raise ControllerError("arm sequence differs from the frozen plan")
    pair_id, replicate, mode = arm_coordinate(arm_id)
    pair = fixture_pair(manifest, pair_id)
    bundle = Path(bundle)
    audit_frozen_bundle(manifest, pair, bundle, replicate, mode)
    envelope = load_json(bundle / "arm.json")
    if envelope["arm_id"] != arm_id or envelope["mode"] != mode or envelope["replicate"] != replicate:
        raise ControllerError("bundle coordinate differs from the frozen plan")
    runtime = DockerRuntime(image, policy)
    raw_dir = Path(tempfile.mkdtemp(prefix="aeg-arm-private-"))
    raw_path = raw_dir / "raw.jsonl"
    raw_path.write_text("", encoding="utf-8")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aeg-one-arm-") as raw:
        repair_root = stage_root(bundle / "workspace", Path(raw) / "repair", bundle / "arm.json")
        container = runtime.start(repair_root)
        try:
            bridge = ToolBridge(
                runtime,
                container,
                policy,
                envelope["budget"],
                public_test_command=envelope["public_test_command"],
            )
            client = ResponsesModelClient(
                os.environ.get("OPENAI_API_KEY"),
                envelope["model"],
                policy,
                bridge,
                raw_path,
            )
            final_text = client.run(render_frozen_prompt(envelope), final_schema=load_json(AGENT_RESULT_SCHEMA))
            agent_result = json.loads(final_text)
            schema_validate(agent_result, AGENT_RESULT_SCHEMA, "agent result")
            exported = runtime.exec(
                container,
                ["export-patch", "--max-bytes", str(policy["bridge"]["max_patch_bytes"])],
            )
        finally:
            runtime.remove(container)
        patch_text = exported["patch"]
        changed = exported["files_changed"]
        with raw_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"kind": "repair_patch", "value": patch_text}, sort_keys=True) + "\n")
        historical_evidence = patch_text + "\n" + raw_path.read_text(encoding="utf-8", errors="replace")
        evaluator_root = Path(raw) / "evaluator"
        evaluator_root.mkdir()
        write_json(evaluator_root / "arm.json", minimal_arm(pair["hidden_test_command"]))
        shutil.copytree(BENCH / "fixtures" / pair_id / "transfer" / "agent", evaluator_root / "task")
        shutil.copyfile(BENCH / "fixtures" / pair_id / "transfer" / "evaluator" / "test_hidden.py", evaluator_root / "task" / "test_hidden.py")
        evaluator = runtime.start(evaluator_root, prefix="aeg-evaluator")
        try:
            if patch_text:
                runtime.exec(evaluator, ["apply-patch", "--max-bytes", str(policy["bridge"]["max_patch_bytes"])], input_text=patch_text)
            evaluated = runtime.exec(evaluator, ["visible-test", "--timeout", "120"], timeout=125)
        finally:
            runtime.remove(evaluator)
    added, deleted = patch_stats(patch_text)
    telemetry = bridge.guard.telemetry()
    if mode == "control":
        experiences = [{"experience_id": None, "disposition": "abstained", "reason": "control mode has no AEG experience"}]
    else:
        disposition = agent_result["experience_disposition"]
        experiences = [
            {"experience_id": envelope["experience_id"], "disposition": "retrieved", "reason": "frozen treatment payload delivered"},
            {
                "experience_id": envelope["experience_id"],
                "disposition": disposition,
                "reason": f"agent structured result reported {disposition}; raw rationale retained encrypted",
            },
        ]
    result = {
        "schema_version": "1.0.0",
        "benchmark_id": envelope["benchmark_id"],
        "family": "S1",
        "pair_id": pair_id,
        "replicate": replicate,
        "mode": mode,
        "evaluation_status": "evaluated",
        "input_hashes": envelope["input_hashes"],
        "budget": envelope["budget"],
        "regression_free_success": evaluated["exit_code"] == 0,
        "attempts": len(bridge.attempt_hashes),
        "completed_commands": bridge.guard.commands,
        "tests_run": bridge.tests + [{"command": pair["hidden_test_command"], "scope": "hidden", "passed": evaluated["exit_code"] == 0}],
        "files_inspected": sorted(bridge.files_inspected),
        "files_changed": changed,
        "patch_size": {"added_lines": added, "deleted_lines": deleted, "files": len(changed)},
        "wall_time_ms": round((time.monotonic() - started) * 1000),
        "tokens": {"input": telemetry["input_tokens"], "output": telemetry["output_tokens"], "unavailable_reason": None},
        "failed_historical_paths_repeated": repeated_historical_paths(pair, historical_evidence),
        "environment_assumptions_checked": sanitized_assumption_metrics(pair, agent_result),
        "experiences": experiences,
        "negative_transfer": None,
        "evaluator_findings": [
            f"hidden regression suite {'passed' if evaluated['exit_code'] == 0 else 'failed'}",
            "repair container terminated before evaluator creation",
            "evaluator received no human patch",
        ],
        "limitations": ["AEG Arm Execution Substrate v1", "negative transfer pending paired comparison"],
    }
    schema_validate(result, ARM_RESULT_SCHEMA, "sanitized arm result")
    certificate = os.environ.get(policy["raw_output"]["public_certificate_environment"], "")
    encrypted_raw_output(raw_path, encrypted_output, certificate)
    write_json(sanitized_output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("validate")
    fixtures = sub.add_parser("revalidate-fixtures")
    fixtures.add_argument("--image", required=True)
    fixtures.add_argument("--output", required=True)
    canary_parser = sub.add_parser("canary")
    canary_parser.add_argument("--image", required=True)
    canary_parser.add_argument("--fixture-record", required=True)
    canary_parser.add_argument("--output", required=True)
    canary_parser.add_argument("--encrypted-raw-output", required=True)
    execute = sub.add_parser("execute-arm")
    execute.add_argument("--image", required=True)
    execute.add_argument("--bundle", required=True)
    execute.add_argument("--arm-id", required=True)
    execute.add_argument("--sequence", required=True, type=int)
    execute.add_argument("--sanitized-output", required=True)
    execute.add_argument("--encrypted-raw-output", required=True)
    args = parser.parse_args()
    if args.action == "validate":
        result = validate_configuration()
    elif args.action == "revalidate-fixtures":
        result = revalidate_fixtures(args.image, args.output)
    elif args.action == "canary":
        result = canary(args.image, args.fixture_record, args.output, args.encrypted_raw_output)
    else:
        result = execute_arm(args.image, args.bundle, args.arm_id, args.sequence, args.sanitized_output, args.encrypted_raw_output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControllerError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"arm substrate error: {error}", file=sys.stderr)
        raise SystemExit(2)
