# Metrics and instrumentation plan

Phase 0 defines fields; it collects no customer or repair data.

| Lane | Metrics | Evidence rule |
|---|---|---|
| Quality | task success, first-pass success, regression-free outcome | frozen objective oracle |
| Work | commands, retries, model calls | machine counters where available |
| Usage | input/output tokens, model cost | exact telemetry or `unavailable`; never estimate zero |
| Time | wall-clock, founder minutes, human interventions | timestamped run and intervention records |
| Retrieval | query timing, abstention/recommendation, reused capsule, execution change | preregistered query record and causal narrative |
| Acceptance | maintainer/customer acceptance, useful diagnosis | attributable external response after approval |
| Retention | repeat usage, delivery 1-to-N improvement | same-user sequence without identity in public evidence |
| Commercial | willingness to pay, first revenue, conversion, no-charge rate | approved offer/payment records only |

Keep ordinary agent work, orchestration, retrieval effect, verified outcome,
external acceptance, and demand as separate fields. Missing data remain `null`
or `unavailable`. Phase 0 values for customer contact, external writes, payment,
repair executions, and promoted experiences must remain zero.
