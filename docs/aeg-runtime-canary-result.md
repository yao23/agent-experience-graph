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

---

## Runtime Canary 02

### Outcome

- Status: `PASS`; this was the single authorized Runtime Canary 02 attempt and
  it was not rerun.
- Control revision:
  `49729bf234040cee625738f02e395c87b29d553f`.
- Pinned public replay source:
  `999efa64e9ba016efc9d3327df4b70e1fc79b804`.
- Actions run: [`34052053116`](https://github.com/yao23/agent-experience-graph/actions/runs/34052053116)
- Job: [`runtime-canary` / `101537297217`](https://github.com/yao23/agent-experience-graph/actions/runs/34052053116/job/101537297217)
- Trigger: one non-force push whose `before` revision was the frozen Canary 01
  result revision `4942049e632bf9442fe7809fe2450697a884fba0`;
  `run_attempt=1`.
- Run created: `2026-09-06T18:32:36Z`; job ran from
  `2026-09-06T18:32:40Z` through `2026-09-06T18:32:57Z`.
- Runner: standard GitHub-hosted `ubuntu-24.04-arm`, Ubuntu 24.04.4 LTS,
  ARM64, runner `2.337.0`, image `20260831.111.1`.

The historical Canary 01 result above remains `BLOCKED`. Its EACCES diagnosis
remains explicitly an inference from that run, not a retroactive proof of its
root cause.

### New boundary evidence

All 17 required probes completed with `PASS`; none remained `UNKNOWN` or
`NOT_RUN`:

1. Host-side inspection attested the digest-labelled Python base image, all
   capabilities dropped, CPU/memory/PID limits, cleared entry environment,
   exact mounts, `network=none`, no devices, `no-new-privileges`, non-privileged
   mode, read-only root, non-root user, and bounded tmpfs.
2. The execution process observed only the 11 allowlisted environment keys and
   no token, secret, password, credential, Actions, or GitHub environment key.
3. Runtime-home, runner-home, and GitHub-home credential paths were `ABSENT`.
   Both `/root` credential paths were `ACCESS_DENIED`; their existence remains
   explicitly unknown. Combined with the digest-attested image, cleared
   environment, exact mounts, and credential-free checkout configuration, the
   supported conclusion is `NO_CREDENTIAL_ACCESS_OBSERVED`, not “all credential
   files are absent.”
4. `/var/run/docker.sock`, `/run/docker.sock`, `/home/runner`, `/github/home`,
   `/__w`, and `/Users` were `ABSENT`. The in-process mount view contained the
   three expected mount points and no suspicious host mount.
5. The host-created synthetic outside sentinel was not present in the
   container namespace (`ENOENT`). `/work` completed a write/read/delete round
   trip. Writes to `/source` and the container root were rejected with `EROFS`.
6. The process ran as UID `1001` with `CapEff=0`, `NoNewPrivs=1`, and
   `Seccomp=2`.
7. The outbound probe returned `ENETUNREACH`; this was accepted only together
   with the independently inspected `network=none` configuration.
8. A 0.2-second synthetic timeout terminated the child with `SIGTERM`
   (`return_code=-15`) and verified that it was reaped without a forced kill.
9. The process observed the exact pinned source revision, and the historical
   non-mainline commit was not present.

Relative to Canary 01, this run therefore adds actual process-level evidence
for the environment, credential-access, mount, sentinel, work/source/root,
network, kernel, timeout, source-identity, and historical-object boundaries.
No real credential content or unrelated host file was read or printed.

### Replay

The replay was attempted once and exited `0`. Its structured report was
`PASS` with:

- `essential_case_count=13`
- `executed_case_count=13`
- `matching_case_count=13`
- baseline escape defect observed
- fixed escape rejection observed
- legitimate in-root cases preserved
- baseline and fixed source identities verified
- replay temporary artifacts cleaned

This is evidence only for the pinned public evidence-path-confinement replay.
It is not evidence that Linkwarden can execute, that AEG-C-001 has reproduced,
that an external user succeeded, or that transfer succeeded.

### Cleanup, lifecycle, and consumption

The canary process elapsed time was `0.408` seconds; the Actions job wall time
was 17 seconds. Both container and wrapper exit codes were `0`. The wrapper
then verified removal of the container, local image, synthetic sentinel, and
temporary root. Actions checkout cleanup completed, and GitHub destroyed the
hosted VM. The runtime is historical evidence and is not registered as a live
Foundry environment.

- Local diagnosis, implementation, and test elapsed time: `UNKNOWN`.
- Main-session and CI token use: `UNKNOWN`.
- Founder/operator time: `UNKNOWN`.
- Actual billed USD: `UNKNOWN`; no paid runner, artifact, or cache was selected.
- Foundry daily budget and historical counters: unchanged.

The remaining Foundry integration is still one same-lifecycle entrypoint that
uses the existing controller to create and qualify a fresh runtime, claim and
execute one already-authorized task, record its result, and destroy that
runtime before the job ends. Canary `PASS` alone does not supply this adapter
or a reusable environment receipt.
