#!/usr/bin/env python3
"""Validate corrected Batch 02 evidence and its discovery-gate regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from selection_gate import evaluate_discovery


BATCH = Path(__file__).resolve().parent
ROOT = BATCH.parents[1]
PRIVATE_PATH_RE = re.compile(
    r"(?:/"
    + "Users"
    + r"/[^/\s]+/|/"
    + "home"
    + r"/[^/\s]+/|"
    + r"[A-Za-z]:\\"
    + "Users"
    + r"\\[^\\\s]+\\)"
)
TOKEN_RE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})")
FORBIDDEN_SUFFIXES = {
    ".bin",
    ".diff",
    ".gz",
    ".jsonl",
    ".log",
    ".patch",
    ".tar",
    ".zip",
}
ALLOWED_SUFFIXES = {".json", ".md", ".py"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(relative: str):
    return json.loads((BATCH / relative).read_text(encoding="utf-8"))


def validate_files() -> None:
    for path in BATCH.rglob("*"):
        if not path.is_file():
            continue
        require(
            path.name == ".gitkeep" or path.suffix in ALLOWED_SUFFIXES,
            f"unsupported file type: {path.relative_to(BATCH)}",
        )
        require(
            path.suffix not in FORBIDDEN_SUFFIXES,
            f"forbidden artifact: {path.relative_to(BATCH)}",
        )
        if path.name == ".gitkeep":
            continue
        text = path.read_text(encoding="utf-8")
        require(
            not PRIVATE_PATH_RE.search(text),
            f"private path in {path.relative_to(BATCH)}",
        )
        require(
            not TOKEN_RE.search(text),
            f"credential-like token in {path.relative_to(BATCH)}",
        )


def validate_correction() -> dict[str, int | str]:
    state = load("execution-state.json")
    require(state["screened"] == 24, "screened total must remain 24")
    require(
        state["qualifiedUnderPreregisteredGates"] == 0,
        "corrected qualified total must be zero",
    )
    require(
        state["incorrectlyAcceptedDuringInitialScreening"] == 1,
        "incorrectly accepted total must be one",
    )
    require(
        state["freshEligibleExecutions"] == 0,
        "fresh eligible execution total must be zero",
    )
    require(
        state["independentLocalReproductions"] == 1,
        "independent reproduction total must be one",
    )
    require(state["promotionReady"] == 0, "promotion-ready total must be zero")

    candidate = load("candidates/category-01-click-progressbar.json")
    require(len(candidate) == 1, "expected one corrected candidate")
    local = candidate[0]["verification"]["localChecks"]
    require(
        "invalid for fresh-task qualification"
        in local["postBatchCorrectedClassification"].lower(),
        "candidate lacks corrected classification",
    )
    limitations = " ".join(candidate[0]["limitations"]).lower()
    require(
        "public prior repair" in limitations,
        "candidate must disclose public prior repair",
    )

    retrieval = load("evidence/category-01-retrieval.json")
    correction = retrieval["postBatchCorrection"]
    require(
        correction["freshTaskQualification"] is False,
        "retrieval must be scoped away from fresh-task evidence",
    )
    require(
        correction["retrievalBenefitEvidence"] is False,
        "retrieval must not claim affirmative benefit",
    )

    fixture = load("fixtures/fork-only-linked-repair.json")
    decision = evaluate_discovery(fixture)
    require(
        decision["eligible"] is fixture["expected"]["eligible"],
        "fork-only regression eligibility mismatch",
    )
    require(
        fixture["expected"]["reason"] in decision["reasons"],
        "fork-only regression did not reject prior repair",
    )

    for relative in (
        "selection-ledger.md",
        "execution-results.md",
        "batch-02-decision.md",
    ):
        text = (BATCH / relative).read_text(encoding="utf-8")
        require(
            "Post-Batch-02 superseding correction" in text,
            f"missing append-only correction in {relative}",
        )

    return {
        "status": "passed",
        "files": sum(path.is_file() for path in BATCH.rglob("*")),
        "screened": state["screened"],
        "qualified": state["qualifiedUnderPreregisteredGates"],
        "independentLocalReproductions": state["independentLocalReproductions"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref")
    args = parser.parse_args()
    validate_files()
    result = validate_correction()
    if args.base_ref:
        subprocess.run(
            [
                "git",
                "diff",
                "--exit-code",
                args.base_ref,
                "--",
                "experiences/verified.json",
            ],
            cwd=ROOT,
            check=True,
        )
        result["baseRef"] = args.base_ref
        result["verifiedLibraryChanged"] = False
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
