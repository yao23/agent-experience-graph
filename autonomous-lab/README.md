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

`evaluate` remains available for experiments that supply acceptance-result
files explicitly. The deterministic shakedown uses the same evaluator logic
inside one-step continuation so every process still makes one transition.

## Current contents

The registry preserves Batch 01 and corrected Batch 02 as historical evidence,
without promoting any candidate. The commercial “AEG-assisted Agent Failure
Recovery Service” remains unchanged in `proposed` with zero budget consumed.

Two local shakedown records prove control-plane behavior only:

- `repository-state-recovery-01` completed the full lifecycle by transforming
  an invalid tracked fixture into a schema-valid normalized artifact;
- `external-action-escalation-01` refused an inert external-write request and
  stopped at an open human escalation.

Neither record is AEG effectiveness, coding-agent intelligence, external-user,
commercial-demand, generalized-effectiveness, or PMF evidence.

## Stateless continuation

An independent Codex run needs no screenshot or prior conversation. From a
clean checkout, read `AGENTS.md` and
`prompts/continue-experiment.md`, then run exactly:

```sh
python3 autonomous-lab/scripts/lab.py run-one-step
```
