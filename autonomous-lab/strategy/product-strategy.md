# Product strategy

The lab tests whether retrieval of prior, verified agent experience can improve
bounded technical work for an identifiable external user. The near-term product
surface is an evidence-preserving recovery service for failed agent tasks, not a
general claim that AEG improves every agent task.

Experiments must connect a specific customer problem to a deliverable, an
objective acceptance oracle, a comparison baseline, external usefulness, and a
credible contribution or delivery path. Technical feasibility, retrieval
usefulness, external acceptance, and commercial demand are separate claims and
must be measured separately.

Batch 01 supports technical feasibility and some limited external usefulness.
Batch 02 supports stricter freshness screening and an abstention calibration;
it produced zero eligible fresh executions. Neither batch establishes
generalized effectiveness or product-market fit.

## Model memory is not the product boundary

Frontier-model providers increasingly preserve notes, search earlier context,
and improve their own agent harnesses. AEG should not compete on the claim that
it remembers more task history. The product boundary is qualification of prior
experience for reuse:

- model memory records what happened in one provider or session;
- tracing records how that run proceeded;
- a local evaluation records whether that run passed its oracle;
- AEG tests whether a compact experience remains useful across a different
  task, model, version, or environment, and preserves when it does not.

The near-term positioning is therefore: **model-neutral evidence for when agent
experience transfers, and when it does not.** Stronger models are an evaluation
condition, not a reason to assume retrieval is either useful or obsolete.

## Defensive OSS maintenance as a task source

Authorized public OSS maintenance is a high-value source of real tasks when it
has an objective, local oracle. The initial wedge remains deterministic CI,
dependency/framework migration, test migration, resource lifecycle,
cross-module regression, misleading green repairs, and environment drift.

"Defensive" here means making public software easier to validate, repair, and
maintain. It does not expand the lab into vulnerability discovery, exploit
development, authentication/permission changes, production systems, or private
infrastructure. Those remain excluded unless a future operator authorization
defines a separate safe scope.

Each eligible case should, when observable, preserve the sequence:

1. reproduce the public failure;
2. freeze a discriminating oracle;
3. validate the finding;
4. prepare a minimal repair;
5. add or preserve a regression test;
6. confirm that the failure no longer reproduces;
7. archive both successful and rejected paths with provenance and limitations.

The source of demand is the external maintenance problem. AEG's product claim
begins only when an independently originated later task tests whether an older
experience changes the outcome or repair path.
