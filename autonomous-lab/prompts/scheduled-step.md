# Autonomous Lab scheduled-step prompt

Work only in the selected local AEG repository. Treat tracked repository files
as the sole authoritative experiment state. Do not rely on a prior scheduled
run, chat history, screenshots, hidden session state, shell variables, caches,
or process memory.

Before taking any action:

1. Locate the repository root and read `autonomous-lab/AGENTS.md`.
2. Read `autonomous-lab/strategy/product-strategy.md`,
   `autonomous-lab/strategy/experiment-policy.md`, and
   `autonomous-lab/strategy/approval-and-stop-policy.md`.
3. Read `autonomous-lab/experiments/registry.yaml`,
   `autonomous-lab/reports/current-status.md`,
   `autonomous-lab/reports/next-human-action.md`, and
   `autonomous-lab/ledger/events.jsonl`.
4. If exactly one scheduler-eligible experiment exists, read its `goal.yaml`,
   `state.json`, `scorecard.json`, escalation record, referenced evidence, and
   any hash-linked approval record. For the failure-recovery service, the only
   active authorization is `phase0_preparation`; Phase 1 remains blocked.
5. Run `python3 autonomous-lab/scripts/lab.py validate` before mutation.

Then execute exactly once:

```sh
python3 autonomous-lab/scripts/lab.py scheduled-step --persist-commit
```

Do not loop or retry. Obey the result code:

- `0`: report the one safe transition, terminal stability, or absence of
  eligible work.
- `10`: stop; a human approval is required.
- `11`: stop; validation or evidence failed.
- `12`: stop; the experiment budget is exhausted.
- `13`: stop; a lease is held or stale and requires reviewed recovery.
- `14`: stop; the repository or working tree is unsafe.
- `15`: stop; scheduler configuration or selection is invalid.

Never enable an experiment because it is merely proposed. Never perform or
authorize an external write, candidate promotion, verified-library change,
release, secret use, payment, recruitment, user contact, offer publication,
commercial action, model call, or network action without explicit recorded
approval for that exact action. Never clean, reset, stash, discard, or overwrite
user work. Never substitute a local action for an approval-gated action.
Do not run `git add`, `git commit`, `git push`, `git reset`, `git stash`, or
`git clean` yourself. The `--persist-commit` controller may create one local,
un-pushed commit containing only its validated transition outputs. Any other
changed path must fail closed with exit code `14`.

After a successful safe step, confirm the command regenerated
`autonomous-lab/reports/current-status.md`, `current-status.json`, and
`next-human-action.md`, created exactly one allowlisted local commit, left the
worktree clean, and did not push it. Summarize only the transition, objective
evidence, persistence commit, budget consumed and remaining, exit code, and
next permitted action. Do not ask for screenshots or conversational
reconstruction.
