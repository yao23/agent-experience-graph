# Batch 01 Executive Evidence Audit

Audit date: 2026-08-06. This audit classifies evidence, not JSON shape. Schema and semantic validity are necessary checks, but neither qualifies an experience for promotion. No candidate is promoted by this report.

## Executive table

| Category | Outcome | Retrieval timing valid? | AEG action | Experience reused? | External value | Promotion class | Key limitation |
|---|---|---|---|---|---|---|---|
| 01 CI rescue | 463-test historical repair replay passed | Yes—before execution | Abstained at 0.05 | No | General Python 3.14 CI lesson; no current repair need | historical/non-blind replay | Known issue repair on an old release; current main is already fixed |
| 02 dependency migration | Static migration oracle passed; hosted runtime untested | Yes—before execution | Abstained at 0.05 | No | Useful completeness oracle; upstream repair already exists | historical/non-blind replay | Known fix and no hosted Actions execution |
| 03 regression-test gap | Controlled fail-before/pass-after transfer passed | Yes—before diagnosis/repair | Recommended TR-04 at 0.101 | Yes | Demonstrates mechanism transfer in a synthetic AEG fixture | locally verified but awaiting external evidence | Target was designed from the retrieved pattern; no independent upstream acceptance |
| 04 documentation doctor | Executable example improved from 3/5 to 5/5 | Yes—before execution | Abstained at 0.05 | No | Confirms a real public docs defect | historical/non-blind replay | Existing open PR disclosed the fix and blocks a competing contribution |
| 05 MCP compatibility | Read-only compatibility surface partial | **No—invalid/contaminated** | Late abstention; excluded from retrieval metrics | No | Bounded compatibility and missing-package-license evidence | partial | Retrieval was post hoc; packaged license and graceful shutdown remain unresolved |
| 06 public-data ETL | Bounded deterministic pipeline passed | **No—invalid/contaminated** | Late abstention; excluded from retrieval metrics | No | Reusable public-data quality oracle | locally verified but awaiting external evidence | Post-hoc retrieval, revisable source response, and non-VCS provenance encoding |
| 07 AEG maintenance | Validator false-positive reproduced and repaired | Yes—before repair | Abstained at 0.05 | No | Protects users from promoted records naming nonexistent evidence | locally verified but awaiting external evidence | Local-only repair lacks hosted CI, review, and upstream acceptance |

## Candidate-by-candidate audit

### 01 — Open-source CI rescue

- **Classification:** historical/non-blind replay.
- **Objective verification:** 2 focused tests, 18 module tests, 463 full-suite tests, lint, and format checks passed on the frozen Mistral v2.3.2 target.
- **Retrieval and effect:** AEG was queried before execution and correctly abstained (best diagnostic score 0.0373). No prior experience was reused and execution did not change because of retrieval.
- **Blindness/currentness:** blindness was not preserved: issue #490 and its repair were known. The historical source is reproducible, but current main already contains the repair, so there is no fresh upstream defect.
- **External value/acceptance:** the event-loop compatibility lesson is reusable, but external users do not need this patch now. The historical project state supplies issue evidence, not new acceptance of this work.
- **Legal/privacy:** Apache-2.0 public source; sanitized aggregate evidence only; no credentials, private paths, conversations, or proprietary content retained.
- **Promotion limit:** known-fix replay, non-blind execution, and no current contribution path.

### 02 — API/dependency migration

- **Classification:** historical/non-blind replay.
- **Objective verification:** three obsolete checkout references became zero and all three changed YAML files parsed. Hosted GitHub Actions execution was not performed.
- **Retrieval and effect:** AEG was queried before execution and abstained (best 0.0143). No experience was reused and retrieval did not change execution.
- **Blindness/currentness:** blindness was not preserved because Pine issue #122 and linked repairs #133/#134 disclosed the migration. The source is historical; the upstream repair is already accepted.
- **External value/acceptance:** the completeness oracle can help similar migrations, but this patch offers no new value to current Pine users. Acceptance exists for the historical upstream fix, not for this replay.
- **Legal/privacy:** MIT public source and sanitized counts/digests only; no sensitive material retained.
- **Promotion limit:** known repair plus incomplete runtime verification.

### 03 — Regression-test gap

- **Classification:** locally verified but awaiting external evidence.
- **Objective verification:** the legacy test stayed green, a new terminal delegate-call regression test failed before and passed after the change, and compilation passed.
- **Retrieval and effect:** AEG was queried before diagnosis. TR-04 cleared the threshold at 0.101, was reused, and changed the selected repair path toward a three-hop terminal-call oracle.
- **Blindness/currentness:** task freezing preceded repair execution, but independent blindness was not preserved because the synthetic fixture was intentionally constructed to test transfer from TR-04. The fixture is current within this batch, not a fresh external defect.
- **External value/acceptance:** this is direct evidence of mechanism-level transfer, but external-user value is only prospective. No external repository or maintainer accepted it.
- **Legal/privacy:** AEG MIT-0 fixture and Apache-2.0 Tornado reference; synthetic, credential-free evidence.
- **Promotion limit:** synthetic target, no independent discovery, baseline arm, external contribution, or upstream acceptance.

### 04 — Documentation example doctor

- **Classification:** historical/non-blind replay.
- **Objective verification:** executable output agreement improved from 3/5 to 5/5 and `git diff --check` passed.
- **Retrieval and effect:** AEG was queried before execution and abstained (best 0.0217). Nothing was reused and retrieval did not change the repair.
- **Blindness/currentness:** blindness was not preserved because Pendulum PR #920 disclosed the defect and repair. Current main still reproduced during the run, but an active correct PR already owned the contribution path.
- **External value/acceptance:** users benefit from correct examples; the local replay confirms the public patch. The PR remained open, so upstream acceptance was absent.
- **Legal/privacy:** MIT public source; no private or raw conversation data.
- **Promotion limit:** disclosed repair, duplicate-work constraint, no docs-site build, and no maintainer acceptance.

### 05 — Agent skill/MCP compatibility

- **Classification:** partial.
- **Objective verification:** protocol handshake, 14-tool discovery, exact allowed-file read, and explicit outside-root denial passed. The package omitted the LICENSE file named by `package.json`; SIGINT ended with exit 1 and no graceful zero-exit shutdown was observed.
- **Retrieval and effect:** AEG was queried only after execution. The abstention is post hoc; retrieval-timing and retrieval-effect evidence are invalid/procedurally contaminated. The execution outcome is preserved and the task was not rerun.
- **Blindness/currentness:** the package version and integrity were frozen before probing; repair blindness is not applicable because this was a compatibility card, not a repair. Version 2026.7.10 was current for the run, but package and repository licensing were transitional.
- **External value/acceptance:** users gain a scoped permission/compatibility warning and a concrete packaging defect. No maintainer confirmation, issue, PR, or release acceptance exists.
- **Legal/privacy:** public package and repository; disposable `/tmp` root only; no credentials or external/private data; no write/destructive tools invoked. Legal status is incomplete because the distributed package lacks its declared license file.
- **Promotion limit:** invalid retrieval timing, partial license evidence, incomplete shutdown behavior, and narrow platform/capability coverage.

### 06 — Public-data ETL/quality

- **Classification:** locally verified but awaiting external evidence.
- **Objective verification:** an unfiltered response failed on a real explosion; the filtered pipeline produced 100 unique UTC-normalized rows twice with an identical SHA-256 digest.
- **Retrieval and effect:** AEG was queried only after execution. Its abstention and any claimed retrieval effect are invalid/procedurally contaminated. The independent ETL result remains passed and was not rerun.
- **Blindness/currentness:** transformation logic was developed from the frozen response, so repair blindness is limited. Historical USGS records can be revised; full response digests freeze the observed bytes but not future URL content.
- **External value/acceptance:** the quality oracle is useful for public FDSN ingestion, but no maintained external project incorporated it and no upstream acceptance exists.
- **Legal/privacy:** USGS-produced data are public domain with attribution; raw rows, coordinates, and place strings stayed in `/tmp`; the repository keeps aggregates and digests only.
- **Promotion limit:** late retrieval, revisable source, one small window, no contribution path, and commit-shaped schema fields holding disclosed digest prefixes rather than VCS commits.

### 07 — AEG self-maintenance

- **Classification:** locally verified but awaiting external evidence.
- **Objective verification:** the old false pass on a nonexistent evidence file was reproduced; focused tests, the full relevant Python suite, schema/result validators, and extension tests passed after repair.
- **Retrieval and effect:** AEG was queried before repair and abstained (best 0.0171). No experience was reused and the repair path did not change because of retrieval.
- **Blindness/currentness:** blindness was preserved for diagnosis—the false positive was reproduced before the fix was implemented. The source was current at frozen base `e7ab21f` for this batch.
- **External value/acceptance:** users benefit because canonical promoted evidence must resolve to repository files. The repair is local only; hosted CI, code review, merge, and release acceptance do not yet exist.
- **Legal/privacy:** AEG MIT-0 public source; no candidate promotion, credentials, proprietary material, or raw conversation evidence.
- **Promotion limit:** no external review/upstream acceptance; file existence alone does not establish evidence truth or freshness.

## Aggregate evidence

- **Tasks attempted:** 7.
- **Promotion classes:** 0 promotion-ready verified experiences; 3 locally verified but awaiting external evidence (03, 06, 07); 3 historical/non-blind replays (01, 02, 04); 1 partial (05); 0 blocked; 0 invalid for reuse.
- **Execution-state outcomes:** 5 completed and 2 partial. These operational outcomes are distinct from the stricter promotion classes above.
- **Correct abstentions:** 4 procedurally valid pre-execution abstentions (01, 02, 04, 07). Six abstentions were observed in total, but the two post-execution abstentions (05, 06) do not count as valid retrieval evidence.
- **Recommendations:** 1 valid above-threshold recommendation (TR-04 for 03).
- **Valid pre-execution retrievals:** 5 (01, 02, 03, 04, 07).
- **Invalid late retrievals:** 2 (05, 06).
- **Experiences reused:** 1 existing experience (TR-04). Three new candidates show the strongest future reuse potential after more evidence: 03, 06, and 07.
- **Commands/tests/time/tokens:** 113 completed commands; 608 reported unit-test or focused-oracle executions; 8h16m43s batch wall time. These are heterogeneous counts, not normalized efficiency measures. Reliable token and cost data were unavailable (`null`).
- **External patches potentially worth contributing:** Category 07's validator repair is the strongest ready-for-review patch. Category 04 may justify a non-duplicative validation note on existing PR #920, and Category 05 may justify a packaging-license issue, but both require approval. Categories 01 and 02 are already repaired upstream; 03 is synthetic; 06 is a local pipeline rather than an upstream patch.
- **Candidates that should remain candidates:** all seven. None belongs in `experiences/verified.json` on present evidence.

## Repository-hygiene conclusion

The review branches must contain no tracked `/tmp` path or external source tree. Batch evidence consists only of project specifications, manifests, candidate JSON, sanitized Markdown summaries, execution state/results, and this report. No credentials, raw conversations, raw JSONL, full command logs, private filesystem paths, raw public-data rows, or proprietary material are permitted. Every external source used by the batch records public provenance and an explicit license/public-domain status. Candidate records remain under `dogfood/self-consumption-batch-01/candidates/`, separate from `experiences/verified.json`.

## Batch 02 recommendation — do not execute yet

Run only one primary family and, if capacity remains, one secondary family:

1. **Primary: independently discovered public contract/regression-test gaps.** This preserves the strongest signal from Category 03 while replacing its synthetic target with a fresh external project. The family has cheap fail-before/pass-after oracles, repeats across wrapper/proxy/delegation projects, and can produce small upstream tests and fixes.
2. **Secondary: executable documentation/API examples with no active repair.** Category 04 demonstrated immediate user value and inexpensive objective output checks. Select only fresh cases with an unclaimed contribution path; do not replay Pendulum #920.

Every Batch 02 task must satisfy all eight gates before execution:

1. Check source freshness.
2. Confirm the defect is not already repaired on main.
3. Confirm there is no active correct PR.
4. Freeze the task before inspecting any fix.
5. Query AEG before diagnosis.
6. Record objective pre/post verification.
7. Confirm an external contribution path.
8. Record the candidate experience honestly, including abstention, contamination, and negative evidence.

Do not run paid A/B arms, publish experiences, push branches, create PRs, or start Batch 02 without separate approval.
