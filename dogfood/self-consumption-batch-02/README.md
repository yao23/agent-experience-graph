# AEG Self-Consumption Batch 02 preregistration

Preregistered at 2026-08-07T16:08:00Z, before candidate selection or repair diagnosis. Batch 02 is a sequential, blind self-consumption experiment on fresh public software defects. Its purpose is trustworthy evidence about whether a pre-execution AEG query helps with real current work, not maximizing completions.

## Hypothesis

For a fresh, objectively reproducible public contract or regression-test gap, querying AEG after freezing the failing oracle but before diagnosis may supply a reusable lesson that materially improves the diagnosis, command sequence, test design, repair path, or final patch without weakening correctness. A correct abstention is useful calibration. A recommendation that does not change execution, a late query, or a non-blind replay does not support the hypothesis. This single-arm batch cannot by itself establish causal improvement, generalized effectiveness, or product-market fit.

## Task family and sample

- Select up to exactly three tasks from fresh public contract or regression-test gaps in open-source repositories.
- Use an executable documentation/API-example task only if fewer than three primary-family tasks pass every gate.
- Do not reuse any Batch 01 target.
- Do not lower a gate to obtain three tasks. Stop with the qualified number if the eligible pool is exhausted.

## Inclusion criteria

A task is eligible only when all ten conditions are recorded before diagnosis:

1. The repository has an explicit open-source license.
2. The issue or defect is current and publicly accessible.
3. The default branch still contains the defect.
4. No correct active PR already fixes it.
5. No inspected issue comment, commit, test, discussion, or other material disclosed the repair.
6. A deterministic failing test or equivalent objective oracle exists or can be created without knowing the repair.
7. The task is small enough for an isolated repair within the task budget.
8. The project documents or demonstrably supports a legitimate contribution path.
9. The pre-fix default-branch commit SHA is frozen.
10. The isolated working tree, task statement, and oracle are frozen before repair investigation.

## Exclusion criteria

Reject a task when any inclusion criterion is unverified; the issue is stale, ambiguous, subjective, security-sensitive, destructive, credentialed, private, proprietary, or already repaired; the likely change is too broad; the license or contribution path is unclear; the oracle depends on a hosted secret or flaky service; or maintaining blindness would require ignoring already observed repair information. Every rejection is appended to `selection-ledger.md`.

## Freshness and blindness

- Freshness requires a current default-branch SHA plus a reproduction on that SHA, a public issue/defect state check, and a search showing no active correct repair PR.
- Before retrieval, inspection is limited to selection metadata, license/contribution policy, dependency setup, the public task statement, and the minimum surface necessary to construct and run the oracle.
- Do not inspect repair commits, patches, linked fix diffs, root-cause discussions, repair-oriented tests, or implementation paths beyond what the oracle requires.
- Freeze and hash the task manifest and oracle before diagnosis. Work only in an isolated checkout.
- If repair information is observed or diagnosis begins before retrieval, classify the task as contaminated and stop that task without claiming retrieval benefit.

## Retrieval timing and classification

For every selected task: record the frozen task and pre-fix SHA, run the failing oracle, then query `experiences/verified.json` before root-cause analysis or repair-oriented source inspection. Preserve the exact query, UTC timestamp, threshold, retrieved ID, score, evidence, capsule, and abstention state. Immediately and immutably classify retrieval as one of: recommended experience, below-threshold near match, correct abstention, incorrect recommendation, or procedurally contaminated.

After execution, separately record whether retrieval changed diagnosis, commands, test design, repair path, or the patch. Do not revise the retrieval classification based on task success.

## Objective oracle

Each task must have a deterministic, credential-free oracle that fails at the frozen pre-fix SHA for the stated contract and can pass after a defensible repair. Prefer an existing focused test; otherwise add the smallest black-box regression test without reading the repair. Record the exact command, failure signal, relevant environment, and frozen oracle hash. Verification requires the focused fail-before/pass-after oracle plus relevant non-regression tests. A subjective output review is insufficient.

## Outcome definitions

- **Success:** the frozen oracle fails before and passes after the smallest defensible patch, relevant regression tests pass, and no scoped regression is found.
- **Partial:** useful bounded work or some verification succeeds, but the repair, oracle coverage, relevant regression suite, provenance, or contribution readiness remains incomplete.
- **Abstention:** AEG returns no record at or above the frozen threshold; classify it as correct only if no applicable verified experience was reasonably available from the frozen library and do not claim repair benefit.
- **Contamination:** retrieval occurred after diagnosis, repair information was observed before completion, blindness was lost, the task/oracle changed to favor a result, or another procedure violation could affect retrieval-effect interpretation.
- **Failure:** the attempted repair does not satisfy the oracle or introduces a verified scoped regression within budget.
- **Blocked:** a prerequisite outside the experiment—environment, dependency, licensing, contribution path, or reliable oracle—prevents meaningful execution within budget.

Final experience classification is exactly one of: promotion-ready verified experience; locally verified awaiting external evidence; historical/non-blind replay; partial; blocked; invalid for reuse.

## Candidate-promotion requirements

Promotion-ready requires all of: a fresh real-world task; valid pre-execution retrieval; preserved blindness; objective failing and passing oracle; verified repair; immutable current provenance; a reusable non-patch-specific lesson; privacy and license clearance; external maintainer acceptance or equivalent independent evidence; and no unresolved contamination. Schema validity alone is insufficient. No candidate may be added to `experiences/verified.json` without explicit user approval.

## External-contribution requirements

A contribution-ready result must have an explicit upstream path, a minimal patch, project-format tests, license compatibility, a sanitized message, and no competing active correct repair. Prepare patches and messages locally only. Forking, pushing, opening or commenting on issues/PRs, contacting maintainers, publishing, and candidate promotion require separate approval naming the action and target.

## Stop conditions

Stop the task immediately if blindness cannot be preserved; the defect is no longer current; an active correct repair appears; the oracle is subjective, flaky, or unreliable; license or contribution status is unclear; AEG was queried too late; secrets, private code, destructive actions, or proprietary material are required; or the task budget is exhausted. Stop selection when the qualified pool is exhausted. Stop the batch before every external write, verified-library change, release, promotion, paid benchmark, or Batch 03.

## Fixed budgets

- Candidate screening: at most 24 candidates and 2 hours total.
- Selected sample: at most 3 tasks; no replacement after diagnosis begins unless the task is immediately classified contaminated or blocked.
- Per selected task: at most 90 minutes execution time, 30 shell commands after selection, 4 changed source/test files, and one isolated checkout.
- Verification: focused oracle plus relevant tests; stop any single test command at 20 minutes unless a shorter project-specific limit applies.
- Batch execution: at most 4.5 hours across selected tasks and 6.5 hours including screening/recording.
- Compute: one sequential agent execution only; no paid multi-arm or model benchmark, no artificial failure, no task duplication for favorable evidence.
- Record elapsed time, completed commands, test/oracle executions, and available token/model usage. Use `null` with an explanation when reliable usage is unavailable.

## Recording rules

`selection-ledger.md` and `execution-results.md` are append-only. Raw repositories, patches, full logs, raw conversations, personal paths, and credentials remain outside this repository. Store sanitized manifests, aggregate evidence, candidates, state, and the final decision only. Record product defects separately rather than adapting the experiment around them.
