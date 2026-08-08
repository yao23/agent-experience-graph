# Continue an autonomous-lab experiment

This prompt supports either a human-launched Codex run or a future scheduled or
GitHub-triggered run. Work only from repository records; prior chat transcripts
and screenshots are never authoritative state.

1. Read `autonomous-lab/AGENTS.md`, every strategy and decision-rule document,
   the experiment registry, current goal, state, scorecard, complete ledger, and
   latest reports.
2. Run `lab.py validate`, `status`, and `next`.
3. Confirm the ledger head, budget, approvals, evidence, objective oracle, and
   exactly one permitted milestone. Never inspect a treatment outcome before
   preregistration is frozen.
4. Execute only within the recorded budget and authority.
5. Run or consume the objective evaluator; narrative judgment is not success
   when acceptance tests or market evidence are absent.
6. Record sanitized evidence and all budget consumption.

The single continuation entry point is:

```sh
python3 autonomous-lab/scripts/lab.py run-one-step
```

It validates, chooses at most one action, persists state and evidence,
regenerates reports, and exits. Interpret exit codes as follows:

- `0`: one safe step completed or terminal state is stable;
- `10`: human approval is required;
- `11`: validation, evidence, schema, or oracle failure;
- `12`: budget exhausted.

Perform at most one transition and continue only when the state machine
explicitly permits it. Do not continue from a terminal state. Do not
execute an approval-gated or forbidden action. If evidence is missing, a budget
or retry limit is reached, contamination is possible, the oracle is absent, or
approval is pending, stop and create/update the machine-readable escalation and
human report. Append a hash-chained event; never replace an old event. Validate
again and report exactly what changed.

When exit code `10` is returned, read
`autonomous-lab/reports/next-human-action.md` and stop. Do not infer approval
from silence, chat history, or a local substitute action.
