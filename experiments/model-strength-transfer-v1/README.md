# Model-Strength Transfer v1

Status: `PROPOSED_NOT_AUTHORIZED`

This preparation-only protocol tests a narrow question:

> When a frontier model becomes materially stronger, does a verified prior AEG
> Experience still improve a real repair, become unnecessary, or cause harmful
> steering?

It compares control and AEG-assisted modes for GPT-6 Astra, GPT-5.6 Sol and one
external model. Every cell receives the same frozen task, repository revision,
oracle, tool surface and budget. The treatment cells receive one frozen compact
Experience; controls receive no substitute advice.

No model run is authorized by this directory. The current coordination policy:

- permits no additional transfer check;
- permits no new paid API;
- fixes the local consumer model to `gpt-5.6-terra`;
- has an unresolved prior transfer-time reservation;
- requires a demonstrable fresh-context and artifact-isolation boundary.

Changing `protocol.json` from `PROPOSED_NOT_AUTHORIZED`, selecting a task,
freezing inputs, or executing an arm therefore requires a new operator-approved
authorization. This protocol does not modify the existing scheduler.

## Candidate requirements

The selected source Experience must have been recorded before GPT-6 Astra's
2026-09-03 release. The target must be independently originated, public and
license-compatible, with an objective local oracle. The source Experience may
contain a reusable mechanism but must not reveal the target repair or evaluator
artifacts.

The first candidate should come from deterministic OSS maintenance already
aligned with AEG's wedge: CI, dependency/framework migration, test migration,
resource lifecycle, regression, misleading green repair, or environment drift.
Security vulnerabilities, exploits, authentication/permission work, production
systems and private data are excluded from this version.

## Planned execution

Phase 0 is one exploratory pair per model: six total arms. It may reject the
study for leakage, triviality, telemetry failure, unacceptable cost, model
unavailability, or negative transfer. It cannot establish a general benefit.

Phase 1 is three pairs per model: eighteen total arms. It requires a second
activation gate after Phase 0 and is not implied by smoke success.

All cells record correctness, attempts, completed commands, tests, input/output
tokens, wall time, Experience disposition, negative transfer and abstention.
Use the existing Situated Experience Benchmark measurement definitions where
they apply.

## Validate the proposal

```bash
python3 experiments/model-strength-transfer-v1/validate_protocol.py
python3 -m unittest experiments/model-strength-transfer-v1/test_validate_protocol.py
```

Validation proves only that the proposal is internally consistent and remains
non-executable. It is not an experiment result.
