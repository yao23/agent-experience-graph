# Autonomous Lab scheduler activation readiness

## Decision

- Scheduler infrastructure: **ready for review**.
- Scheduler itself: **not enabled**.
- Commercial experiment: **proposed and not approved**.
- Batch 03: **not started**.

## Readiness answers

- Is PR #18 merged and green? **Yes.** It merged as
  `b5bd6cc5fb42e06f486bbb0f15466ea9adc03ee0`; post-merge Autonomous Lab CI run
  `31238447525` passed.
- Are shakedown fixtures excluded from live selection? **Yes.** The completed
  recovery fixture is archived; the intentionally escalated external-action
  regression fixture is archived. Both have `scheduler_eligible: false`.
- Is concurrency protected? **Yes within one Git common directory.** Atomic
  lease creation rejects concurrent worktree runners and stale leases require
  explicit recovery. Independent clones are not mutually locked.
- Is working-tree safety enforced? **Yes.** Repository, branch, Git operation,
  expected tracked mutations, untracked Autonomous Lab content, verified
  library, state, and ledger are checked fail-closed.
- Is there a scheduler-eligible experiment? **No.** The safe no-work result is
  `No scheduler-eligible experiment is currently approved.`
- Is the commercial experiment proposed and unapproved? **Yes.** It is not
  silently activated and remains at zero execution budget.
- What prompt should be pasted into Scheduled Tasks? Use the complete contents
  of `autonomous-lab/prompts/scheduled-step.md`.
- What local project should be selected? Select the local AEG repository root
  that contains `autonomous-lab/`, on the allowed `main` branch.
- What cadence is recommended? At most once per hour initially; inspect the
  first several runs before changing it.
- What events require pausing? Exit codes `10`, `11`, `12`, `13`, `14`, and
  `15`, plus any unexpected report or working-tree change.

## Activation prerequisites still outstanding

1. Review and merge the scheduler-readiness pull request.
2. Separately approve one bounded non-commercial experiment and mark exactly
   one registry entry active and scheduler-eligible.
3. Reconfirm local branch, clean/expected working-tree state, no secrets, and
   no competing independent clone.
4. Test the saved prompt manually in the selected local project.
5. Create the scheduled task only after explicit human authorization.

This record does not authorize task creation, commercial execution, network
access, model execution, external writes, promotion, publication, release, or
verified-library modification.
