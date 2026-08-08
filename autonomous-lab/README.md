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
python3 autonomous-lab/scripts/lab.py report
python3 -m unittest discover -s autonomous-lab/scripts/tests -p 'test_*.py'
git diff --check
```

`run-one-step` is optional and performs no more than one transition. It refuses
the current proposed commercial experiment because human approval is required
before screening. `evaluate` similarly refuses unless the experiment is in
`evaluating` with an objective oracle and acceptance-test results.

## Current contents

The registry preserves Batch 01 and corrected Batch 02 as historical evidence,
without promoting any candidate. The only proposed experiment is
“AEG-assisted Agent Failure Recovery Service.” It is a preregistered design
artifact in `proposed` state, not an authorized or running experiment.
