#!/usr/bin/env python3
"""Replay the evidence-path symlink confinement regression on pinned sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


CASE_ID = "PUBLIC_REPLAY_01"
CASE_VERSION = "1.0.0"
REPOSITORY_URL = "https://github.com/yao23/agent-experience-graph"
VALIDATOR_PATH = "scripts/validate_verified_experiences.py"
TEST_PATH = "scripts/test_validate_verified_experiences.py"

BASELINE = {
    "commit": "f985424fed493c52f9686bdd3feff33f28b2d400",
    "tree": "e68fb35e90f8f2cee820f5cba7ca905c22ab6322",
    "parent": None,
    "sources": {
        VALIDATOR_PATH: {
            "git_blob": "7f20fa6177b442225d6314e33787f57c0b07e18b",
            "sha256": "f18709b3af1b0cfe3ff1e4c240b71c907e4a29bb0b95d585de4d2f7f29bb7b4e",
        },
        TEST_PATH: {
            "git_blob": "4ace98604a5446e268768ad617e3ddb36c4a9b21",
            "sha256": "f59cfa374a1f9f1cb5148f5300d5057bd1e3c726553405ac7eb91d3a51cd4e7a",
        },
    },
}

FIXED = {
    "commit": "ee6ed853c1c8e93541d0b38ac5e46b4bdd9146c1",
    "tree": "c54f10fb82e5ea293286250e666214d37b7819d4",
    "parent": BASELINE["commit"],
    "sources": {
        VALIDATOR_PATH: {
            "git_blob": "a64feaa6912379fba25ba396bb3113c88453d70b",
            "sha256": "7a26f365bf28bc08a9007d38b047ca7236059116aef898bffd61c9e117419dc1",
        },
        TEST_PATH: {
            "git_blob": "10c37546228a8641909618a6d8eacd7b8dce479f",
            "sha256": "f67b2806711b37892f7fb6937b94ebaa3583301e373a0bfdc1f5512e36082c82",
        },
    },
}

ORIGINAL_TARGET = {
    "commit": "4f1d26e80a4fba7460cfb2523905fb08619bd08d",
    "recorded_tree": "c54f10fb82e5ea293286250e666214d37b7819d4",
    "recorded_parent": "f985424fed493c52f9686bdd3feff33f28b2d400",
    "recorded_sources": {
        VALIDATOR_PATH: {
            "git_blob": "a64feaa6912379fba25ba396bb3113c88453d70b",
            "sha256": "7a26f365bf28bc08a9007d38b047ca7236059116aef898bffd61c9e117419dc1",
        },
        TEST_PATH: {
            "git_blob": "10c37546228a8641909618a6d8eacd7b8dce479f",
            "sha256": "f67b2806711b37892f7fb6937b94ebaa3583301e373a0bfdc1f5512e36082c82",
        },
    },
    "role": "HISTORICAL_PROVENANCE_ONLY",
    "runtime_required": False,
    "verified_this_run": False,
    "loaded_this_run": False,
    "executed_this_run": False,
    "automatic_acquisition": False,
}

EXPECTED_CASES = (
    {
        "id": "ordinary_in_root_file",
        "kind": "legitimate",
        "display_path": "evidence.json",
        "baseline": "ACCEPTED",
        "fixed": "ACCEPTED",
    },
    {
        "id": "in_root_symlink",
        "kind": "legitimate",
        "display_path": "inside-link.json",
        "baseline": "ACCEPTED",
        "fixed": "ACCEPTED",
    },
    {
        "id": "multi_hop_in_root_symlink",
        "kind": "legitimate",
        "display_path": "inside-hop-1.json",
        "baseline": "ACCEPTED",
        "fixed": "ACCEPTED",
    },
    {
        "id": "direct_outside_symlink",
        "kind": "escape",
        "display_path": "outside-link.json",
        "baseline": "ACCEPTED",
        "fixed": "REJECTED",
    },
    {
        "id": "multi_hop_outside_symlink",
        "kind": "escape",
        "display_path": "outside-hop-1.json",
        "baseline": "ACCEPTED",
        "fixed": "REJECTED",
    },
    {
        "id": "symlinked_directory_escape",
        "kind": "escape",
        "display_path": "outside-directory-link/nested.json",
        "baseline": "ACCEPTED",
        "fixed": "REJECTED",
    },
    {
        "id": "prefix_collision_escape",
        "kind": "escape",
        "display_path": "prefix-collision.json",
        "baseline": "ACCEPTED",
        "fixed": "REJECTED",
    },
    {
        "id": "dangling_symlink",
        "kind": "invalid",
        "display_path": "dangling-link.json",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
    {
        "id": "symlink_loop",
        "kind": "invalid",
        "display_path": "loop-a.json",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
    {
        "id": "missing_path",
        "kind": "invalid",
        "display_path": "missing.json",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
    {
        "id": "absolute_path",
        "kind": "invalid",
        "display_path": "ABSOLUTE_FIXTURE_PATH",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
    {
        "id": "lexical_parent_traversal",
        "kind": "invalid",
        "display_path": "../outside/evidence.json",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
    {
        "id": "directory_instead_of_file",
        "kind": "invalid",
        "display_path": "directory",
        "baseline": "REJECTED",
        "fixed": "REJECTED",
    },
)


class ReplayBlocked(RuntimeError):
    """Raised when required source or platform capabilities are unavailable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.public_message = message


def _git(repo_root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ReplayBlocked("GIT_UNAVAILABLE", "git could not be executed") from error
    if completed.returncode != 0:
        raise ReplayBlocked(
            "PINNED_HISTORY_UNAVAILABLE",
            "the repository does not contain all pinned source history",
        )
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _source_identity(repo_root: Path, label: str, expected: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    commit = expected["commit"]
    observed_tree = _git(repo_root, "rev-parse", f"{commit}^{{tree}}")
    if observed_tree != expected["tree"]:
        raise ReplayBlocked("PROVENANCE_MISMATCH", f"{label} tree does not match the committed case identity")

    observed_parent = None
    if expected["parent"] is not None:
        observed_parent = _git(repo_root, "rev-parse", f"{commit}^")
        if observed_parent != expected["parent"]:
            raise ReplayBlocked("PROVENANCE_MISMATCH", f"{label} parent does not match the committed case identity")

    source_bytes: dict[str, bytes] = {}
    observed_sources: dict[str, Any] = {}
    for path, source_expected in expected["sources"].items():
        content = _git(repo_root, "show", f"{commit}:{path}", binary=True)
        assert isinstance(content, bytes)
        digest = hashlib.sha256(content).hexdigest()
        blob = _git(repo_root, "rev-parse", f"{commit}:{path}")
        if digest != source_expected["sha256"] or blob != source_expected["git_blob"]:
            raise ReplayBlocked("PROVENANCE_MISMATCH", f"{label} source hash does not match for {path}")
        source_bytes[path] = content
        observed_sources[path] = {"git_blob": blob, "sha256": digest}

    return (
        {
            "commit": commit,
            "tree": observed_tree,
            "parent": observed_parent,
            "sources": observed_sources,
            "identity_verified": True,
        },
        source_bytes,
    )


def verify_source_history(repo_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, bytes]]]:
    if shutil.which("git") is None:
        raise ReplayBlocked("GIT_UNAVAILABLE", "git is required to read the pinned source revisions")
    try:
        inside = _git(repo_root, "rev-parse", "--is-inside-work-tree")
    except ReplayBlocked as error:
        raise ReplayBlocked("PINNED_HISTORY_UNAVAILABLE", "the selected directory is not a usable Git worktree") from error
    if inside != "true":
        raise ReplayBlocked("PINNED_HISTORY_UNAVAILABLE", "the selected directory is not a usable Git worktree")

    observed: dict[str, Any] = {}
    sources: dict[str, dict[str, bytes]] = {}
    for label, expected in (
        ("baseline", BASELINE),
        ("fixed", FIXED),
    ):
        identity, source_bytes = _source_identity(repo_root, label, expected)
        observed[label] = identity
        sources[label] = source_bytes
    return observed, sources


def probe_symlink_support(temporary_root: Path) -> tuple[bool, str | None]:
    probe_root = temporary_root / "symlink-probe"
    probe_root.mkdir()
    target = probe_root / "target"
    target.write_text("inert\n", encoding="utf-8")
    link = probe_root / "link"
    try:
        link.symlink_to(target)
        if not link.is_file():
            return False, "created symlinks cannot be followed as files"
    except (NotImplementedError, OSError):
        return False, "symlink creation is unavailable on this platform"
    return True, None


def _load_validator(source: bytes, export_root: Path, label: str) -> types.ModuleType:
    script_path = export_root / "scripts" / "validate_verified_experiences.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_bytes(source)
    module = types.ModuleType(f"aeg_replay_validator_{label}")
    module.__file__ = str(script_path)
    module.__name__ = f"aeg_replay_validator_{label}"
    try:
        code = compile(source, str(script_path), "exec")
        exec(code, module.__dict__)
    except Exception as error:
        raise ReplayBlocked("VALIDATOR_IMPORT_FAILED", f"the {label} production validator could not be loaded") from error
    if not hasattr(module, "validate_repository_reference") or not hasattr(module, "ValidationError"):
        raise ReplayBlocked("VALIDATOR_INTERFACE_UNAVAILABLE", f"the {label} validator lacks the required production interface")
    return module


def _create_fixtures(temporary_root: Path) -> tuple[Path, dict[str, str]]:
    fixtures = temporary_root / "fixtures"
    repository = fixtures / "repository"
    outside = fixtures / "outside"
    prefix_collision = fixtures / "repository-collision"
    repository.mkdir(parents=True)
    outside.mkdir()
    prefix_collision.mkdir()

    ordinary = repository / "evidence.json"
    ordinary.write_text("{}\n", encoding="utf-8")
    (outside / "evidence.json").write_text("{}\n", encoding="utf-8")
    (outside / "nested.json").write_text("{}\n", encoding="utf-8")
    (prefix_collision / "evidence.json").write_text("{}\n", encoding="utf-8")
    (repository / "directory").mkdir()

    (repository / "inside-link.json").symlink_to("evidence.json")
    (repository / "inside-hop-2.json").symlink_to("evidence.json")
    (repository / "inside-hop-1.json").symlink_to("inside-hop-2.json")
    (repository / "outside-link.json").symlink_to(outside / "evidence.json")
    (repository / "outside-hop-2.json").symlink_to(outside / "evidence.json")
    (repository / "outside-hop-1.json").symlink_to("outside-hop-2.json")
    (repository / "outside-directory-link").symlink_to(outside, target_is_directory=True)
    (repository / "prefix-collision.json").symlink_to(prefix_collision / "evidence.json")
    (repository / "dangling-link.json").symlink_to("missing-target.json")
    (repository / "loop-a.json").symlink_to("loop-b.json")
    (repository / "loop-b.json").symlink_to("loop-a.json")

    inputs = {
        "ordinary_in_root_file": "evidence.json",
        "in_root_symlink": "inside-link.json",
        "multi_hop_in_root_symlink": "inside-hop-1.json",
        "direct_outside_symlink": "outside-link.json",
        "multi_hop_outside_symlink": "outside-hop-1.json",
        "symlinked_directory_escape": "outside-directory-link/nested.json",
        "prefix_collision_escape": "prefix-collision.json",
        "dangling_symlink": "dangling-link.json",
        "symlink_loop": "loop-a.json",
        "missing_path": "missing.json",
        "absolute_path": str(ordinary.resolve()),
        "lexical_parent_traversal": "../outside/evidence.json",
        "directory_instead_of_file": "directory",
    }
    return repository, inputs


def _observe(validator: types.ModuleType, value: str, repository_root: Path) -> dict[str, str]:
    try:
        validator.validate_repository_reference(value, "replay_fixture", repository_root)
    except validator.ValidationError:
        return {"decision": "REJECTED", "result_type": "ValidationError"}
    except Exception as error:
        return {"decision": "ERROR", "result_type": type(error).__name__}
    return {"decision": "ACCEPTED", "result_type": "none"}


def run_case_matrix(
    baseline_validator: types.ModuleType,
    fixed_validator: types.ModuleType,
    temporary_root: Path,
) -> list[dict[str, Any]]:
    repository_root, inputs = _create_fixtures(temporary_root)
    observations: list[dict[str, Any]] = []
    for expectation in EXPECTED_CASES:
        value = inputs[expectation["id"]]
        observations.append(
            {
                "id": expectation["id"],
                "kind": expectation["kind"],
                "display_path": expectation["display_path"],
                "baseline": _observe(baseline_validator, value, repository_root),
                "fixed": _observe(fixed_validator, value, repository_root),
            }
        )
    return observations


def _expected_case_projection() -> list[dict[str, str]]:
    return [dict(item) for item in EXPECTED_CASES]


def _empty_report() -> dict[str, Any]:
    return {
        "case_id": CASE_ID,
        "case_version": CASE_VERSION,
        "classifications": [
            "RETROSPECTIVE_REGRESSION_REPLAY",
            "FOUNDER_OWNED_REPOSITORY",
            "KNOWN_SOLUTION_AVAILABLE",
        ],
        "status": "BLOCKED",
        "reason_codes": [],
        "repository": REPOSITORY_URL,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.system() or "UNKNOWN",
        },
        "source_identity": {
            "runtime_required_expectations": {
                "baseline": BASELINE,
                "fixed": FIXED,
            },
            "historical_provenance_only": {
                "original_target": ORIGINAL_TARGET,
            },
            "runtime_observed": {},
        },
        "prerequisites": {
            "git_available": shutil.which("git") is not None,
            "pinned_history_available": False,
            "source_hashes_verified": False,
            "required_runtime_sources": ["baseline", "fixed"],
            "verified_runtime_sources": [],
            "symlinks_supported": False,
        },
        "coverage": {
            "kind": "FOCUSED_PRODUCTION_FUNCTION_REPLAY",
            "production_function": "validate_repository_reference",
            "full_registry_cli_validation": False,
        },
        "committed_expectations": {
            "cases": _expected_case_projection(),
            "success_definition": (
                "all essential cases execute against both pinned production validators; "
                "baseline escape cases are accepted, fixed escape cases are rejected, "
                "and legitimate in-root cases remain accepted"
            ),
        },
        "observed_replay": {"cases": []},
        "summary": {
            "essential_case_count": len(EXPECTED_CASES),
            "executed_case_count": 0,
            "matching_case_count": 0,
            "baseline_escape_defect_observed": False,
            "fixed_escape_rejection_observed": False,
            "legitimate_cases_preserved": False,
            "all_essential_checks_executed": False,
        },
        "temporary_artifacts_created": False,
        "temporary_artifacts_cleaned": True,
        "governance": {
            "capture_candidate": False,
            "registry_experience": False,
            "execution_authorized_by_case": False,
            "recommendation_eligible": False,
            "public_confidence_changed": False,
        },
        "limitations": [
            "The replay tests path validation, not general filesystem sandboxing.",
            "Concurrent malicious filesystem replacement between validation and later use is not covered.",
            "Results apply only to the pinned validator sources and the current replay platform.",
            "Other operating systems and filesystem implementations remain untested unless replayed there.",
        ],
    }


def build_report(repo_root: Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    report = _empty_report()

    try:
        identities, sources = verify_source_history(root)
    except ReplayBlocked as error:
        report["reason_codes"].append(error.code)
        report["message"] = error.public_message
        return report

    report["source_identity"]["runtime_observed"] = identities
    report["prerequisites"]["pinned_history_available"] = True
    report["prerequisites"]["source_hashes_verified"] = True
    report["prerequisites"]["verified_runtime_sources"] = ["baseline", "fixed"]

    temporary_path: Path | None = None
    observations: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="aeg-public-replay-01-") as temporary:
            temporary_path = Path(temporary)
            report["temporary_artifacts_created"] = True
            supported, reason = probe_symlink_support(temporary_path)
            report["prerequisites"]["symlinks_supported"] = supported
            if not supported:
                raise ReplayBlocked("UNSUPPORTED_PREREQUISITE", reason or "symlinks are unavailable")

            baseline_validator = _load_validator(
                sources["baseline"][VALIDATOR_PATH],
                temporary_path / "baseline-export",
                "baseline",
            )
            fixed_validator = _load_validator(
                sources["fixed"][VALIDATOR_PATH],
                temporary_path / "fixed-export",
                "fixed",
            )
            observations = run_case_matrix(baseline_validator, fixed_validator, temporary_path)
    except ReplayBlocked as error:
        report["reason_codes"].append(error.code)
        report["message"] = error.public_message
    except (NotImplementedError, OSError) as error:
        report["reason_codes"].append("UNSUPPORTED_PREREQUISITE")
        report["message"] = f"fixture setup is unsupported: {type(error).__name__}"
    finally:
        report["temporary_artifacts_cleaned"] = temporary_path is None or not temporary_path.exists()

    report["observed_replay"]["cases"] = observations
    observed_by_id = {item.get("id"): item for item in observations}
    matching = 0
    for expected in EXPECTED_CASES:
        observed = observed_by_id.get(expected["id"])
        if observed is None:
            continue
        if (
            observed.get("baseline", {}).get("decision") == expected["baseline"]
            and observed.get("fixed", {}).get("decision") == expected["fixed"]
        ):
            matching += 1

    essential_ids = {item["id"] for item in EXPECTED_CASES}
    all_executed = set(observed_by_id) == essential_ids and all(
        observed_by_id[case_id].get("baseline", {}).get("decision") in {"ACCEPTED", "REJECTED"}
        and observed_by_id[case_id].get("fixed", {}).get("decision") in {"ACCEPTED", "REJECTED"}
        for case_id in essential_ids & set(observed_by_id)
    )
    escape_ids = {item["id"] for item in EXPECTED_CASES if item["kind"] == "escape"}
    legitimate_ids = {item["id"] for item in EXPECTED_CASES if item["kind"] == "legitimate"}
    baseline_defect = all(
        observed_by_id.get(case_id, {}).get("baseline", {}).get("decision") == "ACCEPTED"
        for case_id in escape_ids
    )
    fixed_rejection = all(
        observed_by_id.get(case_id, {}).get("fixed", {}).get("decision") == "REJECTED"
        for case_id in escape_ids
    )
    legitimate_preserved = all(
        observed_by_id.get(case_id, {}).get("baseline", {}).get("decision") == "ACCEPTED"
        and observed_by_id.get(case_id, {}).get("fixed", {}).get("decision") == "ACCEPTED"
        for case_id in legitimate_ids
    )
    report["summary"] = {
        "essential_case_count": len(EXPECTED_CASES),
        "executed_case_count": len(observations),
        "matching_case_count": matching,
        "baseline_escape_defect_observed": baseline_defect,
        "fixed_escape_rejection_observed": fixed_rejection,
        "legitimate_cases_preserved": legitimate_preserved,
        "all_essential_checks_executed": all_executed,
    }

    if report["reason_codes"]:
        report["status"] = "BLOCKED"
    elif (
        all_executed
        and matching == len(EXPECTED_CASES)
        and baseline_defect
        and fixed_rejection
        and legitimate_preserved
        and report["temporary_artifacts_cleaned"]
    ):
        report["status"] = "PASS"
    else:
        report["status"] = "FAIL"
        report["reason_codes"].append("UNEXPECTED_BEHAVIOR")
        report["message"] = "observed behavior did not match every committed essential expectation"
    return report


def render_human(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"{report['case_id']} {report['status']}",
        f"source hashes verified: {report['prerequisites']['source_hashes_verified']}",
        f"essential cases: {summary['executed_case_count']}/{summary['essential_case_count']}",
        f"matching cases: {summary['matching_case_count']}/{summary['essential_case_count']}",
        f"temporary artifacts cleaned: {report['temporary_artifacts_cleaned']}",
    ]
    if report["reason_codes"]:
        lines.append("reason codes: " + ", ".join(report["reason_codes"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the complete machine-readable replay report")
    parser.add_argument("--repo-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = build_report(args.repo_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_human(report))
    return 0 if report["status"] == "PASS" else 2 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
