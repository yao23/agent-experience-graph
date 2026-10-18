# AEG hosted runtime canary

This branch performs one bounded isolation canary on a standard
GitHub-hosted `ubuntu-24.04-arm` VM. Runtime Canary 02 is gated to the single
non-force push whose `before` revision is the frozen Runtime Canary 01 result
revision `4942049e632bf9442fe7809fe2450697a884fba0`; a rerun has
`github.run_attempt > 1` and is skipped.
The workflow has one job with a 20-minute limit and no `workflow_dispatch`,
`pull_request`, `pull_request_target`, artifact, cache, larger-runner, or
self-hosted-runner path.

The dependency phase checks out exactly public `main` revision
`999efa64e9ba016efc9d3327df4b70e1fc79b804` with depth three and builds a
local-only container from a digest-pinned Python image. Those three mainline
commits contain the replay, fixed source, and baseline source. The historical
non-mainline target commit is required to be absent.

The execution phase starts one non-privileged, non-root container with no
network, no capabilities, a read-only root, seccomp, no-new-privileges, and
only three bind mounts: read-only control, read-only public source, and a new
read/write result directory. It checks that credential variables and files,
host homes, the Docker socket, unrelated host paths, and a synthetic outside
sentinel are unavailable. Path observations preserve `ABSENT`, `PRESENT`,
`ACCESS_DENIED`, and `PROBE_ERROR` separately: access denial never becomes an
absence claim and contributes to an inaccessibility result only when combined
with the inspected image environment and exact-mount policy. Expected
permission/read-only errors remain distinct from unexpected I/O errors.

It also proves a write/read round trip inside the result directory, rejects a
source/root write, combines an outbound HTTPS negative probe with the inspected
`network=none` configuration, and terminates and reaps a short synthetic timeout
process. Every required probe is predeclared as `NOT_RUN`, so an exception
retains completed observations and can never produce an aggregate pass. Only
after every required boundary is `PASS` does it run:

```text
python3 examples/evidence-path-confinement/replay.py --json
```

Replay `PASS` additionally requires the observed report to contain 13 unique
cases, 13 executions and matches, baseline escape, fixed rejection, legitimate
in-root preservation, and the two pinned runtime source identities.

The job runs a focused synthetic probe regression before the canary. It prints
its complete structured result and concise Job Summary, then
removes its container, local image, sentinel, and temporary directory. Logs and
Job Summary do not use Actions artifact or cache storage. The hosted VM itself
is destroyed by GitHub after the job and is never registered as a future
Foundry runtime.

This canary does not run an external target repository, call a repair model,
create a Capture Candidate, or count as external reuse or transfer. A future
AEG-C-001 reproduction needs a newly created ARM64 job that performs
qualification and the frozen target oracle within that same job lifetime.
