# AEG Arm Execution Substrate v1

This infrastructure runs an agent model on a GitHub Actions host while every
model-requested file or command operation executes in one locked, networkless
repair container. It is reusable laboratory infrastructure; it is not a
Situated Experience Benchmark result.

The host controller alone receives `OPENAI_API_KEY`. It sends strict function
tools to the Responses API, validates every tool request, and invokes only the
container worker through `docker exec` with an explicit `env -i` environment.
The repair container receives one `arm.json`, one task directory, no controller
checkout, no hidden evaluator files, no Git remote, no socket, and no secret.
The controller copies those two inputs into a dedicated size-limited tmpfs;
the container has zero host bind mounts.

The pinned base image is:

```text
python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7
```

The workflow uses `ubuntu-24.04`; each result records the hosted runner's
runtime `ImageOS` and `ImageVersion`. Docker runs with `--network none`, a
read-only root, isolated tmpfs, all capabilities dropped, no-new-privileges,
private PID namespace, and CPU, memory, PID, workspace, file, command, token,
cost, and wall-time limits from `policy.json`. A tool timeout kills the complete
repair container rather than leaving an over-time subprocess alive.

The host replays every Responses API output item in stateless mode so opaque
reasoning items remain continuous across strict function calls. The controller
records API token usage and computes a running cost estimate from the pinned
pricing values in `policy.json`; either ceiling stops the arm.

## Controller operations

```sh
python3 infrastructure/aeg-arm-execution-substrate/controller.py validate
python3 infrastructure/aeg-arm-execution-substrate/controller.py revalidate-fixtures \
  --image aeg-arm-runner:python3.12.11-slim-bookworm-v1 \
  --output /tmp/aeg-fixture-revalidation.json
python3 infrastructure/aeg-arm-execution-substrate/controller.py canary \
  --image aeg-arm-runner:python3.12.11-slim-bookworm-v1 \
  --fixture-record /tmp/aeg-fixture-revalidation.json \
  --output /tmp/aeg-canary.json \
  --encrypted-raw-output /tmp/aeg-canary-raw.p7m
```

`canary` requires a host-only `OPENAI_API_KEY` and the public X.509 certificate
in `AEG_RAW_OUTPUT_CERT_PEM`. The corresponding decryption key must remain
outside the repository and Actions job. Missing either input blocks readiness.

The canary covers controller and sibling-arm paths, host credentials and
environment inheritance, Docker socket, network, hidden evaluator inputs,
human patches, caches and transcripts, symlink/absolute/`/proc` escapes,
subprocess inheritance, resource ceilings, allowlisted patch export, repair
termination before evaluation, result-schema sanitization, live model tool use,
telemetry, and encryption. It executes no benchmark arm.

The manual workflow defaults to `canary`. Its `execute-s1` matrix is present but
requires an exact confirmation string, runs at most one matrix job at a time,
and is intentionally not invoked by this infrastructure change.
