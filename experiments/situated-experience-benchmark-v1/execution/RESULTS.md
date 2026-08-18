# S1 execution result

Situated Experience Benchmark v1 S1 is **infrastructure-blocked**. This is an
S1 mechanism pilot using faithful public extracts, not full historical
dependency stacks.

The exact frozen 12-arm plan was generated after hosted CI passed. A reusable
host-controller and disposable-container substrate was subsequently built and
tested on GitHub-hosted Ubuntu. Its non-benchmark canary passed 28 fixture,
isolation, resource, patch-export, evaluator-order, and sanitizer attempts.
The gate remained blocked because the repository has neither required Actions
secret: `OPENAI_API_KEY` for the host controller and
`AEG_RAW_OUTPUT_CERT_PEM` for the external encryption recipient. No model call
or benchmark arm was attempted.

## Arm accounting

- Planned: 12.
- Started: 0.
- Completed: 0.
- Task failures: 0.
- Infrastructure-failed arm records: 0; the substrate failed before an arm was
  started, so no task outcome was manufactured.
- Hidden evaluations: 0.
- Non-benchmark model calls and input/output tokens: 0 because the hosted
  credential was absent.
- Recorded model cost: $0.

There are no per-pair or aggregate repair results. Regression-free success,
attempts, completed commands, tests, files inspected, patch size, repeated
historical paths, negative transfer, experience disposition, environment
assumptions, token overhead, and median wall time are all not evaluable.

## Mechanical decision

Promotion is not supported and fails closed. No correctness comparison or
interpretable repair-path improvement exists, and treatment token overhead was
not measured. The real hosted container boundary passed its adversarial checks,
but live credential brokering, encrypted retention, and token telemetry were
not demonstrated. No frozen benchmark stop condition was triggered by an
observed arm outcome because no arm ran; instead, the prerequisite substrate
gate blocked execution.

Do not expand S1 to full historical dependency stacks yet. First configure the
two host-only workflow inputs and rerun the same canary to demonstrate live
model access, encrypted retention, and token telemetry for both modes. S2-S6
remain unstarted.
