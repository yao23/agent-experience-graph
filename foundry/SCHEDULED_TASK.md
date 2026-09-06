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
or no meaningful change exists, remain quiet.

For the one claimed task, execute exactly one discovery, reproduction, repair,
verification, transfer-evaluation, or release-material stage. Persist intent
before any network read/write or other external effect and resolve it only from
the actual result. Never retry an uncertain effect before read-only
verification. Do not run external repository code, installers, or tests unless
the charter's clean disposable-environment gate is already satisfied. Never
read historical `.aeg` content. Keep raw logs and model output only in
`.aeg-foundry-private/`.

Finish with the actual deterministic oracle outcome using
`python3 scripts/aeg_foundry.py finish-round`; `SUCCESS` requires `PASSED`.
Keep founder hours, tokens, and dollars as `UNKNOWN` when not observable. Run
`python3 scripts/aeg_foundry.py audit-public`, then
`python3 scripts/aeg_foundry.py persist --run-id <ROUND_ID> --push`. Do not
merge a PR, deploy, promote an Experience, alter repository rulesets, spend new
money, export private material, or contact external maintainers without the
separate authorization required by the charter.

Notify only for a real milestone, failure, terminal conclusion, or required
human decision. The fixed pilot expiry is `2026-10-18T07:22:29Z`; do not start
new experiments at or after it.
