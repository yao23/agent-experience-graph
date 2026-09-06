# Hosted runtime canary result

## Outcome

- Status: `BLOCKED`; the single authorized attempt was not rerun.
- Actions run: [`34047772154`](https://github.com/yao23/agent-experience-graph/actions/runs/34047772154)
- Job: [`runtime-canary` / `101525807054`](https://github.com/yao23/agent-experience-graph/actions/runs/34047772154/job/101525807054)
- Trigger: the branch-creation `push` for
  `codex/aeg-runtime-canary-v0.1` at control revision
  `a804e80df06dc6c70336ccbd2000902457f66ecc`.
- Run created: `2026-09-06T17:10:34Z`; job ran from
  `2026-09-06T17:10:39Z` through `2026-09-06T17:10:57Z`.
- Runner: GitHub-hosted `ubuntu-24.04-arm`, Ubuntu 24.04.4 LTS, ARM64,
  runner `2.337.0`, image `20260831.111.1`.
- Pinned public source checkout completed at
  `999efa64e9ba016efc9d3327df4b70e1fc79b804`.

This used a standard GitHub-hosted runner in a public repository. GitHub's
[Actions billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
states that standard GitHub-hosted runners are free in public repositories;
larger runners are always charged. The workflow selected neither a larger nor
self-hosted runner and uploaded no artifact or cache. No paid resource was
selected; actual billed USD remains `UNKNOWN` rather than being inferred as
zero.

## Boundary evidence

Before process execution, the job inspected the created container and passed
all configured-policy checks: non-privileged; all Linux capabilities dropped;
`no-new-privileges`; read-only root; non-root UID; no devices; `network=none`;
bounded CPU, memory, PIDs, and tmpfs; an empty explicit environment; and
exactly three mounts (`/control` read-only, `/source` read-only, `/work`
read/write). Dependency acquisition had already completed outside that
network-disabled execution container.

The execution-process probes did not complete. The result envelope recorded
`CANARY_EXCEPTION_PERMISSIONERROR`, an empty `boundary_probes` list, and
`replay.attempted=false`. The most specific diagnosis supported by the program
order is a probe-harness bug: the first credential-path check calls
`Path.exists()` on `/root/.git-credentials` as the non-root container user;
that operation can raise `PermissionError` instead of returning false. The
exception occurred before the function returned its earlier probe records.
This is an inference from the emitted exception type, empty probe list, and
source order; it is not evidence that a credential was present.

Consequently, the run did **not** establish execution-process absence of model,
GitHub, or Actions credentials; in-process host-home and Docker-socket
inaccessibility; the actual outbound-network negative probe; `/work` read/write;
outside-sentinel denial; source/root write denial; timeout behavior; or replay
behavior. It did establish the corresponding Docker configuration boundary,
but configuration evidence alone is not treated as runtime qualification.

The container returned exit code `2`. The wrapper then successfully passed its
cleanup commands for the container, local image, and synthetic sentinel before
propagating exit code `2`; Actions checkout cleanup also completed. GitHub
destroyed the hosted VM after the job. This is a historical canary environment,
not an available runtime receipt.

## Replay and lifecycle consequence

The command
`python3 examples/evidence-path-confinement/replay.py --json` was not attempted,
so none of its 13 essential cases, baseline escape, fixed rejection, or legal
internal-path preservation was observed in this run. The actual replay result
is therefore `BLOCKED`, not `PASS` or `FAIL`.

A receipt-first/next-round handoff cannot safely represent this kind of
short-lived runner: the environment is gone before a later round could claim
it. The smallest later integration is one existing-controller entrypoint that
performs creation, qualification, one already-authorized claim and execution,
result recording, and destruction inside the same job lifetime. This task does
not implement that integration or register a fictional live runtime.

## Consumption

- Main interactive session: elapsed time, token use, and dollar cost `UNKNOWN`.
- Automation-maintenance update: elapsed time, token use, and dollar cost
  `UNKNOWN`.
- CI: one job, 18 seconds wall time; token use `UNKNOWN`; actual billed USD
  `UNKNOWN`; no paid runner, artifact, or cache was selected.
- Founder/operator time: `UNKNOWN`.
- New paid spend: no paid resource was selected; observable invoice amount
  `UNKNOWN`.

The only next engineering step is to correct the EACCES handling in the
credential-path probe and make one newly authorized same-lifecycle canary
attempt. It is not authorized as part of this completed attempt.
