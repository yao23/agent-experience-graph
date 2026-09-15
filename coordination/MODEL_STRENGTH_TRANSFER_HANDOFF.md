# Model-Strength Transfer v1 handoff

## State

`experiments/model-strength-transfer-v1/` is a validated proposal, not an
execution authorization. It introduces no new queue item, model call, case
start, repository, budget, scheduler, external write, or transfer claim.

The active policy remains `coordination/AUTHORIZATION.json`. If this handoff or
the protocol conflicts with that policy, the policy wins and the conflicting
action must stop.

## What existing cloud roles may do

- **OSS scan:** apply the defensive-maintenance priority in
  `SEARCH_CHECKLIST.md` within the existing repository list and hard
  exclusions. Record future model-strength suitability facts, but do not run
  another arm or contact a model.
- **Startup OS:** preserve those facts when evaluating or drafting an existing
  candidate. Do not select a protocol task, create a transfer queue item, alter
  READY ordering solely for this study, or change the local consumer model.
- **Competitive research:** use primary evidence to refine falsifiable
  hypotheses about model memory, harnesses, evaluation, and cross-model
  transfer. Do not convert an announcement into an AEG result.
- **Bayesian review:** count protocol readiness separately from transfer
  evidence. Zero eligible candidates or zero authorized runs is a valid result.
- **Local consumer:** ignore this protocol for execution until an immutable,
  operator-approved activation replaces the non-executable state.

All roles continue using their existing schedules and budgets. No second
scheduler or queue writer is authorized.

## Future study suitability fields

For an otherwise eligible candidate, record only observable facts:

```json
{
  "model_strength_study": {
    "experience_predates_astra": "YES|NO|UNKNOWN",
    "independent_target": "YES|NO|UNKNOWN",
    "shared_frozen_oracle_possible": "YES|NO|UNKNOWN",
    "treatment_only_experience_possible": "YES|NO|UNKNOWN",
    "telemetry_available": "YES|NO|UNKNOWN",
    "fresh_context_and_artifact_isolation": "YES|NO|UNKNOWN",
    "status": "SUITABLE_FOR_FUTURE_REVIEW|NOT_SUITABLE|UNKNOWN"
  }
}
```

These fields are advisory metadata. They do not change candidate eligibility,
claim a case start, reserve transfer budget, or authorize model access.

## Activation gate

Before any arm can run, all of the following must exist at one immutable commit:

1. a new operator-approved authorization permitting the exact transfer case;
2. reconciliation of prior transfer minutes and cash-equivalent usage;
3. exact available model identifiers, including the external comparator;
4. approved cost, time, retry, and case-start limits;
5. a frozen public task, revision, dependencies, oracle, and Experience digest;
6. fresh non-inheriting solver contexts with evaluator and cross-arm artifact
   isolation;
7. a preregistered arm order, stop conditions, and result contract.

Activation must replace `PROPOSED_NOT_AUTHORIZED` through a reviewed commit; it
must not be inferred from this handoff, a scheduled-task prompt, a writable
report, or model availability in the product UI.

## Operator validation commands

```bash
git fetch origin codex/aeg-task-bridge-v1
git switch codex/aeg-task-bridge-v1
git pull --ff-only origin codex/aeg-task-bridge-v1
python3 experiments/model-strength-transfer-v1/validate_protocol.py
python3 -m unittest experiments/model-strength-transfer-v1/test_validate_protocol.py
git diff --check
```
