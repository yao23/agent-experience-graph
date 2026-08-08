# Autonomous Lab scheduler activation readiness

## Decision

- Scheduler infrastructure: **ready for review**.
- Scheduler itself: **not enabled**.
- Commercial experiment: **Phase 0 preparation only is approved and
  preregistered**; the complete commercial experiment and Phase 1 are not.
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
  clean starting state, exact post-transition allowlist, local persistence
  commit, verified library, state, and ledger are checked fail-closed.
- Is there a scheduler-eligible experiment? **Yes.** Exactly one bounded,
  repository-local `phase0_preparation` entry is eligible.
- Is the commercial experiment fully approved? **No.** Only Phase 0 package
  preparation is authorized; Phase 1 and all external actions remain blocked.
- What prompt should be pasted into Scheduled Tasks? Use the complete contents
  of `autonomous-lab/prompts/scheduled-step.md`.
- What local project should be selected? Select the local AEG repository root
  that contains `autonomous-lab/`, on the allowed `main` branch.
- What cadence is recommended? At most once per hour initially; inspect the
  first several runs before changing it.
- What events require pausing? Exit codes `10`, `11`, `12`, `13`, `14`, and
  `15`, plus any unexpected report or working-tree change.

## Scheduled Task prerequisites still outstanding

1. Review and merge the scheduler-persistence repair pull request.
2. Reconfirm local `main`, clean working-tree state, no secrets, and
   no competing independent clone.
3. Test the saved prompt manually in the selected local project without
   executing the real Phase 0 transition.
4. Create the scheduled task only after explicit human authorization.

This record does not authorize task creation, commercial execution, network
access, model execution, external writes, promotion, publication, release, or
verified-library modification.
