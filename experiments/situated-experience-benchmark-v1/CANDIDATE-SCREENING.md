# Candidate screening contract

Screening is completed and frozen before any arm output exists. Every inspected
candidate is recorded in `candidate-screening.json`, including rejections. A
candidate cannot be revived after outcomes are observed; it must enter a future
manifest revision with a new benchmark ID.

All families require public provenance or an explicitly authorized private
corpus, a reproducible failing state, an objective evaluator, a bounded license
and privacy review, a source experience that predates the transfer task, and a
credible reason that situated knowledge could alter the repair path. Exclude
tasks whose answer is present in the prompt, whose human patch is reachable by
the agent, whose evaluator cannot distinguish a plausible false positive, or
whose environment cannot be staged before execution.

## S1 dependency and version migration

Accept only natural dependency, runtime, protocol, or metadata-representation
migrations with a version-locked pre-migration failure, a known human fix, and
visible plus controller-only regression coverage. Source and transfer must
share a migration invariant but differ in symptom and production patch. The
source fix must predate the transfer fix. Reject pure version-string bumps,
tasks requiring unstaged network downloads, tasks whose only oracle is static
syntax, and pairs whose compact experience would reveal the transfer patch.

## S2 CI and deployment failures

Require a reproducible failing job or deployment stage, a frozen runner image
and matrix, sanitized logs, and an evaluator that can rerun the relevant job in
the same substrate. Source and transfer must share an environmental or pipeline
failure invariant without sharing the same workflow edit. Reject provider-only
failures that cannot be replayed, secret-dependent tasks without an approved
broker, and green local substitutes for a failing hosted job.

## S3 cross-module regressions

Require a change in one module with an objectively failing consumer in at least
one other module. The hidden suite must exercise consequences beyond the
obvious edit site. Source experience must encode ownership or contract evidence,
not a filename. Reject single-file failures, tasks with no downstream oracle,
and tasks where the prompt names every affected module.

## S4 Planner-Coder-Tester-Reviewer collaboration

Require four independently logged roles, fixed handoff artifacts, bounded role
budgets, and evaluators for plan fidelity, patch correctness, test adequacy, and
review finding quality. Source experience may affect handoff content but cannot
contain role-specific answers. Reject tasks solvable without a handoff, roles
that share hidden state, and workflows where reviewer findings reach earlier
roles before their artifacts freeze.

## S5 misleading repairs and repeated failure paths

Require at least one historically plausible repair that passes a weak check but
fails a stronger registered oracle. Freeze detectors for repeated failed paths
before execution. Source experience must provide invalidating evidence and a
recovery principle, not the correct patch. Reject manufactured traps with no
public or recorded history and tasks whose false path is disclosed verbatim in
the task prompt.

## S6 experience invalidation under environment drift

Require paired environments where a once-valid experience becomes inapplicable
because of a frozen dependency, runtime, platform, or configuration change. The
correct treatment behavior must include rejection or abstention. Reject drift
that also changes the task oracle, environments that cannot be reconstructed,
and cases where the new environment merely repeats S1's original migration.

S2-S6 are screening rules only in v1. They have no accepted tasks, fixtures, or
execution authorization.
