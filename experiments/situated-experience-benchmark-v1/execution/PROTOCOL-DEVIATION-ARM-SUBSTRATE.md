# Infrastructure-only protocol deviation: container arm substrate

Recorded: 2026-08-14, before any Situated Experience Benchmark arm.

The original controller-host execution substrate was rejected before 0/12 S1
arms. No task outcome, transfer patch, evaluator result, treatment comparison,
or benchmark metric had been observed. This deviation therefore changes only
the execution substrate.

The frozen manifest, task pairs, prompts, compact experiences, modes, seeds,
budgets, arm ordering, measurements, promotion criteria, stop conditions, and
execution-plan hash remain unchanged. The authoritative hashes remain:

- manifest: `95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`;
- execution plan: `6e6a3b75102d03d804cf0b8e1f51b3b1194fe5e1c39802b9d0cc64043bb9582a`.

Execution moves to a host-controller / pinned Linux repair-container boundary.
The GitHub-hosted Ubuntu VM may access the job-scoped model credential. The
model has no host tools: its four strict tool calls are validated by the host
and executed only in a networkless container. The controller copies one
sanitized envelope and one task into a hard-size-limited workspace tmpfs; the
container has no host bind mount. Hidden evaluation starts in a separate
container only after repair termination. Raw transcripts and patches are
encrypted to an externally held public-key recipient before artifact upload;
only schema-validated metrics are public evidence.

The pinned base is
`python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
All four buggy source/transfer seeds, expected failure signatures, hidden suites,
and human patches must pass again on that image. S1 remains
`infrastructure-blocked` until the complete adversarial canary passes on the
same GitHub-hosted runner and container configuration. Mocked or local tests do
not establish readiness.
