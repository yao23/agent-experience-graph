# AEG natural-transfer benchmark v1

This directory contains a frozen, five-task benchmark for testing whether a
retrieved debugging experience transfers to a later, naturally occurring bug.
It is deliberately not a collection of tasks invented to reward a known
experience. The pairs were selected from BugsInPy metadata and the corresponding
upstream Git histories before any arm was run.

The source and transfer bugs are non-identical members of these failure
families:

1. Scrapy CookieJar adapter compatibility on Python 3.
2. Scrapy redirect `Location` normalization.
3. Scrapy browser-like HTML form-control translation.
4. FastAPI/Pydantic request-field classification.
5. Black comment/directive attachment around decorators.

`manifest.json` is the pre-registration. It fixes the five pairs, prompts,
capsules, retrieval scores and thresholds, one abstention, three randomized arm
orders per task, budgets, contamination controls, measurements, evaluation
rules, and the positive-result criterion. `environment-lock.json` freezes the
CPython runtime, platform, and complete package set after a modern parser was
found to mask one candidate oracle during pre-execution preparation; that pair
was replaced and no arm had run. Upstream evidence links and controller hashes
make the selection independently auditable.

## Blindness and isolation

The controller constructs a seed from the transfer bug's buggy production tree
and replaces only the declared regression-test files with their contents at the
later fixed commit. It then creates a new repository with one commit. Thus an
arm contains the failing oracle but no upstream history, remote, fixed commit,
human production patch, manifest, capsule file, other-arm artifact, or evaluator
feedback.

Sibling worktrees are prohibited after the pre-execution isolation failure
documented in `PROTOCOL-DEVIATION-846d018.md`. Each arm instead runs on a fresh
GitHub-hosted `macos-14` arm64 VM from a sanitized, single-arm envelope. The
agent receives no Actions/artifact credential, other-arm artifact, shared
writable cache, full manifest, or evaluator data. The task prompt remains fixed
across arms. For a treatment that passes the gate, the envelope includes only
the five fields of the compact source capsule. An abstaining treatment receives
exactly the task prompt and is recorded as an AEG abstention.

Pairwise evaluation begins only after both arms finish. The human production
diff remains controller-side and is used for deterministic changed-file, token,
and changed-symbol similarity. Tests remain authoritative.

## Commands

Validation and CI-safe isolation checks do not invoke an agent or access the
network:

```sh
python3 experiments/natural-transfer-benchmark/run_benchmark.py validate
python3 experiments/natural-transfer-benchmark/run_benchmark.py self-test
python3 experiments/natural-transfer-benchmark/test_run_benchmark.py
```

After this exact manifest passes CI, prepare all historical seeds from local
upstream mirrors:

```sh
python3 experiments/natural-transfer-benchmark/run_benchmark.py prepare \
  --output /tmp/aeg-natural-transfer-prepare \
  --mirror scrapy=/path/to/scrapy \
  --mirror fastapi=/path/to/fastapi \
  --mirror black=/path/to/black \
  --python-env scrapy=/path/to/scrapy-venv \
  --python-env fastapi=/path/to/fastapi-venv \
  --python-env black=/path/to/black-venv
```

The legacy local `run` path is fail-closed because sibling worktrees do not meet
the isolation protocol. The frozen 30-arm protocol may be dispatched only by
the disposable-runner coordinator after its actual-environment adversarial
preflight passes. Repair failure is benchmark data; protocol, blindness, or
controller failures remain infrastructure failures.

## Interpretation

Results are reported per task before macro medians. Wall-clock time is measured
but is excluded from the benefit rule. A positive benchmark result requires
help across at least two injected tasks and no material aggregate increase in
regressions, patch complexity, or non-cached token cost. The abstaining task is
reported as a gate decision and is not evidence for or against repair quality.
