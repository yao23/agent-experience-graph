#!/usr/bin/env python3
"""Fail-closed evaluation for fresh public-task repair discovery."""

from __future__ import annotations

from datetime import datetime
from typing import Any


REQUIRED_SEARCH_KINDS = (
    "issue_timeline",
    "issue_development_links",
    "cross_referenced_prs",
    "upstream_prs_all_states",
    "fork_prs",
    "linked_commits",
    "exact_issue_reference_global",
    "defect_wording_repository",
    "defect_wording_global",
    "public_patch_search",
    "default_branch_recent_changes",
    "contributor_branches",
)


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_discovery(record: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic eligibility decision from frozen search evidence."""
    accepted_at = _timestamp(record["acceptanceCandidateAt"])
    searches = record.get("searches", [])
    indexed = {item.get("kind"): item for item in searches}
    missing = [kind for kind in REQUIRED_SEARCH_KINDS if kind not in indexed]
    malformed: list[str] = []
    if len(indexed) != len(searches):
        malformed.append("duplicate-search-kind")
    late: list[str] = []
    prior_repairs: list[dict[str, str]] = []

    for kind in REQUIRED_SEARCH_KINDS:
        search = indexed.get(kind)
        if search is None:
            continue
        if not isinstance(search.get("query"), str) or not search["query"]:
            malformed.append(f"{kind}:query")
        if not isinstance(search.get("urls"), list) or not search["urls"]:
            malformed.append(f"{kind}:urls")
        if not isinstance(search.get("results"), list):
            malformed.append(f"{kind}:results")
            continue
        queried_at = search.get("queriedAt")
        if not isinstance(queried_at, str):
            malformed.append(f"{kind}:queriedAt")
            continue
        if _timestamp(queried_at) > accepted_at:
            late.append(kind)

        for index, result in enumerate(search["results"]):
            result_path = f"{kind}:results[{index}]"
            if not isinstance(result, dict):
                malformed.append(result_path)
                continue
            disclosure = result.get("discloses", {})
            created_at = result.get("createdAt")
            url = result.get("url")
            required_result_fields = {
                "url": isinstance(url, str) and bool(url),
                "createdAt": isinstance(created_at, str) and bool(created_at),
                "state": isinstance(result.get("state"), str)
                and bool(result.get("state")),
                "location": isinstance(result.get("location"), str)
                and bool(result.get("location")),
                "public": isinstance(result.get("public"), bool),
                "discloses": isinstance(disclosure, dict)
                and all(
                    isinstance(disclosure.get(name), bool)
                    for name in ("rootCause", "repair", "tests")
                ),
            }
            invalid_fields = [
                name for name, valid in required_result_fields.items() if not valid
            ]
            if invalid_fields:
                malformed.extend(f"{result_path}:{field}" for field in invalid_fields)
                continue
            if not result["public"]:
                continue
            if _timestamp(created_at) >= accepted_at:
                continue
            disclosed = [
                name
                for name in ("rootCause", "repair", "tests")
                if disclosure.get(name) is True
            ]
            if disclosed:
                prior_repairs.append(
                    {
                        "kind": kind,
                        "url": url,
                        "createdAt": created_at,
                        "disclosed": ",".join(disclosed),
                    }
                )

    reasons: list[str] = []
    if missing or malformed:
        reasons.append("selection_evidence_incomplete")
    if late:
        reasons.append("selection_search_ran_after_acceptance")
    if prior_repairs:
        reasons.append("public_prior_repair")

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "missingSearchKinds": missing,
        "malformedEvidence": malformed,
        "lateSearchKinds": late,
        "priorRepairs": prior_repairs,
    }
