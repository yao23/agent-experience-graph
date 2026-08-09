# Verified Experience Challenge: Phase 1 preregistration

Status: **proposed; do not recruit or execute**.

## Question and offer

Can verified, reusable agent experience provide observable value on current,
real developer tasks while abstaining when the library has nothing relevant?

> Bring one real coding problem. We will test whether a reusable, verified
> agent experience helps your coding agent solve it with less effort or better
> reliability.

The sample is three to five seed developers, one task each, and five tasks at
most. Eligible participants already use a coding agent, contribute to public
open source, and have a current reproducible bug, failing test, migration, or CI
problem. Close friends and relationships that inhibit negative feedback are
excluded. Mass outreach, scraping, paid acquisition, and unsolicited automation
are prohibited.

## Sequence

1. Obtain recruitment, consent, execution, and model-cost approvals that are
   still pending in `approval-record.json`.
2. Confirm repository authorization, license, contribution path, and consent.
3. Reproduce the defect without diagnosis, then freeze the repository commit,
   environment, task statement, and objective oracle.
4. Search issues, pull requests, commits, and forks for prior public repairs.
5. Freeze a feasible control plan or a written reason why no clean comparison
   can be run.
6. Query AEG before diagnosis and freeze the scores, evidence, recommendation,
   or abstention.
7. Only after every gate passes, run the separately authorized task procedure.
8. Record exact sanitized commands, tests, UTC timestamps, agent actions,
   interventions, objective result, path-change evidence, and participant rating.
9. Apply contamination rules before calculating any metric.

## Outcome classification

Retrieval is classified as a relevant recommendation, correct abstention,
irrelevant retrieval, or misleading retrieval. Repair is classified separately:
oracle pass with a material AEG path change, oracle pass independent of AEG,
oracle failure, or not executed/excluded. A successful repair is not AEG value
unless the trace supports a material path change. Perceived usefulness is a
separate 1–5 rating.

Where feasible, identical isolated snapshots use the same agent configuration:
a delayed-retrieval control finishes without AEG output before the treatment
queries AEG and begins diagnosis. Any leakage invalidates the comparison. An
unpaired task may support observed path-change evidence but no causal efficiency
claim.

## Decision rule

Success requires at least three uncontaminated tasks, at least two
observable-value tasks, at least one relevant recommendation that changes the
path and passes the frozen oracle, recommendation correctness of at least 0.67,
abstention correctness of at least 0.80, zero misleading retrievals, median
usefulness of at least 4 on observable-value tasks, and no critical boundary
breach. Denominators that do not occur are reported as unavailable, not 100%.

Failure includes one materially harmful misleading retrieval, fewer than two
observable-value tasks after five evaluable tasks, no recommendation that both
changes the path and passes the oracle, the preregistered low correctness or
usefulness thresholds, or any critical privacy, consent, authorization,
provenance, or verified-library violation. A sample below three or evidence only
about latency/tokens is inconclusive.

## Promotion boundary

This experiment cannot directly promote an experience. Any candidate must first
show independent external reuse by a separate user and task, pass an objective
oracle, retain authorized provenance, pass privacy review, and receive separate
human approval for the exact `experiences/verified.json` change.
