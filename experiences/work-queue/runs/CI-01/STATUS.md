# CI-01 — Black multiprocessing fallback

Status: partial
Owner: Codex
Category: build-ci-recovery
Started: 2026-08-02
Last updated: 2026-08-02
Attempts: 1
Time budget: 30 minutes
Current blocker: historical optional test infrastructure is incompatible or unavailable in the bounded modern environment

## Source lock

- Upstream repository: https://github.com/psf/black
- License: MIT
- Benchmark: BugsInPy Black bug 1
- Buggy commit: `26c9465a22c732ab1e17b0dec578fa3432e9b558`
- Focused scope: `reformat_many` executor initialization
- Evaluator-only fixed commit: `c0a7582e3d4cc8bec3b7f5a6c52b36880dcb57d7`
- Golden patch inspected: yes, only after candidate hash

## Checklist

- [x] Isolated source and license verified
- [x] `OSError` reproduced before source edit
- [x] Root-cause hypothesis recorded before editing
- [x] Existing verified AEG library searched; no match above threshold
- [x] One minimal candidate saved and hashed
- [x] Adapted focused test and syntax compilation passed
- [x] Candidate schema and semantic validation passed; natural-query retrieval score `0.1138`
- [x] Human fix compared after hashing
- [x] No upstream action or raw/private artifact publication

## Root cause and recovery

`ProcessPoolExecutor` is created unconditionally before the cleanup block, so an
OS-facility `OSError` escapes before scheduling. The candidate catches only that
initialization failure and supplies a one-worker `ThreadPoolExecutor`, retaining
the existing executor-based scheduling path.

## Attempt 1

- Changed file: `black.py`
- Patch SHA-256: `419bfd6a1b930a4638a8ff68e6b2002697a534c5247681be46c4ea2498836840`
- Before: adapted failure-injection test errored with `OSError`
- After: adapted focused test passed; source syntax compilation passed
- Cost: 1 attempt, 9 completed task commands, 4 test executions; duration and non-cached tokens unavailable

## Regression limitations

The upstream `tests/test_black.py` module could not load because the historical
optional aiohttp test infrastructure was unavailable/incompatible, and the full
suite was not run. The outcome is therefore partial.

## Evaluator comparison

Root cause and fallback semantics match. The candidate uses an explicit
one-worker thread executor; the human fix passes `None` to asyncio's default
executor and conditionally skips shutdown. Production strategies are not
textually identical, and the human commit also adds an integration test.

## Promotion

Decision: retain as a partial candidate until historical regression coverage is
reconstructed. This is experience collection, not causal AEG evidence.
