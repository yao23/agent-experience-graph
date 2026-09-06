#!/usr/bin/env python3
"""Probe a constrained container and run the pinned public replay once."""

from __future__ import annotations

from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any


OUTPUT = Path("/work/canary-result.json")
REPLAY = Path("/source/examples/evidence-path-confinement/replay.py")
ORIGINAL_NON_MAINLINE_COMMIT = "4f1d26e80a4fba7460cfb2523905fb08619bd08d"
EXPECTED_ENVIRONMENT_KEYS = {
    "CANARY_RUN_ID",
    "CONTROL_REVISION",
    "HOME",
    "PATH",
    "PYTHONDONTWRITEBYTECODE",
    "RUNNER_ARCHITECTURE",
    "SENTINEL_PATH",
    "SOURCE_REF",
    "SOURCE_REPOSITORY",
    "SOURCE_REVISION",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_status_fields() -> dict[str, str]:
    wanted = {"CapEff", "NoNewPrivs", "Seccomp"}
    observed: dict[str, str] = {}
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key in wanted:
            observed[key] = value.strip()
    return observed


def mount_points() -> list[str]:
    points: list[str] = []
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 5:
            points.append(fields[4].replace("\\040", " "))
    return sorted(set(points))


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", "/source", *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def add_probe(
    probes: list[dict[str, Any]], name: str, passed: bool, observation: Any
) -> None:
    probes.append({"name": name, "passed": bool(passed), "observation": observation})


def run_boundary_probes() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    environment_keys = set(os.environ)
    add_probe(
        probes,
        "sanitized_environment",
        environment_keys == EXPECTED_ENVIRONMENT_KEYS,
        {"keys": sorted(environment_keys)},
    )

    sensitive_fragments = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "ACTIONS_", "GITHUB_")
    sensitive_keys = sorted(
        key for key in environment_keys if any(fragment in key.upper() for fragment in sensitive_fragments)
    )
    add_probe(probes, "credential_environment_absent", not sensitive_keys, {"keys": sensitive_keys})

    credential_paths = [
        Path("/root/.git-credentials"),
        Path("/root/.config/gh/hosts.yml"),
        Path("/home/runner/.git-credentials"),
        Path("/github/home/.git-credentials"),
    ]
    present_credential_paths = [str(path) for path in credential_paths if path.exists()]
    source_config = Path("/source/.git/config").read_text(encoding="utf-8").lower()
    forbidden_config_markers = [
        marker
        for marker in ("extraheader", "credential.helper", "authorization:", "token")
        if marker in source_config
    ]
    add_probe(
        probes,
        "credential_files_and_checkout_headers_absent",
        not present_credential_paths and not forbidden_config_markers,
        {
            "forbidden_git_config_markers": forbidden_config_markers,
            "present_credential_paths": present_credential_paths,
        },
    )

    sockets = [Path("/var/run/docker.sock"), Path("/run/docker.sock")]
    present_sockets = [str(path) for path in sockets if path.exists()]
    add_probe(probes, "docker_socket_absent", not present_sockets, {"present": present_sockets})

    host_paths = [Path("/home/runner"), Path("/github/home"), Path("/__w"), Path("/Users")]
    present_host_paths = [str(path) for path in host_paths if path.exists()]
    add_probe(probes, "host_home_and_workspace_absent", not present_host_paths, {"present": present_host_paths})

    sentinel = Path(os.environ["SENTINEL_PATH"])
    sentinel_accessible = False
    sentinel_error = "NONE"
    try:
        sentinel.read_bytes()
        sentinel_accessible = True
    except OSError as error:
        sentinel_error = errno.errorcode.get(error.errno or 0, type(error).__name__)
    add_probe(
        probes,
        "outside_synthetic_sentinel_inaccessible",
        not sentinel_accessible,
        {"error_code": sentinel_error},
    )

    write_probe = Path("/work/read-write-probe.txt")
    write_probe.write_text("bounded\n", encoding="utf-8")
    work_read_write = write_probe.read_text(encoding="utf-8") == "bounded\n"
    write_probe.unlink()
    add_probe(probes, "work_directory_read_write", work_read_write, {"round_trip": work_read_write})

    source_probe = Path("/source/.aeg-runtime-canary-write-probe")
    source_write_error = "NONE"
    source_write_succeeded = False
    try:
        source_probe.write_text("unexpected\n", encoding="utf-8")
        source_write_succeeded = True
        source_probe.unlink(missing_ok=True)
    except OSError as error:
        source_write_error = errno.errorcode.get(error.errno or 0, type(error).__name__)
    add_probe(
        probes,
        "source_checkout_read_only",
        not source_write_succeeded,
        {"error_code": source_write_error},
    )

    root_probe = Path("/.aeg-runtime-canary-root-write-probe")
    root_write_error = "NONE"
    root_write_succeeded = False
    try:
        root_probe.write_text("unexpected\n", encoding="utf-8")
        root_write_succeeded = True
        root_probe.unlink(missing_ok=True)
    except OSError as error:
        root_write_error = errno.errorcode.get(error.errno or 0, type(error).__name__)
    add_probe(probes, "container_root_read_only", not root_write_succeeded, {"error_code": root_write_error})

    status = read_status_fields()
    kernel_boundary = (
        status.get("CapEff") == "0000000000000000"
        and status.get("NoNewPrivs") == "1"
        and status.get("Seccomp") == "2"
        and os.geteuid() != 0
    )
    add_probe(
        probes,
        "non_root_no_capabilities_no_new_privileges_seccomp",
        kernel_boundary,
        {"effective_uid": os.geteuid(), **status},
    )

    points = mount_points()
    suspicious_prefixes = ("/home/runner", "/github", "/__w", "/Users")
    suspicious_mounts = [point for point in points if point.startswith(suspicious_prefixes)]
    explicit_mounts_present = all(path in points for path in ("/control", "/source", "/work"))
    add_probe(
        probes,
        "no_unrelated_host_directory_mounts",
        explicit_mounts_present and not suspicious_mounts,
        {
            "explicit_mounts_present": explicit_mounts_present,
            "mount_count": len(points),
            "suspicious_mounts": suspicious_mounts,
        },
    )

    network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    network_socket.settimeout(3)
    try:
        network_result = network_socket.connect_ex(("1.1.1.1", 443))
    finally:
        network_socket.close()
    add_probe(
        probes,
        "test_network_negative_probe",
        network_result != 0,
        {"connect_ex": network_result, "target": "PUBLIC_TEST_IP_HTTPS"},
    )

    revision = git("rev-parse", "HEAD")
    source_revision_matches = revision.returncode == 0 and revision.stdout.strip() == os.environ["SOURCE_REVISION"]
    add_probe(
        probes,
        "public_source_revision_pinned",
        source_revision_matches,
        {"observed_revision": revision.stdout.strip() if revision.returncode == 0 else "UNAVAILABLE"},
    )

    original = git("cat-file", "-e", f"{ORIGINAL_NON_MAINLINE_COMMIT}^{{commit}}")
    add_probe(
        probes,
        "original_non_mainline_commit_not_acquired",
        original.returncode != 0,
        {"object_present": original.returncode == 0},
    )

    return probes, {
        "mount_points": points,
        "source_revision": revision.stdout.strip() if revision.returncode == 0 else "UNAVAILABLE",
    }


def write_result(result: dict[str, Any]) -> None:
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)


def main() -> int:
    started_at = utc_now()
    started = time.monotonic()
    Path(os.environ["HOME"]).mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "BLOCKED",
        "started_at": started_at,
        "source": {
            "repository": os.environ["SOURCE_REPOSITORY"],
            "ref": os.environ["SOURCE_REF"],
            "revision": os.environ["SOURCE_REVISION"],
            "control_revision": os.environ["CONTROL_REVISION"],
        },
        "runtime": {
            "canary_run_id": os.environ["CANARY_RUN_ID"],
            "runner_architecture": os.environ["RUNNER_ARCHITECTURE"],
            "machine": os.uname().machine,
            "python": sys.version.split()[0],
        },
        "boundary_probes": [],
        "boundary_context": {},
        "replay": {"attempted": False, "exit_code": None, "report": None},
    }
    exit_code = 2
    try:
        probes, context = run_boundary_probes()
        result["boundary_probes"] = probes
        result["boundary_context"] = context
        boundaries_passed = all(probe["passed"] for probe in probes)
        result["boundaries_passed"] = boundaries_passed
        if boundaries_passed:
            replay = subprocess.run(
                [sys.executable, str(REPLAY), "--json"],
                cwd="/source",
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
            )
            result["replay"]["attempted"] = True
            result["replay"]["exit_code"] = replay.returncode
            result["replay"]["stderr_present"] = bool(replay.stderr)
            try:
                replay_report = json.loads(replay.stdout)
            except json.JSONDecodeError:
                replay_report = {"status": "BLOCKED", "reason_codes": ["INVALID_REPLAY_JSON"]}
            result["replay"]["report"] = replay_report
            replay_status = replay_report.get("status")
            if replay.returncode == 0 and replay_status == "PASS":
                result["status"] = "PASS"
                exit_code = 0
            elif replay_status == "BLOCKED" or replay.returncode == 2:
                result["status"] = "BLOCKED"
                exit_code = 2
            else:
                result["status"] = "FAIL"
                exit_code = 1
        else:
            result["status"] = "FAIL"
            result["reason_codes"] = ["BOUNDARY_PROBE_FAILED"]
            exit_code = 1
    except subprocess.TimeoutExpired:
        result["status"] = "BLOCKED"
        result["reason_codes"] = ["REPLAY_TIMEOUT"]
        exit_code = 2
    except Exception as error:
        result["status"] = "BLOCKED"
        result["reason_codes"] = [f"CANARY_EXCEPTION_{type(error).__name__.upper()}"]
        exit_code = 2
    finally:
        result["completed_at"] = utc_now()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_result(result)
        print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
