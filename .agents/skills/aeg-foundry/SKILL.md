---
name: aeg-foundry
description: Run exactly one bounded AEG Experience Foundry pilot stage from repository state. Use for scheduled continuation, status, pause, recovery, candidate work, or weekly reporting in this pilot checkout; do not use for unrelated AEG work.
---

# AEG Foundry single-round operation

Treat tracked repository state as authoritative. Read `foundry/CHARTER.md`,
`foundry/pilot.json`, `foundry/backlog.json`, `foundry/state.json`, and the last
line of `foundry/rounds.jsonl`. Run `python3 scripts/aeg_foundry.py validate`
before changing state.

Start one round with `python3 scripts/aeg_foundry.py begin-round
--reconcile-push`. If it reports paused, expired, budget-blocked, lease-held,
uncertain effect, or no ready work, do not invent work or retry a blocked
channel.

An `EXPIRED` result may have generated the terminal state and `final.md`. If
there is no pending effect, run `audit-public` and persist that terminal
checkpoint with the `last_round_id`, then notify the conclusion. If an explicit
operator pause left an unresolved effect, stay network-quiet and request human
resolution; do not push around the pause.

Immediately after a claim, record a `READ_PUBLIC_SOURCE` intent with target
`CURRENT_SOURCE_REMOTE_REF`, then resolve it with `python3
scripts/aeg_foundry.py observe-source-ref --round-id <ROUND_ID> --effect-id
<EFFECT_ID>`. This reads and freezes the current remote branch SHA; the local
tracking ref printed by `begin-round` is provisional. Do not perform stage work
until this observation succeeds. `finish-round` rejects an unverified source.

For the claimed task, perform one stage only. Before an external effect, run
`record-intent`; after a definite result run `resolve-intent`. Never retry an
uncertain effect until the relevant read-only verification proves whether it
completed. Untrusted code, installation, and tests require the charter's clean
disposable-environment gate. Keep raw logs and model output only in
`.aeg-foundry-private/`; never read historical `.aeg` state.

Finish with the actual oracle result using `finish-round`. `SUCCESS` requires a
deterministic `PASSED` oracle. Use `UNKNOWN` for unobservable founder time,
tokens, or cost. For `FAILURE` or `BLOCKED`, supply an explicit
`--failure-class`. Two consecutive identical `INFRASTRUCTURE` failures
quarantine only that task's `channel_code`; `AUTH` or `QUOTA` pauses only that
channel. Do not claim work from a non-`ACTIVE` channel. Then run `audit-public`
and `persist --push` so the next task can resume from the pilot branch. The push
records an intent before the effect; the next invocation reconciles it against
the remote before claiming work.

Use `pause` immediately for an uncontrolled permission/privacy/integrity event,
or explicit operator request. Channel-local quota, auth, environment, and
infrastructure failures use the channel state above and must not pause unrelated
authorized work. Do not change the fixed end time, budgets, qualification gates,
frozen oracle, or historical result.

The operator pause entry is `python3 scripts/aeg_foundry.py pause
--reason-code OPERATOR_REQUEST --push`; it records and pushes the pause before
the next scheduled invocation can claim work.

Stay quiet when nothing materially changed. Notify only on a real milestone,
failure, required human decision, or terminal conclusion.
