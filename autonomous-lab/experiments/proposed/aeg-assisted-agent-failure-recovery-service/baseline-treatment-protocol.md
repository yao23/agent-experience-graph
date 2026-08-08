# Future baseline/treatment protocol

Design only. No baseline or treatment repair arm may run in Phase 0.

## Unit and assignment

Use only fresh, qualified tasks with a frozen source, oracle, privacy/license
status, contribution path, and budget. Create separate blind executions:

- Baseline: AEG retrieval disabled.
- Treatment: AEG queried before diagnosis; only relevant verified experiences
  may be used.

Freeze assignment and task material before either execution. Prevent cross-arm
chat, worktree, patch, log, or diagnosis leakage. Record abstention as a valid
treatment result, not forced reuse.

## Measures

- Task and first-pass success.
- Commands, retries, model calls, input/output tokens when available.
- Wall-clock time and human intervention count/minutes.
- Frozen-oracle repair outcome and unrelated regressions.
- Customer and maintainer acceptance.
- Repeat usage, willingness to pay, first revenue.
- Improvement between delivery 1 and delivery N.

## Phase 1 entry gates

- Every Phase 0 artifact passes review.
- Privacy/IP and rejection boundaries are approved.
- Objective repair acceptance tests exist.
- Intake can reject proprietary or unsuitable tasks.
- External-contact wording and a separate budget are approved.
- Explicit outreach authorization is recorded.
- Freshness discovery includes fork/closed PRs, backlinks, commits, global
  search, contributor branches, and recent default-branch changes.

Retrospective comparisons, historical replays, late retrieval, or non-fresh
tasks cannot support a causal AEG benefit claim.
