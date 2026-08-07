# Batch 02 decision

Decision pending. Do not infer effectiveness, promotion readiness, or product-market fit from preregistration or selection alone. This file will be completed only after all eligible selected tasks reach a terminal classification.

## Decision

Batch 02 stopped after one selected task because the preregistered 24-candidate screening cap was exhausted. Twenty-three candidates failed strict blindness, active-repair, oracle, or scope gates; gates were not lowered and discarded over-cap search results were not used.

- **Technical feasibility:** supported for one fresh Click defect. The frozen oracle failed on current default-branch source, passed after a two-file local repair, and relevant plus full tests passed.
- **Retrieval usefulness:** no positive reuse evidence. AEG was queried at the valid preregistered time and correctly abstained; no prior experience changed execution.
- **Correct abstention:** one. The best below-threshold score was 0.0179 and did not identify an applicable progress-finalization lesson.
- **Contaminated or non-blind results:** zero selected executions. Strict screening rejected disclosures before selection rather than relabeling them after work.
- **Locally verified awaiting external evidence:** one, Category 01.
- **Historical/non-blind replays:** zero.
- **Promotion-ready verified experiences:** zero. The candidate was not added to `experiences/verified.json`.
- **External evidence:** absent. The local Click commit was not pushed, no PR or comment was created, and no maintainer acceptance exists.
- **PMF/generalization:** unsupported. One successful local repair with a correct retrieval abstention does not establish retrieval benefit, generalized effectiveness, causal efficiency, or product-market fit.
- **Hypothesis evidence:** the batch supports procedural feasibility and calibrated abstention, but supplies no affirmative evidence that retrieval helps solve the repair because no experience was recommended or reused. It neither measures nor demonstrates a correctness, speed, cost, or success-rate improvement.
- **Computation:** 24 candidates screened; one selected task used 18 recorded shell commands and 6 oracle/pytest executions through local repair completion. Token/model and cost usage were not exposed. The UTC observation span from preregistration through final validation was 4h07m53s; active compute time was not independently metered.

## Next decision requiring approval

The only plausible external-value action is to recheck Click issue/PR freshness and, if still clear, prepare or submit the existing two-file patch through Click's documented contribution process. Pushing, opening a PR, or commenting upstream remains prohibited without explicit approval. No candidate should be promoted unless external acceptance and independent evidence are later recorded. Batch 03 must not begin without approval.

## Recommended next experiment — do not start

Before another execution batch, improve candidate discovery rather than expanding the repair budget: preregister a search that treats repair-heavy issue bodies as immediate exclusions, separates returned-but-unscreened results from the screening cap, and targets repositories with deterministic local test harnesses and sparse active-PR queues. Then run a small fresh sample only when at least one verified AEG record produces a genuinely task-specific above-threshold recommendation; otherwise continue measuring abstention quality. A controlled causal claim would require a separately approved baseline design, not retrospective comparison with this run.

## Post-Batch-02 superseding correction — 2026-08-07T20:50:28Z

The original decision incorrectly counted one qualified task. A manual audit, independently verified against GitHub issue timelines, global search, fork PR metadata, closed upstream PR metadata, commits, and patches, found multiple public repairs predating selection. The original active-upstream-only search was not an adequate freshness or contribution-availability gate.

Corrected decision:

- candidates screened: 24;
- qualified under the preregistered gates: 0;
- incorrectly accepted during initial screening: 1;
- rejected under the corrected gate: 24;
- fresh eligible executions: 0;
- independent local reproductions: 1;
- correct AEG abstentions: 1 only as library-query calibration, not fresh-task effectiveness evidence;
- historical/non-blind executions: 0, because the executing agent did not inspect prior repair material;
- promotion-ready candidates: 0.

The Click work is best classified as **independent local reproduction, invalid for fresh-task qualification**. Agent blindness and patch process independence are supported, but public freshness, novelty, contribution availability, external value, and promotion readiness are not. Its material convergence with earlier public patches reinforces the technical diagnosis but provides no affirmative evidence that AEG retrieval helped. Batch 02 therefore supplies no eligible fresh-task test of its primary hypothesis and cannot support generalized-effectiveness or PMF claims.
