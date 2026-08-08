# Repository-state-only shakedown

These fixtures exercise persistence and orchestration without network access,
models, credentials, secrets, paid cost, external writes, or commercial work.

`repository-state-recovery-01` records an objectively invalid precondition,
freezes a deterministic transformation and oracle, creates a normalized local
artifact, evaluates it, and completes. Six fresh `run-one-step` processes made
the six lifecycle transitions. A seventh process proved terminal idempotence.

`external-action-escalation-01` contains an inert request targeting the reserved
`.invalid` domain. The controller detects the external-write request, performs
no network or substitute action, enters `escalated`, writes a machine-readable
record, and returns exit code `10` on subsequent independent invocations.

The fixtures validate only:

- GitHub/repository state as the persistent control plane;
- deterministic one-step lifecycle progression;
- objective local evaluation and budget recording;
- append-only global and per-experiment ledger integrity;
- terminal idempotence and fail-closed escalation.

They do not validate AEG retrieval benefit, model intelligence, external value,
commercial demand, generalized effectiveness, or product-market fit.
