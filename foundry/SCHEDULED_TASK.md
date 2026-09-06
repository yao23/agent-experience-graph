# AEG Experience Foundry scheduled task

Run one bounded AEG Experience Foundry Pilot v0.1 stage. In the selected local
project, locate the single Git checkout with remote
`https://github.com/yao23/agent-experience-graph.git` on branch
`codex/aeg-experience-foundry-pilot-v0.1`; do not use `main` or another
worktree. Read `foundry/CHARTER.md`, `foundry/pilot.json`,
`foundry/backlog.json`, `foundry/state.json`,
`.agents/skills/aeg-foundry/SKILL.md`, and the last `foundry/rounds.jsonl`
record from that checkout.

Run `python3 scripts/aeg_foundry.py validate`, then
`python3 scripts/aeg_foundry.py begin-round --reconcile-push`. Respect its
pause, expiry, budget, lease, unresolved-effect, and no-work exits. If no work
or no meaningful change exists, remain quiet. An active-run budget exit occurs
before push reconciliation and intentionally preserves the committed pending
intent for the next eligible invocation; expiry still reconciles first.
Treat `foundry/pilot.json` as a closed, immutable control contract. Never edit
its activation, authorization, budget, execution, model, schedule, source, or
target/gate fields to make a run start or a result pass.

If `begin-round` reports `EXPIRED`, inspect the state it just wrote. When no
effect remains pending, run `audit-public` and persist the generated terminal
state and `foundry/reports/final.md` with the recorded `last_round_id`, then
notify the terminal recommendation. If an explicit operator pause left an
unresolved effect, remain network-quiet and request human resolution rather
than pushing around the pause.

Immediately after a claim, run `record-intent` with effect type
`READ_PUBLIC_SOURCE` and target code `CURRENT_SOURCE_REMOTE_REF`, then run
`python3 scripts/aeg_foundry.py observe-source-ref --round-id <ROUND_ID>
--effect-id <EFFECT_ID>`. Treat the SHA initially returned by `begin-round` as
provisional; do no stage work until the controller freezes the current remote
branch SHA. If the source read fails, finish the round as an infrastructure
failure using the reported failure code.

For the one claimed task, execute exactly one discovery, reproduction, repair,
verification, transfer-evaluation, or release-material stage. Persist intent
before any network read/write or other external effect and resolve it only from
the actual result. Never retry an uncertain effect before read-only
verification. Do not run external repository code, installers, or tests unless
the charter's clean disposable-environment gate is already satisfied. Never
read historical `.aeg` content. Keep raw logs and model output only in
`.aeg-foundry-private/`.

Do not rewrite a committed candidate classification or put verification flags
on candidates. A behavior-verification stage writes a first-class
`behavior_verifications[]` record only after an independent verifier actually
runs the frozen oracle in isolated baseline and repaired environments and saves
both command/exit/evidence receipts. Baseline must fail and repaired must pass.

For an Experience stage, write only the code-only, digest-pinned artifact shape
accepted under `foundry/experiences/`, and register its sources and builder
tasks in `experiences[]`. For a held-out transfer, preregister all frozen fields
in `transfer_evaluations[]` before starting either arm. Use separate contexts,
workspaces, and disposable environments; keep the same target revision, oracle,
model budget, tool permissions, and tests. Preserve every attempt in order with
command, exit status, timing, failure/validity state, oracle observation, and
evidence digest. Do not expose any Experience or evaluator feedback to the
baseline. Do not mark an Experience release-ready until a completed independent
transfer passes controller validation. Never hand-edit derived release-review
or positive-transfer counts. Committed Experience versions, preregistered
frozen fields, and terminal transfer results are append-only; use a new version
or transfer ID rather than rewriting history.

Treat external adoption separately from internal verification. Self-reports may
be registered but do not verify a user or successful reuse. Only a
digest-backed deterministic oracle run for a verified external user, stored in
`external_reuse_events[]` with an independent verifier and fresh environment,
enters the external-success numerator. Never count the founder, this loop, its
agents, or project CI as an external user.

Finish with the actual deterministic oracle outcome using
`python3 scripts/aeg_foundry.py finish-round`; `SUCCESS` requires `PASSED`.
The controller charges the scheduled worker at claim time, including crashes;
register every extra worker against the active round ID and let finish infer the
total from those events.
Record configured and observed model separately, model attestation, call method,
input/output/total tokens, retries, quota observation, actual-cost basis, and any
market estimate with its source. Use `UNKNOWN` rather than zero whenever a value
or its evidence is not observable.
For `FAILURE` or `BLOCKED`, classify the cause with `--failure-class` and retain
the actual failure code. Respect the claimed task's `channel_code`: two
consecutive identical infrastructure failures quarantine that channel, while
auth or quota failure pauses only that channel. Continue unrelated authorized
work on other `ACTIVE` channels.
Keep founder hours, tokens, and dollars as `UNKNOWN` when not observable. Run
`python3 scripts/aeg_foundry.py audit-public`, then
`python3 scripts/aeg_foundry.py persist --run-id <ROUND_ID> --push`. Do not
merge a PR, deploy, promote an Experience, alter repository rulesets, spend new
money, export private material, or contact external maintainers without the
separate authorization required by the charter.

Notify only for a real milestone, failure, terminal conclusion, or required
human decision. The fixed pilot expiry is `2026-10-18T07:22:29Z`; do not start
new experiments at or after it.

If the controller synthesizes a due `REPORTING` task after ordinary work is
exhausted, complete only that stage with
`WEEKLY_REPORT_SCHEMA_AND_WINDOW_CHECK`; the controller creates the missing
weekly report deterministically and includes all model-worker events.

An operator may pause through `python3 scripts/aeg_foundry.py pause
--reason-code OPERATOR_REQUEST --push`. The command reconciles an already-pushed
checkpoint first; if an unresolved non-push effect or active round prevents
remote persistence, the local pause remains effective and reports the exact
deferred condition for safe resolution.
