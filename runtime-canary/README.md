# AEG hosted runtime canary

This branch performs one bounded isolation canary on a standard
GitHub-hosted `ubuntu-24.04-arm` VM. The branch-creation push is the only event
allowed to start the job; a rerun has `github.run_attempt > 1` and is skipped.
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
sentinel are unavailable. It also proves a write/read round trip inside the
result directory, rejects a source/root write, and makes an outbound HTTPS
negative probe before running:

```text
python3 examples/evidence-path-confinement/replay.py --json
```

The job prints its complete structured result and concise Job Summary, then
removes its container, local image, sentinel, and temporary directory. Logs and
Job Summary do not use Actions artifact or cache storage. The hosted VM itself
is destroyed by GitHub after the job and is never registered as a future
Foundry runtime.

This canary does not run an external target repository, call a repair model,
create a Capture Candidate, or count as external reuse or transfer. A future
AEG-C-001 reproduction needs a newly created ARM64 job that performs
qualification and the frozen target oracle within that same job lifetime.
