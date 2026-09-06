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

For an active, non-expired pilot, budget gates run before prior-push
reconciliation. If the current UTC-day or total budget is exhausted, leave the
committed push intent untouched for a later eligible invocation; do not create
an uncommitted reconciliation receipt. Expiry remains the exception and
reconciles before writing the terminal checkpoint.

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

Candidate records use the controller's exact field shape. Once committed, their
identity, category, contamination and qualification are immutable; add a new
candidate instead of reclassifying history. Independently verified behavior is
counted only from `behavior_verifications[]`: it needs a qualified non-held-out
candidate, completed verification task, frozen revisions/oracle/model/budget,
isolated baseline failure and repaired success receipts, and a verifier distinct
from the solver. Candidate annotations never count as verification.

Create Experience artifacts only as direct JSON files under
`foundry/experiences/`, using the controller's code-only allowlist and a digest
recorded in `backlog.json`. Record the Experience entity separately from its
source candidates and builder tasks. Never hand-edit release or transfer
counts: they are derived only from validated `experiences[]` and
`transfer_evaluations[]` records.

Before either arm of a held-out transfer begins, preregister the immutable
Experience version, qualified held-out target and revision, oracle and version,
model configuration, budget, retry and decision rules, order, tool permissions,
and visible materials. Baseline and assisted must use distinct contexts,
workspaces, and disposable environments. Retain every attempt in order with its
command, exit code, timing, status, oracle observation, evidence digest and
summary codes; the terminal arm summary must match the final attempt. The
deterministic oracle executor must be distinct from the solver. Baseline cannot
see any Experience or evaluator feedback, and the assisted arm may see only the
declared Experience version. A release-ready Experience requires at least one
completed transfer whose target and transfer task did not build it. Never alter
a committed Experience version, a preregistered frozen field, or a terminal
transfer result; create a new version or transfer record instead.

External users and reuse are separate evidence. Record pseudonymous,
digest-backed user evidence in `external_users[]`; a self-report is not a
verified user. Record external reuse in `external_reuse_events[]`; only an
actual deterministic oracle run for a verified external user, with command,
exit status, fresh verification environment, digest and independent verifier,
counts in the external-success numerator. Founder, Foundry agents, and project
CI are never external users.

Finish with the actual oracle result using `finish-round`. `SUCCESS` requires a
deterministic `PASSED` oracle. The scheduled worker start is charged when the
round is claimed, including a later crash. Register every extra worker with the
active `--round-id`; `finish-round` derives the total from those immutable
events, so do not hand-edit or double-count it. Record the
configured model separately from the observed model and attestation, plus call
method, input/output/total tokens, retries, quota observation, actual cost basis,
and any market-price estimate with its source. Use `UNKNOWN` for unobservable
founder time, tokens, quota, attestation, or cost; a numeric cost is rejected
without its basis. For `FAILURE` or `BLOCKED`, supply an explicit
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
--reason-code OPERATOR_REQUEST --push`. It verifies an already-pushed checkpoint
before recording and pushing the pause. If that verification is unavailable, or
a round is active, local pause is immediate and the command explicitly returns
`DEFERRED_PENDING_EFFECT` or
`DEFERRED_ACTIVE_ROUND_SAFE_CHECKPOINT_REQUIRED`; do not claim remote
persistence until the stated condition is resolved.

Stay quiet when nothing materially changed. Notify only on a real milestone,
failure, required human decision, or terminal conclusion.

When no ordinary work is ready and a seven-day report is due, the controller
synthesizes one `REPORTING` stage. Finish it with the frozen weekly-report oracle;
the controller generates the report and verifies its presence. Do not replace
that bounded task with an out-of-band hand-written report.
