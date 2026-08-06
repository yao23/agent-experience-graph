# Self-Consumption Batch 01 execution results

This ledger is append-only. Times are UTC unless stated otherwise. Command and test counts are best-effort bounded execution metrics; unavailable token/cost data is recorded as `null` because this run exposes no reliable per-category token meter.

## Category 01 — Open-source CI rescue

- **Start/end:** 2026-08-06T06:48:31Z / 2026-08-06T06:50:39Z (batch incorporation only; original pilot executed earlier).
- **Selected target:** `mistralai/client-python` issue [#490](https://github.com/mistralai/client-python/issues/490), historical tag `v2.3.2`.
- **Repository/data source and license:** https://github.com/mistralai/client-python, Apache-2.0.
- **Source/fixed commits:** pre-fix `fe8a50340395fc2e427975e5bb01a79505973f05`; local fixed `e43224d23184802c74fe6095970a060a44042411`.
- **Task:** replace two synchronous test calls that depend on Python's removed implicit event-loop creation; preserve product behavior and assertions.
- **Why selected:** exact named tests, runtime-specific error, permissive license, fast local oracle, high cross-project relevance. Classification is non-blind historical replay because the issue and current main disclosed the repair.
- **Reproduction:** CPython 3.14.4; two named tests failed with `RuntimeError: There is no current event loop in thread 'MainThread'`; exit 1.
- **Frozen manifest:** `manifests/01-open-source-ci-rescue.json`; original frozen SHA-256 `a3090c653161531677df0673e634529dcacc29bf720b95148bd9b34afc413200`.
- **AEG query:** “Repair a public Python 3.14 test-infrastructure compatibility failure in mistralai/client-python release 2.3.2… Two OpenTelemetry tests fail because their event-loop lifecycle assumption was removed…” with reproduce/repair/verify subtasks and public/no-write/non-blind constraints.
- **Retrieval:** abstained. Best verified near-match `trace-2026-08-03-repair-lab-ci-v0.1.3` score 0.0373; second TR-04 score 0.0155; threshold 0.05; selected capsule 0 characters / 0 tokens.
- **Retrieval effect:** none; no experience used, no diagnostic/repair/verification change, small query/audit overhead only.
- **Hypothesis/attempts:** current-main attempt stopped because already fixed; PhenoFastMCP fallback stopped after invalid hook sources expanded to 199-file baseline churn; historical v2.3.2 reproduced exactly; `asyncio.run` repaired both call sites.
- **Failures/recovery:** full-suite collection initially missed the declared GCP extra; installed `gcp` extra and reran. Retained Python 3.16 pytest-asyncio deprecation warnings.
- **Changed external file:** `src/mistralai/extra/tests/test_otel_tracing.py`; patch SHA-256 `a3485a995c3db7cb2fe557a6346e3a7b8fb8fd16286393a72ad7b5e708fa866d`; 2 insertions/5 deletions.
- **Validation:** focused 2 passed; related module 18 passed; full suite 463 passed/46 external-integration skips; Ruff lint and format passed.
- **Metrics:** 3 bounded attempts; 31 completed commands; 533 test executions; elapsed/token usage `null` in the candidate because no reliable aggregate meter was available.
- **Privacy/license:** public Apache-2.0 source only; no credentials, private data, proprietary material, raw conversations, or external writes.
- **Classification:** **verified local historical replay**, non-blind, not actionable upstream. Equivalent repair exists on current main; contribution guide rejects direct PRs.
- **Candidate experience:** `candidates/01-open-source-ci-rescue.json` (schema and semantic validation passed in original pilot; copied artifact SHA-256 `b4c74b113f8cbb620fb6f816a946d32203cbe8b4adfd877cc809075b7daca7a4`).
- **Limitations:** not independent diagnosis; no Actions logs due expired local `gh`; 46 integration skips; no maintainer acceptance; publication schema field points to source issue because no PR exists.
- **External approval needed:** any comment/contact, fork/push/PR, workflow trigger, or candidate promotion.
- **Pilot 02 decision:** not executed tonight. Every shortlisted target failed at least one strict freshness/fidelity/contribution gate; see `evidence/01-freshness-shortlist.md`.
- **Next recommendation:** run a fresh search later and require the frozen current commit to fail before dependency installation. Prefer Python runtime/API drift with a host-faithful oracle.
