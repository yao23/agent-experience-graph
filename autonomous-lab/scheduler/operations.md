# Scheduler operations guide

Status: infrastructure prepared for review; no scheduled task is created or
enabled.

## Recommended operating mode

Use the ChatGPT desktop app and select the local AEG Git repository as the
project. Choose local-project execution initially because the experiment state
and append-only event ledger must persist between runs. Keep the computer on,
the repository available, and the desktop app running when local files are
needed.

OpenAI's current scheduled-task documentation says desktop tasks can operate in
a local project or isolated worktree, warns that local-project runs can modify
unfinished work, recommends narrow sandbox access, and recommends reviewing the
first runs before increasing cadence:
https://learn.chatgpt.com/docs/automations?surface=app

The product documentation does not promise that uncommitted state in a
scheduled background worktree is reused by the next independent run. This
control plane therefore uses local-project mode on `main` and requires
`scheduled-step --persist-commit`. After one validated transition, the
controller accepts only its explicit state/ledger/evidence/report allowlist,
stages those actual files, creates one local un-pushed commit with hooks and GPG
signing disabled and a fixed non-personal local author identity, and verifies a
clean worktree. It never pushes, resets,
stashes, cleans, or touches unrelated work. Any unexpected path stops with
exit code `14` and remains available for manual inspection.

## Initial cadence and access

- Start at most once per hour.
- Use `autonomous-lab/prompts/scheduled-step.md` as the saved standalone prompt.
- Select **Local project**, not Worktree, so the local commits form the next
  run's authoritative state.
- Review the first several runs before considering any higher frequency.
- Do not grant network access unless a separately reviewed experiment requires
  it.
- Do not add secrets.
- Keep the task disabled until the scheduler-readiness pull request is reviewed
  and merged and an eligible experiment is separately approved.

Pause the task after any of these results:

- `10`: human approval required;
- `11`: validation or evidence failure;
- `12`: budget exhausted;
- `13`: lease held or stale;
- `14`: unsafe or conflicting working tree;
- `15`: invalid scheduler configuration or selection.

Never retry those results automatically.

## Lease and recovery

The atomic execution lease is stored under Git's shared common directory, not
in tracked content. All worktrees attached to that Git directory contend on the
same lease. Acquisition, rejection, stale detection, release, and explicit
recovery are appended to a hash-linked local operational audit file beside the
lease. The transient files are never committed.

A non-expired lease must never be broken. When a lease is expired, inspect the
reported holder and timestamps, then run:

```sh
python3 autonomous-lab/scripts/lab.py recover-stale-lease
```

This protects worktrees sharing one Git common directory. It cannot coordinate
independent clones on different machines or filesystems; do not schedule the
same experiment from multiple clones.

The controller never cleans, resets, stashes, discards, or overwrites user
changes. Unsafe-tree recovery is a manual operator action.

## Per-transition commit allowlist

Only actual changes within this superset may be committed:

- `autonomous-lab/experiments/registry.yaml`
- `autonomous-lab/ledger/events.jsonl`
- `autonomous-lab/reports/current-status.json`
- `autonomous-lab/reports/current-status.md`
- `autonomous-lab/reports/next-human-action.md`
- the selected experiment's `state_path`, `scorecard_path`, and
  `escalation_path`
- the selected experiment's declared `runtime_evidence_paths`

The controller commits the subset actually changed by that transition. A
second experiment, business-artifact rewrite, verified-library change,
untracked file, rename, deletion, staged change, or unrelated modification is
not allowed.
