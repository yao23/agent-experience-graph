# AM-01 — Sanic `AsyncioServer` API parity

Status: partial
Owner: Codex
Category: api-dependency-migration
Started: 2026-08-02
Last updated: 2026-08-02
Attempts: 1
Time budget: 30 minutes
Current blocker: complete historical suite coverage and older asyncio/uvloop compatibility behavior remain unverified

## Source lock

- Upstream repository: https://github.com/sanic-org/sanic
- License: MIT
- Benchmark: BugsInPy Sanic bug 2
- Buggy commit: `ba9b432993019b0af0c4827a5ed42aaa091bd17d`
- Focused scope: `AsyncioServer` lifecycle proxy
- Evaluator-only fixed commit: `801595e24acdf8050b8d3ffa512d424147848d32`
- Golden patch inspected: yes, only after candidate hash

## Checklist

- [x] Isolated source and license verified
- [x] Missing wrapper API reproduced as `AttributeError`
- [x] Root-cause hypothesis recorded before editing
- [x] Existing verified AEG library searched; no match above threshold
- [x] One candidate saved and hashed
- [x] Adapted focused test, source compilation, and one upstream focused test passed
- [x] Candidate schema and semantic validation passed
- [x] Candidate natural-query retrieval passed at score `0.0996`
- [x] Human fix compared only after hashing
- [x] No upstream action or raw/private artifact publication

## Root cause and recovery

The wrapper manually exposed older lifecycle methods but did not track Python
3.7 additions on the underlying `asyncio.Server`. The candidate adds guarded
delegation for `start_serving` and `serve_forever`.

## Attempt 1

- Changed file: `sanic/server.py`
- Patch SHA-256: `661f79a497a2c01d460a69b8564891aae0b7840f897cc976a9bc81371040c43e`
- Before: adapted proxy test errored with `AttributeError`
- After: adapted delegation test passed; source compiled; upstream start-serving setup test passed alone
- Cost: 1 attempt, 10 completed task commands, 5 test executions; duration and non-cached tokens unavailable

## Regression limitations

Two localhost tests interfered through port reuse when run together, though each
focused case passed independently. The full historical suite was not run. The
candidate also lacks the human fix's `NotImplementedError` translation for an
older underlying server without these methods, so the result remains partial.

## Evaluator comparison

The root cause and direct delegation strategy match, but the source patches are
not textually or fully semantically identical. The human fix adds explicit
compatibility error handling and an integration test.

## Promotion

Decision: retain as a partial candidate pending compatibility and full-suite
coverage. This is experience collection, not causal AEG evidence.
