# AEG Autonomous Experiment Lab v0

This directory is a GitHub-backed control plane for bounded, reviewable AEG
experiments. It records goals, state, evidence, budgets, scorecards, approval
gates, and append-only transitions. It does not run models, spend money,
publish experiences, or write to external projects.

The v0 design is deliberately fail-closed:

- an experiment cannot skip a lifecycle stage;
- execution cannot begin before preregistration and readiness evidence exist;
- evaluation requires an objective oracle and recorded acceptance results;
- terminal experiments cannot continue;
- approval-gated actions cannot run without explicit recorded approval;
- each state transition must append a hash-chained ledger event;
- budget exhaustion, repeated failure, contamination, and missing evidence stop
  autonomous continuation and produce an escalation.

## Lifecycle

`proposed -> screening -> preregistered -> ready -> running -> evaluating -> completed`

Interrupt or terminal states are `rejected`, `blocked`, `budget_exhausted`,
`contaminated`, `escalated`, and `cancelled`. `completed` is also terminal.

## Local commands

Install the small validation dependencies and run the same checks as CI:

```sh
python3 -m pip install -r autonomous-lab/requirements.txt
python3 autonomous-lab/scripts/lab.py validate
python3 autonomous-lab/scripts/lab.py status
python3 autonomous-lab/scripts/lab.py next
python3 autonomous-lab/scripts/lab.py run-one-step
python3 autonomous-lab/scripts/lab.py scheduled-step
python3 autonomous-lab/scripts/lab.py report
python3 -m unittest discover -s autonomous-lab/scripts/tests -p 'test_*.py'
git diff --check
```

`run-one-step` validates first, reconstructs the active experiment only from
tracked files, performs no more than one safe transition, persists evidence,
regenerates reports, and exits. It never loops or performs an approval-gated
action.

Exit codes are stable:

- `0`: one safe step completed, or a completed/terminal experiment was already
  stable;
- `10`: human approval is required and no gated action was performed;
- `11`: validation, schema, evidence, or oracle failure;
- `12`: execution budget is exhausted.
- `13`: another execution lease is held, or a stale lease requires explicit
  recovery;
- `14`: repository identity, branch, Git operation, working-tree content, or
  verified-library state is unsafe;
- `15`: scheduler configuration or experiment selection is invalid.

`scheduled-step` is the unattended, local-project entry point. It locates and
verifies the repository, selects at most one explicitly active and eligible
experiment, acquires an atomic lease shared by Git worktrees, performs the
working-tree preflight, validates, executes at most one transition, regenerates
notification-friendly reports, and releases the lease. It never loops.

The checked-in registry contains exactly one scheduler-eligible experiment:
the bounded, repository-local `phase0_preparation` stage of the Agent Failure
Recovery Service. The complete commercial experiment and Phase 1 remain
unapproved. When Phase 0 completes, the controller disables scheduling and
reports exit code `10` with the next human decision.

The completed recovery shakedown is archived. The synthetic external-action
escalation remains immutable regression evidence and is also archived, so its
unresolved synthetic approval is not live work.

If `scheduled-step` reports a stale lease, inspect it and use the explicit
recovery command only after its expiration:

```sh
python3 autonomous-lab/scripts/lab.py recover-stale-lease
```

Never remove a lease manually or break a non-expired lease. See
[`scheduler/operations.md`](scheduler/operations.md) before creating any
desktop scheduled task.

`evaluate` remains available for experiments that supply acceptance-result
files explicitly. The deterministic shakedown uses the same evaluator logic
inside one-step continuation so every process still makes one transition.

## Current contents

The registry preserves Batch 01 and corrected Batch 02 as historical evidence,
without promoting any candidate. The commercial “AEG-assisted Agent Failure
Recovery Service” is preregistered only for approved Phase 0 package preparation
with zero budget consumed at activation.

Two local shakedown records prove control-plane behavior only:

- `repository-state-recovery-01` completed the full lifecycle by transforming
  an invalid tracked fixture into a schema-valid normalized artifact;
- `external-action-escalation-01` refused an inert external-write request and
  stopped at an open human escalation.

Neither record is AEG effectiveness, coding-agent intelligence, external-user,
commercial-demand, generalized-effectiveness, or PMF evidence.

## Stateless continuation

An independent run needs no screenshot or prior conversation. From a
clean checkout, read `AGENTS.md` and
`prompts/continue-experiment.md`, then run exactly:

```sh
python3 autonomous-lab/scripts/lab.py run-one-step
```

For a future scheduled run, use the standalone prompt in
[`prompts/scheduled-step.md`](prompts/scheduled-step.md). Preparing that prompt
does not create or enable a scheduled task.
