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

## Category 05 — Agent skill/MCP compatibility

- **Start/end:** 2026-08-06T09:28:00Z / 2026-08-06T11:43:08Z. The 30-minute wall-clock target was exceeded; the 20-command bound was respected.
- **Selected target:** `@modelcontextprotocol/server-filesystem@2026.7.10`, source commit `9a96ea6e5913736f92b88345bf51caeaaa8e719f`; npm integrity frozen; repository licensing transitions new code to Apache-2.0.
- **Permission envelope:** stdio only; single disposable `/tmp/aeg-batch01-cat05-mcp` root; no Roots capability, credentials, external data, or write-tool calls.
- **Manifest/shortlist:** `manifests/05-agent-skill-mcp-compatibility.json` SHA-256 `198e053c0c5b53ffe2376c360c7648c3c872187c571d73ff0e88cc398b4027cb`; three candidates scored in `evidence/05-candidate-shortlist.md`.
- **AEG retrieval:** procedure deviation—the query ran after execution. It abstained (best diagnostic TR-04 0.005; Repair Lab 0.0), and necessarily had no effect.
- **Startup/recovery:** initial npm use collided with the restricted user cache; redirected npm cache to `/tmp`, then initialized protocol `2025-11-25`. Server identified as `secure-filesystem-server` 0.2.0.
- **Discovery:** 14 tools with JSON schemas and annotations; both read and destructive capabilities were visible. This card covers only the invoked read-only surface.
- **Safe task:** `read_text_file` returned the exact probe text; output SHA-256 `6efb5ec7fab84c0d31fa8f720cc8b99e05a3e63eca6cca4bb91eb7081729ce78`.
- **Failure contract:** the same tool on `/etc/hosts` returned `isError: true` and explicitly denied the path outside the two normalized forms of the allowed `/tmp` root.
- **Termination:** SIGINT bounded the subprocess; exit 1 reflects the signal. Graceful zero-exit protocol shutdown was not demonstrated.
- **Distribution defect:** installed package `package.json` SHA-256 `6b2c11d4d348cace9c652636d602713c377ba59d868e013de69f3a9046d61244` declares `SEE LICENSE IN LICENSE`, but no LICENSE file ships in the package. Public repository licensing is explicit but transitional.
- **Metrics:** 2 attempts; 17 commands; 2 tool invocations; 14 tools discovered; elapsed/token meter `null`.
- **Classification:** **partial scoped compatibility**—handshake, discovery, read, and confinement pass; packaged licensing and graceful shutdown remain incomplete.
- **Limitations:** late retrieval; destructive tools untested; npm transitive `glob@10.5.0` warning not investigated; no Roots-capable client, Windows, dynamic roots, or media/write tests.
- **External approval needed:** registry publication, maintainer contact, issue/PR, destructive/write-tool testing outside the disposable root, or experience promotion.
- **Next recommendation:** retest with a tiny client that sends Roots and a documented shutdown sequence, and separately report the missing packaged LICENSE file if authorized.

## Category 06 — Public-data ETL/quality

- **Start/end:** 2026-08-06T11:43:08Z / 2026-08-06T12:17:00Z. The 30-minute wall-clock target was exceeded by roughly four minutes; all data/command bounds held.
- **Selected source:** USGS FDSN Event Web Service API 2.7.0, fixed 2025-01-01 UTC day, ascending time, limit 100. USGS-produced data are U.S. public domain; credit U.S. Geological Survey.
- **Bounds/retention:** raw 71–72 KB; 100 records; raw, pipeline, and output remain only in `/tmp`; repository stores aggregates and hashes.
- **Manifest/shortlist:** `manifests/06-public-data-etl-quality.json` SHA-256 `4cc7a29b412c3283867bdb9afbf1ddee5677de60fd4d928771c5aeea1b28fa76`; three candidates in `evidence/06-candidate-shortlist.md`.
- **AEG retrieval:** procedure deviation—query ran after execution; abstained at 0.05 (Repair Lab 0.0139; TR-04 0.0055), so no effect.
- **Quality defects:** query metadata omitted documented `metadata.count`; direct feature count was required. Unfiltered first 100 contained 99 earthquakes and one explosion (`ak0251nkqz1`).
- **Profile:** zero duplicate IDs; core magnitude/place/time/updated complete; optional fields frequently null (`tz` 100, `felt/cdi` 95, `mmi/alert` 99, `nst/dmin/gap` 15); all geometries had three coordinates and times were ascending.
- **Repair:** add `eventtype=earthquake` at the API boundary; validate every row; count features; normalize epoch milliseconds to UTC `Z`; select eight fields; sort by `(time_utc,event_id)`; stable sorted-key JSON.
- **Validation:** unfiltered input failed loudly on the explosion; filtered 100-row input passed; output 25,871 bytes, unique IDs, all UTC; two executions byte-identical at SHA-256 `170e98907baefe2559e88d0298973f3553e69788bd94dd19d84faec6be175459`.
- **Source/pipeline hashes:** unfiltered `7b3936...c9995`; filtered `852da5...8657`; pipeline `3a0b72...26d0` (full hashes in candidate).
- **Metrics:** 1 attempt; 12 commands; 3 ETL oracle runs; 100 rows; token/runtime meter `null`.
- **Classification:** **verified bounded ETL/quality repair** on frozen response bytes.
- **Limitations:** historical catalog revisions can change future URL responses; schema commit fields use disclosed content-digest prefixes because the source is not VCS; one day/first 100 only; late retrieval; no raw rows retained.
- **External approval needed:** publishing output, calling any write API, contacting USGS, or promoting the experience.
- **Next recommendation:** snapshot the response under an explicitly permitted data-fixture policy or add ETag/Last-Modified capture, then repeat on pagination boundaries.

## Category 07 — AEG self-maintenance

- **Start/end:** 2026-08-06T12:17:00Z / 2026-08-06T15:05:14Z. The 30-minute wall-clock target was exceeded; file and 20-command bounds held.
- **Selected target:** AEG at pre-fix `e7ab21fead7af45050003a312bae4cca60b2a7d8`, MIT-0; canonical verified-evidence path resolution.
- **Task/selection:** harden the semantic validator so promoted evidence cannot name missing, absolute, or repository-escaping files. Selected over ambiguous version alignment and already-green README links because it reproduced a real two-file false positive without release overlap.
- **Manifest/shortlist:** `manifests/07-aeg-self-maintenance.json` SHA-256 `e54c11fb08acee076aa877ba81b569a2bf9e02ca9f9900dad81706fd43eb1554`; three candidates have per-dimension 1–5 scores in `evidence/07-candidate-shortlist.md`.
- **AEG retrieval:** queried before repair; abstained at 0.05. Diagnostic scores: Repair Lab 0.0171 from generic validation/CI overlap; TR-04 0.0049. No capsule or execution effect.
- **Reproduction:** changed both provenance and verification in memory to `experiences/missing-result.json`; the old `validate_library` returned `passed` because it checked string equality but not existence.
- **Hypothesis/repair:** add a separate canonical-library evidence-file pass, reject absolute/`..` paths, and require five known evidence fields to resolve to regular files. Keep portable `--library` candidate validation free of AEG-repository layout assumptions.
- **Failures/recovery:** bare `python -m unittest discover` reported zero tests; switched to the explicit CI-listed test commands. No production failure or unrelated edit occurred.
- **Changed AEG files:** `scripts/validate_verified_experiences.py`, `scripts/test_validate_verified_experiences.py`; fixed commit `e001b094ab3373747ff756e104985741fb1880e4`; 36 insertions/1 deletion; patch SHA-256 `1f40ec46d7746c77f6d3851e23866c8c812bc047842b937fc0c4342b0de8fc96`.
- **Validation:** 6 focused semantic tests; 42 CI-listed Python tests; canonical semantic audit; paired-results aggregate; natural-transfer validation; AJV schema; 20 extension tests including source/bundle equality—all passed. Extension `npm audit` reported 0 vulnerabilities.
- **Metrics:** 1 attempt; 16 completed commands; 62 unit tests; elapsed/token meter `null`.
- **Privacy/license:** public MIT-0 AEG data only; no promoted record, schema, version, release file, private data, credential, or external write.
- **Classification:** **verified internal maintenance repair**, internal operational value only—not cross-project or PMF evidence.
- **Candidate experience:** `candidates/07-aeg-self-maintenance.json`, schema/semantic validation passed and unpromoted.
- **Limitations:** existence does not prove evidence truth/freshness; automatic resolution is canonical-library-only; wall-clock bound exceeded; hosted CI and review absent.
- **External approval needed:** push/PR, merge/cherry-pick into another branch, release, or experience promotion.
- **Next recommendation:** extend the canonical audit with optional content hashes and evidence-type-specific validators, preserving candidate portability.

## Batch summary

| Category | Target | Result | AEG retrieval | Objective evidence | External value | Next action |
| -------- | ------ | ------ | ------------- | ------------------ | -------------- | ----------- |
| 01 CI rescue | Mistral #490 historical v2.3.2 | Verified historical replay | Correct abstention; best 0.0373 | 2 focused, 18 module, 463 full-suite passes; lint/format pass | Reusable Python 3.14 event-loop lesson; no current upstream need | Search later with strict freshness and host-fidelity gates |
| 02 migration | Pine #122 checkout v4→v6 | Partial historical replay | Correct abstention; best 0.0143 | 3 old refs before, 0 after; 3 YAML files parse | Reusable completeness oracle; hosted runtime untested | Prefer open compiler/test-backed migration |
| 03 test gap | AEG protocol delegation transfer fixture | Verified controlled transfer | TR-04 reused at 0.101 | Legacy green; regression fail→pass; compile pass | Mechanism-level transfer only | Test an independently discovered public boundary |
| 04 docs | Pendulum PR #920 | Verified docs replay | Correct abstention; best 0.0217 | 3/5 outputs before, 5/5 after; diff check pass | Confirms existing PR and catches whitespace; no duplicate write | Automate isolated fenced-example execution |
| 05 MCP | Filesystem server 2026.7.10 | Partial compatibility | Correct abstention; best 0.005, queried late | Handshake, 14-tool discovery, read success, outside-root denial | Scoped compatibility plus missing packaged-license evidence | Retest Roots/graceful shutdown; report license only if approved |
| 06 data | USGS fixed-window earthquake ETL | Verified bounded pipeline | Correct abstention; best 0.0139, queried late | Explosion rejected; 100 rows; repeat SHA-256 identical | Deterministic public-domain data-quality pattern | Capture HTTP revision metadata and test pagination |
| 07 maintenance | AEG evidence-file validation | Verified internal repair | Correct abstention; best 0.0171 | False pass reproduced; 62 tests plus schema/result validation pass | Canonical provenance reliability only | Review local commit; consider evidence hashes later |

- **Status:** 5 completed verified categories, 2 partial categories, 0 blocked, 0 skipped, 0 failed. All seven pilots produced schema/semantic-valid candidate files; 5 have passed verification and 2 are intentionally partial.
- **Retrieval:** 6 correct abstentions; 1 reused experience (TR-04 in Category 03); 0 misleading above-threshold retrievals. Category 03 documented a qualitative repair-path effect, but no baseline arm supports a causal efficiency claim. Categories 05 and 06 queried too late, a procedural defect preserved as negative evidence.
- **Aggregate bounded metrics:** 113 completed commands and 608 reported test/oracle executions across candidate records; batch wall time 8h16m43s. Counts mix unit-test cases and focused oracle executions and should not be treated as a normalized performance metric. Reliable token/cost data were unavailable, so total tokens/cost are `null`.
- **Strongest reusable lesson:** pair a positive oracle with a deliberately failing boundary check, and verify the actual owned artifact/path—not merely agreement between metadata fields or a green legacy suite.
- **Most promising repeated family:** deterministic contract and compatibility validation (public wrapper delegation, executable examples, protocol permissions, schema/data invariants) because it transfers cleanly and yields cheap before/after evidence.
- **AEG product friction:** the verified library is still sparse and abstained in 6/7 categories; retrieval-before-execution is manual enough to be missed; capsule-size accounting is not built in; the verified-experience schema assumes VCS repair commits and PR URLs, which fits compatibility cards and non-VCS data poorly.
- **AEG change proposed and implemented locally:** canonical promoted evidence paths must be repository-relative and resolve to files (`e001b09`). No version, release, schema, or promoted-library change was made.
- **External actions awaiting approval:** push/open an AEG PR for the batch and validator repair; optionally comment on Pendulum #920 about validation/whitespace; optionally report the MCP package's missing LICENSE file; publish none of the candidates or data without review. Pine/Pendulum/fixture/data patches remain local under `/tmp`.
- **Recommended Batch 02:** do not start automatically. First add an automated `freeze → retrieve → execute` harness with query/capsule metrics, then run fewer fresh public candidates whose default commits still fail and whose contribution paths have no active repair PR. Prioritize independently discovered contract-test gaps and compiler-backed API migrations.
- **Evidence level:** the batch supports technical feasibility and limited external usefulness through reproducible public checks. It does **not** establish maintainer acceptance, generalized effectiveness, causal AEG performance improvement, or product-market fit.
