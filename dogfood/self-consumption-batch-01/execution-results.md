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

## Category 02 — API/dependency migration

- **Start/end:** 2026-08-06T06:50:39Z / 2026-08-06T06:55:16Z.
- **Selected target:** `batonogov/pine` issue [#122](https://github.com/batonogov/pine/issues/122), historical `actions/checkout` v4→v6 migration.
- **Repository/source and license:** https://github.com/batonogov/pine, MIT.
- **Source/fixed commits:** frozen parent `455c7f386544e3b008e6286abd2a80e3647a4366`; upstream fix `5b373564a72575bba8fa1b9aded17fa9d02ac2aa`; local replay `f7beda8840c6d045dae7ed53a614cecfefb36aef`.
- **Why selected:** exact three-reference dependency edge, public deprecation evidence, permissive license, small patch, deterministic frozen parent, and a focused local completeness oracle. It is explicitly non-blind and historical.
- **Shortlist:** two candidates inspected deeply; five search results considered; top three and rejection reasons are in `evidence/02-candidate-shortlist.md`. OHWR failed freshness because current main was already migrated; local-gpss had an open duplicate PR.
- **Frozen manifest:** `manifests/02-api-dependency-migration.json`; SHA-256 `06772c61f8db63d6241283bdfdc5045ac4f9af397e616264b2bd4c96616e1e9c`.
- **AEG query:** upgrade the GitHub Actions checkout dependency from the Node 20 runtime to a Node-24-compatible major version across YAML workflows, verify every reference, and preserve workflow behavior.
- **Retrieval:** abstained at threshold 0.05; diagnostic best match was the Repair Lab record at 0.0143 through a generic `GitHub Actions` tag; TR-04 scored 0.0; selected capsule 0 characters / 0 tokens.
- **Retrieval effect:** none. The below-threshold CI-process overlap did not change candidate selection, diagnosis, patch, or verification.
- **Reproduction:** on the frozen parent, the focused scan found three `actions/checkout@v4` references and exited 1 as expected.
- **Repair:** replayed the exact upstream three-line v4→v6 migration in `.github/workflows/ci.yml` and `.github/workflows/release.yml`; 3 insertions/3 deletions; patch SHA-256 `46d93659be6a3676aea21ff56febc780d77a36125821559ee1a9773f277e4a3c`.
- **Validation:** zero v4 and exactly three v6 references; all three workflows parsed as YAML; `git diff --check` passed. Candidate schema/semantic validation passed.
- **Metrics:** 2 bounded candidate attempts; 15 completed commands; 2 focused oracle executions; elapsed/token usage `null` where no reliable meter exists.
- **Privacy/license:** public MIT source and public issue metadata only; no secrets, private data, proprietary material, or external writes.
- **Classification:** **partial verified historical replay**. Local configuration checks pass, but no hosted Actions run was triggered, so Node 24 runner execution is not claimed.
- **Candidate experience:** `candidates/02-api-dependency-migration.json`, valid but unpromoted.
- **Limitations:** known repair; closed issue; no blind diagnosis; local YAML/reference checks do not exercise action download or hosted runners; no new maintainer acceptance.
- **External approval needed:** any upstream contact, push/PR, workflow trigger, or promotion into `experiences/verified.json`.
- **Next recommendation:** prefer an open, still-reproducible runtime/API edge with a local compiler or unit-test oracle; reject default branches that already contain the migration before setup.

## Category 03 — Regression-test gap

- **Start/end:** 2026-08-06T06:55:16Z / 2026-08-06T06:58:03Z.
- **Selected target:** AEG's MIT-0 `protocol-resource-delegation` dependency-free transfer fixture, copied to `/tmp`; related public source is Apache-2.0 Tornado BugsInPy bug 1.
- **Why selected:** it preserves the verified TR-04 topology—public wrapper → protocol → active stream—while changing domains from TCP_NODELAY to channel keepalive, giving a deterministic test of experience transfer. This is controlled fixture value, not a fresh upstream contribution.
- **Shortlist:** three scored; historical Tornado replay rejected as duplicate, current OpenClaw issue rejected as risky/unbounded. See `evidence/03-candidate-shortlist.md`.
- **Frozen manifest:** `manifests/03-regression-test-gap.json`; SHA-256 `40f3a92f0fd201d1a0ce3783386ae73d4705b5051addfcacf3d4a75b7f28b863`.
- **AEG query:** repair a green-suite false positive where public `Channel.set_keepalive` reaches a stale direct socket after ownership moved behind a protocol; assert delegation to the active stream.
- **Retrieval:** TR-04 selected at 0.101 (>0.05) through task similarity 0.0556, `recommendedFor` similarity 0.0309, and `green test false positive` tag 0.0145. Repair Lab scored 0.0193 diagnostically. Four TR-04 lessons and four skills were returned; no separate hidden capsule was used.
- **Retrieval effect:** yes, qualitatively. Before editing, the retrieved ownership rule selected `Channel.set_keepalive → ChannelProtocol.set_keepalive → stream.set_keepalive` and ruled out restoring a stale direct socket. No unassisted control arm ran, so no causal time/token gain is claimed.
- **False-green proof:** a legacy protocol-send test passed; the focused public-control test then failed with `AssertionError` at the obsolete `Channel.socket` access.
- **Repair:** one production file; route the public method through an abstract protocol method implemented by `TcpChannelProtocol`; patch SHA-256 `9f7d1e3dced1de789f7e83df08d8e53464978b1555152770f88532212a556fc1`.
- **Validation:** regression failed before/passed after; legacy test remained green; 2 post-repair tests passed; all three Python files compiled with pycache redirected to `/tmp`; candidate semantic validation passed.
- **Metrics:** 1 attempt; 8 completed commands; 4 test executions; three ownership hops; elapsed/token usage `null`.
- **Privacy/license:** original MIT-0 fixture plus disclosed Apache-2.0 public provenance; no credentials, private data, proprietary snippets, or external writes.
- **Classification:** **verified controlled transfer**. Strong mechanism-level relevance, but expected high similarity because the fixture was designed from TR-04.
- **Candidate experience:** `candidates/03-regression-test-gap.json`, valid but unpromoted.
- **Limitations:** synthetic transfer target; no baseline arm; legacy test added only in `/tmp`; no fresh upstream or maintainer acceptance evidence.
- **External approval needed:** any repository patch beyond these batch artifacts, upstream contact, or experience promotion.
- **Next recommendation:** repeat on an independently discovered public wrapper/proxy issue frozen before its fix is inspected, retaining the same terminal delegate-call oracle.

## Category 04 — Documentation example doctor

- **Start/end:** 2026-08-06T06:58:03Z / 2026-08-06T09:28:00Z. The 45-minute wall-clock target was exceeded; command and file bounds were respected.
- **Selected target:** Pendulum open PR [#920](https://github.com/python-pendulum/pendulum/pull/920), fluent timezone-helper example in `docs/docs/fluent_helpers.md`; MIT.
- **Frozen source:** current main `5ad098bc7b74d660679f0606673728042b9d4aca`; PR commit `0e32103a99d623c3fb4482fafb3d659f3b650708`; non-blind and duplicate-work constrained.
- **Why selected:** current main still reproduces, one docs file, five deterministic credential-free outputs, existing PR provides public defect evidence but forbids a competing contribution.
- **Manifest/shortlist:** `manifests/04-documentation-example-doctor.json` SHA-256 `215250a8f30582a4c053093318a417bfd259ab99854cd2130fcac2531f209a36`; three scored in `evidence/04-candidate-shortlist.md`.
- **AEG retrieval:** abstained at 0.05; diagnostic scores Repair Lab 0.0217 and TR-04 0.0112; no capsule and no repair-path effect.
- **Reproduction:** running the five operations in documented order showed state leakage from repeated `dt` reassignment; only 3/5 displayed outputs matched runtime values.
- **Repair:** start every transformation from `dt0`; retain the PR's DST explanation but shorten it to remove trailing whitespace. One docs file, 7 insertions/6 deletions; patch SHA-256 `3eeb3f4bd7f7a6cc18c9303bcb2cedb0f936c70f92d6810e8f392da006b4d3c5`.
- **Validation:** 5/5 runtime values matched; `git diff --check` passed; candidate semantic validation passed. Complete library tests were not run because production code did not change.
- **Metrics:** 1 attempt; 14 commands; 2 before/after executable-example checks; elapsed/token meter `null`.
- **Classification:** **verified documentation-only historical/current replay**, with existing open PR and no duplicate external write.
- **Limitations:** repair disclosed by PR; wall-clock budget exceeded; dependencies downloaded publicly; no maintainer acceptance; no docs-site build.
- **External approval needed:** any comment on PR #920, push, competing PR, or experience promotion.
- **Next recommendation:** add an automated extractor that executes fenced Python examples in isolated scopes and compares normalized displayed outputs.
