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
from typing import Any, Callable


OUTPUT = Path("/work/canary-result.json")
CONTAINER_POLICY = Path("/work/container-policy.json")
REPLAY = Path("/source/examples/evidence-path-confinement/replay.py")
ORIGINAL_NON_MAINLINE_COMMIT = "4f1d26e80a4fba7460cfb2523905fb08619bd08d"
EXPECTED_REPLAY_CASES = 13
EXPECTED_ENVIRONMENT_KEYS = {
    "CANARY_RUN_ID",
    "CONTROL_REVISION",
    "HOME",
    "PATH",
    "PYTHONCOERCECLOCALE",
    "PYTHONDONTWRITEBYTECODE",
    "RUNNER_ARCHITECTURE",
    "SENTINEL_PATH",
    "SOURCE_REF",
    "SOURCE_REPOSITORY",
    "SOURCE_REVISION",
}
PROBE_NAMES = (
    "container_policy_attested",
    "sanitized_environment",
    "credential_environment_absent",
    "credential_paths_inaccessible",
    "checkout_credential_config_absent",
    "docker_socket_inaccessible",
    "host_home_and_workspace_inaccessible",
    "outside_synthetic_sentinel_inaccessible",
    "work_directory_read_write",
    "source_checkout_read_only",
    "container_root_read_only",
    "non_root_no_capabilities_no_new_privileges_seccomp",
    "no_unrelated_host_directory_mounts",
    "test_network_isolated",
    "timeout_termination_and_reaping",
    "public_source_revision_pinned",
    "original_non_mainline_commit_not_acquired",
)
PATH_ABSENT = "ABSENT"
PATH_PRESENT = "PRESENT"
PATH_ACCESS_DENIED = "ACCESS_DENIED"
PATH_PROBE_ERROR = "PROBE_ERROR"
PROBE_PASS = "PASS"
PROBE_FAIL = "FAIL"
PROBE_UNKNOWN = "UNKNOWN"
PROBE_NOT_RUN = "NOT_RUN"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def errno_name(error: OSError) -> str:
    return errno.errorcode.get(error.errno or 0, type(error).__name__)


def observe_path(
    path: Path,
    stat_function: Callable[[Path], Any] = os.lstat,
) -> dict[str, Any]:
    """Observe existence without reading content or collapsing access errors."""
    try:
        stat_function(path)
    except (FileNotFoundError, NotADirectoryError) as error:
        return {"path": str(path), "state": PATH_ABSENT, "errno": errno_name(error)}
    except PermissionError as error:
        if error.errno in (errno.EACCES, errno.EPERM):
            return {
                "path": str(path),
                "state": PATH_ACCESS_DENIED,
                "errno": errno_name(error),
                "presence_known": False,
            }
        return {"path": str(path), "state": PATH_PROBE_ERROR, "errno": errno_name(error)}
    except OSError as error:
        return {"path": str(path), "state": PATH_PROBE_ERROR, "errno": errno_name(error)}
    return {"path": str(path), "state": PATH_PRESENT, "errno": None, "presence_known": True}


def requirement_absent(observations: list[dict[str, Any]]) -> bool:
    """A requirement for absence accepts only an observed ABSENT state."""
    return bool(observations) and all(item["state"] == PATH_ABSENT for item in observations)


def requirement_inaccessible(
    observations: list[dict[str, Any]], policy_attested: bool
) -> bool:
    """Access denial can support inaccessibility, never a claim of absence."""
    allowed = {PATH_ABSENT, PATH_ACCESS_DENIED}
    return policy_attested and bool(observations) and all(
        item["state"] in allowed for item in observations
    )


def read_observation(path: Path) -> dict[str, Any]:
    """Try a one-byte synthetic read without retaining or printing content."""
    try:
        with path.open("rb") as stream:
            stream.read(1)
    except (FileNotFoundError, NotADirectoryError) as error:
        return {"path": str(path), "state": PATH_ABSENT, "errno": errno_name(error)}
    except PermissionError as error:
        if error.errno in (errno.EACCES, errno.EPERM):
            return {
                "path": str(path),
                "state": PATH_ACCESS_DENIED,
                "errno": errno_name(error),
                "presence_known": False,
            }
        return {"path": str(path), "state": PATH_PROBE_ERROR, "errno": errno_name(error)}
    except OSError as error:
        return {"path": str(path), "state": PATH_PROBE_ERROR, "errno": errno_name(error)}
    return {"path": str(path), "state": PATH_PRESENT, "errno": None, "read_succeeded": True}


def classify_write_error(error: OSError) -> str:
    if error.errno in (errno.EACCES, errno.EPERM):
        return PATH_ACCESS_DENIED
    if error.errno == errno.EROFS:
        return "READ_ONLY"
    return PATH_PROBE_ERROR


def forbidden_write_observation(path: Path) -> dict[str, Any]:
    try:
        path.write_text("synthetic-canary-write\n", encoding="utf-8")
    except OSError as error:
        return {
            "path": str(path),
            "state": classify_write_error(error),
            "errno": errno_name(error),
        }
    try:
        path.unlink()
    except OSError as error:
        return {
            "path": str(path),
            "state": PATH_PROBE_ERROR,
            "errno": errno_name(error),
            "write_succeeded": True,
            "cleanup_succeeded": False,
        }
    return {
        "path": str(path),
        "state": "WRITE_SUCCEEDED",
        "errno": None,
        "write_succeeded": True,
        "cleanup_succeeded": True,
    }


def work_round_trip(work_root: Path) -> dict[str, Any]:
    path = work_root / "read-write-probe.txt"
    try:
        path.write_text("bounded\n", encoding="utf-8")
        matched = path.read_text(encoding="utf-8") == "bounded\n"
        path.unlink()
    except OSError as error:
        return {"state": PATH_PROBE_ERROR, "errno": errno_name(error), "round_trip": False}
    return {
        "state": "READ_WRITE_SUCCEEDED" if matched else "CONTENT_MISMATCH",
        "errno": None,
        "round_trip": matched,
    }


def initial_probes() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "required": True,
            "status": PROBE_NOT_RUN,
            "passed": False,
            "observation": None,
        }
        for name in PROBE_NAMES
    ]


def record_probe(
    probes: list[dict[str, Any]], name: str, status: str, observation: Any
) -> None:
    if status not in {PROBE_PASS, PROBE_FAIL, PROBE_UNKNOWN, PROBE_NOT_RUN}:
        raise ValueError(f"unsupported probe status for {name}")
    probe = next(item for item in probes if item["name"] == name)
    probe.update({"status": status, "passed": status == PROBE_PASS, "observation": observation})


def all_required_probes_passed(probes: list[dict[str, Any]]) -> bool:
    required = [probe for probe in probes if probe["required"]]
    return bool(required) and all(probe["status"] == PROBE_PASS for probe in required)


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


def load_container_policy() -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        policy = json.loads(CONTAINER_POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        observation = {
            "state": PATH_PROBE_ERROR,
            "error_type": type(error).__name__,
        }
        if isinstance(error, OSError):
            observation["errno"] = errno_name(error)
        return {}, observation
    checks = policy.get("checks")
    if not isinstance(checks, dict) or policy.get("passed") is not True:
        return {}, {"state": "POLICY_FAILED", "checks": checks}
    return checks, None


def network_observation() -> dict[str, Any]:
    acceptable = {
        errno.EACCES,
        errno.EPERM,
        errno.ENETDOWN,
        errno.ENETUNREACH,
        errno.EHOSTUNREACH,
    }
    network_socket: socket.socket | None = None
    try:
        network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        network_socket.settimeout(3)
        result = network_socket.connect_ex(("1.1.1.1", 443))
    except OSError as error:
        return {
            "state": PATH_PROBE_ERROR,
            "errno": errno_name(error),
            "target": "PUBLIC_TEST_IP_HTTPS",
        }
    finally:
        if network_socket is not None:
            network_socket.close()
    if result == 0:
        state = "CONNECTION_SUCCEEDED"
    elif result in acceptable:
        state = "NETWORK_UNREACHABLE"
    else:
        state = PATH_PROBE_ERROR
    return {
        "state": state,
        "connect_ex": result,
        "errno": errno.errorcode.get(result, "NONE"),
        "target": "PUBLIC_TEST_IP_HTTPS",
    }


def timeout_termination_observation(timeout_seconds: float = 0.2) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    timed_out = False
    forced_kill = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            forced_kill = True
            process.kill()
            process.wait(timeout=2)
    reaped = process.poll() is not None
    try:
        os.waitpid(process.pid, os.WNOHANG)
    except ChildProcessError:
        wait_state = "REAPED"
    else:
        wait_state = "UNEXPECTED_WAITABLE_STATE"
        reaped = False
    return {
        "state": "TIMED_OUT_AND_REAPED" if timed_out and reaped else "PROBE_FAILED",
        "timed_out": timed_out,
        "reaped": reaped,
        "forced_kill": forced_kill,
        "return_code": process.returncode,
        "wait_state": wait_state,
        "timeout_seconds": timeout_seconds,
    }


def probe_status_from_paths(
    observations: list[dict[str, Any]], policy_attested: bool
) -> str:
    states = {item["state"] for item in observations}
    if PATH_PRESENT in states:
        return PROBE_FAIL
    if PATH_PROBE_ERROR in states:
        return PROBE_UNKNOWN
    return PROBE_PASS if requirement_inaccessible(observations, policy_attested) else PROBE_UNKNOWN


def run_boundary_probes(probes: list[dict[str, Any]]) -> dict[str, Any]:
    policy_checks, policy_error = load_container_policy()
    policy_attested = policy_error is None
    record_probe(
        probes,
        "container_policy_attested",
        PROBE_PASS if policy_attested else PROBE_UNKNOWN,
        {"checks": policy_checks, "error": policy_error},
    )

    environment_keys = set(os.environ)
    record_probe(
        probes,
        "sanitized_environment",
        PROBE_PASS if environment_keys == EXPECTED_ENVIRONMENT_KEYS else PROBE_FAIL,
        {"keys": sorted(environment_keys)},
    )

    sensitive_fragments = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "ACTIONS_", "GITHUB_")
    sensitive_keys = sorted(
        key for key in environment_keys if any(fragment in key.upper() for fragment in sensitive_fragments)
    )
    record_probe(
        probes,
        "credential_environment_absent",
        PROBE_PASS if not sensitive_keys else PROBE_FAIL,
        {"keys": sensitive_keys},
    )

    credential_paths = [
        Path(os.environ["HOME"]) / ".git-credentials",
        Path(os.environ["HOME"]) / ".config/gh/hosts.yml",
        Path("/root/.git-credentials"),
        Path("/root/.config/gh/hosts.yml"),
        Path("/home/runner/.git-credentials"),
        Path("/github/home/.git-credentials"),
    ]
    credential_observations = [observe_path(path) for path in credential_paths]
    credential_policy = policy_attested and all(
        policy_checks.get(name) is True
        for name in ("base_image_digest_attested", "entry_environment_cleared", "mounts_exact")
    )
    credential_status = probe_status_from_paths(credential_observations, credential_policy)
    record_probe(
        probes,
        "credential_paths_inaccessible",
        credential_status,
        {
            "paths": credential_observations,
            "access_conclusion": (
                "NO_CREDENTIAL_ACCESS_OBSERVED" if credential_status == PROBE_PASS else "NOT_ESTABLISHED"
            ),
            "presence_conclusion": (
                "UNKNOWN_FOR_ACCESS_DENIED_PATHS"
                if any(item["state"] == PATH_ACCESS_DENIED for item in credential_observations)
                else "ALL_ABSENT" if requirement_absent(credential_observations) else "NOT_ESTABLISHED"
            ),
            "supporting_policy_checks": {
                name: policy_checks.get(name)
                for name in (
                    "base_image_digest_attested",
                    "entry_environment_cleared",
                    "mounts_exact",
                )
            },
        },
    )

    try:
        source_config = Path("/source/.git/config").read_text(encoding="utf-8").lower()
    except OSError as error:
        record_probe(
            probes,
            "checkout_credential_config_absent",
            PROBE_UNKNOWN,
            {"state": PATH_PROBE_ERROR, "errno": errno_name(error)},
        )
    else:
        forbidden_config_markers = [
            marker
            for marker in ("extraheader", "credential.helper", "authorization:", "token")
            if marker in source_config
        ]
        record_probe(
            probes,
            "checkout_credential_config_absent",
            PROBE_PASS if not forbidden_config_markers else PROBE_FAIL,
            {"forbidden_markers": forbidden_config_markers},
        )

    socket_observations = [
        observe_path(Path("/var/run/docker.sock")),
        observe_path(Path("/run/docker.sock")),
    ]
    socket_policy = policy_attested and all(
        policy_checks.get(name) is True for name in ("mounts_exact", "no_device_passthrough")
    )
    record_probe(
        probes,
        "docker_socket_inaccessible",
        probe_status_from_paths(socket_observations, socket_policy),
        {
            "paths": socket_observations,
            "presence_claim": "ABSENT" if requirement_absent(socket_observations) else "NOT_CLAIMED",
            "supporting_policy_checks": {
                name: policy_checks.get(name) for name in ("mounts_exact", "no_device_passthrough")
            },
        },
    )

    host_observations = [
        observe_path(path)
        for path in (Path("/home/runner"), Path("/github/home"), Path("/__w"), Path("/Users"))
    ]
    record_probe(
        probes,
        "host_home_and_workspace_inaccessible",
        probe_status_from_paths(
            host_observations,
            policy_attested and policy_checks.get("mounts_exact") is True,
        ),
        {
            "paths": host_observations,
            "presence_claim": "ABSENT" if requirement_absent(host_observations) else "NOT_CLAIMED",
            "supporting_policy_check": {"mounts_exact": policy_checks.get("mounts_exact")},
        },
    )

    sentinel_observation = read_observation(Path(os.environ["SENTINEL_PATH"]))
    sentinel_state = sentinel_observation["state"]
    record_probe(
        probes,
        "outside_synthetic_sentinel_inaccessible",
        (
            PROBE_PASS
            if sentinel_state in {PATH_ABSENT, PATH_ACCESS_DENIED}
            and policy_attested
            and policy_checks.get("mounts_exact") is True
            else PROBE_FAIL if sentinel_state == PATH_PRESENT else PROBE_UNKNOWN
        ),
        {
            **sentinel_observation,
            "host_created_synthetic_sentinel": True,
            "supporting_policy_check": {"mounts_exact": policy_checks.get("mounts_exact")},
        },
    )

    work_observation = work_round_trip(Path("/work"))
    record_probe(
        probes,
        "work_directory_read_write",
        PROBE_PASS if work_observation["round_trip"] else PROBE_UNKNOWN,
        work_observation,
    )

    source_write = forbidden_write_observation(Path("/source/.aeg-runtime-canary-write-probe"))
    record_probe(
        probes,
        "source_checkout_read_only",
        PROBE_PASS if source_write["state"] in {"READ_ONLY", PATH_ACCESS_DENIED} else (
            PROBE_FAIL if source_write["state"] == "WRITE_SUCCEEDED" else PROBE_UNKNOWN
        ),
        source_write,
    )

    root_write = forbidden_write_observation(Path("/.aeg-runtime-canary-root-write-probe"))
    record_probe(
        probes,
        "container_root_read_only",
        PROBE_PASS if root_write["state"] in {"READ_ONLY", PATH_ACCESS_DENIED} else (
            PROBE_FAIL if root_write["state"] == "WRITE_SUCCEEDED" else PROBE_UNKNOWN
        ),
        root_write,
    )

    status = read_status_fields()
    kernel_boundary = (
        status.get("CapEff") == "0000000000000000"
        and status.get("NoNewPrivs") == "1"
        and status.get("Seccomp") == "2"
        and os.geteuid() != 0
    )
    record_probe(
        probes,
        "non_root_no_capabilities_no_new_privileges_seccomp",
        PROBE_PASS if kernel_boundary else PROBE_FAIL,
        {"effective_uid": os.geteuid(), **status},
    )

    points = mount_points()
    suspicious_prefixes = ("/home/runner", "/github", "/__w", "/Users")
    suspicious_mounts = [point for point in points if point.startswith(suspicious_prefixes)]
    explicit_mounts_present = all(path in points for path in ("/control", "/source", "/work"))
    mount_boundary = (
        explicit_mounts_present
        and not suspicious_mounts
        and policy_attested
        and policy_checks.get("mounts_exact") is True
    )
    record_probe(
        probes,
        "no_unrelated_host_directory_mounts",
        PROBE_PASS if mount_boundary else PROBE_FAIL,
        {
            "explicit_mounts_present": explicit_mounts_present,
            "mount_count": len(points),
            "suspicious_mounts": suspicious_mounts,
            "supporting_policy_check": {"mounts_exact": policy_checks.get("mounts_exact")},
        },
    )

    network = network_observation()
    network_isolated = (
        network["state"] == "NETWORK_UNREACHABLE"
        and policy_attested
        and policy_checks.get("network_disabled") is True
    )
    record_probe(
        probes,
        "test_network_isolated",
        PROBE_PASS if network_isolated else (
            PROBE_FAIL if network["state"] == "CONNECTION_SUCCEEDED" else PROBE_UNKNOWN
        ),
        {
            **network,
            "supporting_policy_check": {"network_disabled": policy_checks.get("network_disabled")},
            "connection_failure_alone_is_sufficient": False,
        },
    )

    try:
        timeout_observation = timeout_termination_observation()
    except (OSError, subprocess.SubprocessError) as error:
        timeout_observation = {
            "state": PATH_PROBE_ERROR,
            "error_type": type(error).__name__,
        }
        if isinstance(error, OSError):
            timeout_observation["errno"] = errno_name(error)
        timeout_status = PROBE_UNKNOWN
    else:
        timeout_status = (
            PROBE_PASS if timeout_observation["state"] == "TIMED_OUT_AND_REAPED" else PROBE_FAIL
        )
    record_probe(
        probes,
        "timeout_termination_and_reaping",
        timeout_status,
        timeout_observation,
    )

    revision = git("rev-parse", "HEAD")
    source_revision_matches = (
        revision.returncode == 0 and revision.stdout.strip() == os.environ["SOURCE_REVISION"]
    )
    record_probe(
        probes,
        "public_source_revision_pinned",
        PROBE_PASS if source_revision_matches else PROBE_FAIL,
        {
            "observed_revision": revision.stdout.strip() if revision.returncode == 0 else "UNAVAILABLE",
            "git_exit_code": revision.returncode,
        },
    )

    original = git("cat-file", "-e", f"{ORIGINAL_NON_MAINLINE_COMMIT}^{{commit}}")
    record_probe(
        probes,
        "original_non_mainline_commit_not_acquired",
        PROBE_PASS if original.returncode != 0 else PROBE_FAIL,
        {"object_present": original.returncode == 0, "git_exit_code": original.returncode},
    )

    return {
        "mount_points": points,
        "source_revision": revision.stdout.strip() if revision.returncode == 0 else "UNAVAILABLE",
        "credential_presence_claim": "NOT_MADE_FOR_ACCESS_DENIED_PATHS",
    }


def assess_replay(report: Any, exit_code: int) -> tuple[bool, dict[str, Any]]:
    if not isinstance(report, dict):
        return False, {"contract_errors": ["REPORT_NOT_OBJECT"]}
    summary = report.get("summary")
    cases = report.get("observed_replay", {}).get("cases")
    runtime_sources = report.get("source_identity", {}).get("runtime_observed")
    errors: list[str] = []
    if exit_code != 0:
        errors.append("NONZERO_EXIT")
    if report.get("status") != "PASS":
        errors.append("STATUS_NOT_PASS")
    if not isinstance(summary, dict):
        errors.append("SUMMARY_MISSING")
        summary = {}
    if not isinstance(cases, list) or len(cases) != EXPECTED_REPLAY_CASES:
        errors.append("CASE_COUNT_NOT_13")
        cases = [] if not isinstance(cases, list) else cases
    case_ids = [item.get("id") for item in cases if isinstance(item, dict)]
    if len(set(case_ids)) != EXPECTED_REPLAY_CASES:
        errors.append("CASE_IDS_NOT_13_UNIQUE")
    expected_summary = {
        "essential_case_count": EXPECTED_REPLAY_CASES,
        "executed_case_count": EXPECTED_REPLAY_CASES,
        "matching_case_count": EXPECTED_REPLAY_CASES,
        "all_essential_checks_executed": True,
        "baseline_escape_defect_observed": True,
        "fixed_escape_rejection_observed": True,
        "legitimate_cases_preserved": True,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"SUMMARY_{key.upper()}_MISMATCH")
    if set(runtime_sources or []) != {"baseline", "fixed"}:
        errors.append("RUNTIME_SOURCE_IDENTITY_MISMATCH")
    return not errors, {
        "contract_errors": errors,
        "essential_case_count": summary.get("essential_case_count"),
        "executed_case_count": summary.get("executed_case_count"),
        "matching_case_count": summary.get("matching_case_count"),
        "baseline_escape_defect_observed": summary.get("baseline_escape_defect_observed"),
        "fixed_escape_rejection_observed": summary.get("fixed_escape_rejection_observed"),
        "legitimate_cases_preserved": summary.get("legitimate_cases_preserved"),
        "runtime_observed_sources": runtime_sources,
    }


def write_result(result: dict[str, Any]) -> None:
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)


def main() -> int:
    started_at = utc_now()
    started = time.monotonic()
    probes = initial_probes()
    result: dict[str, Any] = {
        "schema_version": 2,
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
        "boundary_probes": probes,
        "boundary_context": {},
        "boundaries_passed": False,
        "replay": {"attempted": False, "exit_code": None, "report": None, "contract": None},
    }
    exit_code = 2
    try:
        Path(os.environ["HOME"]).mkdir(parents=True, exist_ok=True)
        result["boundary_context"] = run_boundary_probes(probes)
        result["boundaries_passed"] = all_required_probes_passed(probes)
        if result["boundaries_passed"]:
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
                replay_report: Any = json.loads(replay.stdout)
            except json.JSONDecodeError:
                replay_report = {"status": "BLOCKED", "reason_codes": ["INVALID_REPLAY_JSON"]}
            result["replay"]["report"] = replay_report
            replay_passed, replay_contract = assess_replay(replay_report, replay.returncode)
            result["replay"]["contract"] = replay_contract
            if replay_passed:
                result["status"] = "PASS"
                exit_code = 0
            elif isinstance(replay_report, dict) and (
                replay_report.get("status") == "BLOCKED" or replay.returncode == 2
            ):
                result["status"] = "BLOCKED"
                result["reason_codes"] = ["REPLAY_BLOCKED"]
                exit_code = 2
            else:
                result["status"] = "FAIL"
                result["reason_codes"] = ["REPLAY_CONTRACT_FAILED"]
                exit_code = 1
        elif any(probe["status"] == PROBE_FAIL for probe in probes if probe["required"]):
            result["status"] = "FAIL"
            result["reason_codes"] = ["BOUNDARY_PROBE_FAILED"]
            exit_code = 1
        else:
            result["status"] = "BLOCKED"
            result["reason_codes"] = ["BOUNDARY_PROBE_UNKNOWN_OR_NOT_RUN"]
            exit_code = 2
    except subprocess.TimeoutExpired:
        result["status"] = "BLOCKED"
        result["reason_codes"] = ["REPLAY_TIMEOUT"]
        exit_code = 2
    except Exception as error:
        result["status"] = "BLOCKED"
        result["reason_codes"] = [f"CANARY_EXCEPTION_{type(error).__name__.upper()}"]
        result["exception"] = {"type": type(error).__name__}
        if isinstance(error, OSError):
            result["exception"]["errno"] = errno_name(error)
        exit_code = 2
    finally:
        result["completed_at"] = utc_now()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_result(result)
        print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
