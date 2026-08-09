# Verified Experience Challenge: Phase 1 preregistration

Status: **proposed; do not recruit or execute**.

## Question and offer

Can verified, reusable agent experience provide observable value on current,
real developer tasks while abstaining when the library has nothing relevant?

> Bring one real coding problem. We will test whether a reusable, verified
> agent experience helps your coding agent solve it with less effort or better
> reliability.

The sample is three to five seed developers, one task each, and five tasks at
most. Stage A stops after at most three participants/tasks for mandatory human
review. Stage B may add at most two only after a separate recorded approval;
continuation is never automatic. Eligible participants already use a coding agent, contribute to public
open source, and have a current reproducible bug, failing test, migration, or CI
problem. Close friends and relationships that inhibit negative feedback are
excluded. Mass outreach, scraping, paid acquisition, and unsolicited automation
are prohibited.

## Sequence

1. Obtain separate recruitment, participant-task execution, evidence-retention,
   and model-cost approvals that are still pending in `approval-record.json`.
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
10. Stop after three Stage A tasks for mandatory review. Stage B requires its
    own approval after that review; result publication and experience promotion
    remain separate decisions.

## Outcome classification

Retrieval is classified as a relevant recommendation, correct abstention,
irrelevant retrieval, or misleading retrieval. Repair is classified separately:
oracle pass with a material AEG path change, oracle pass independent of AEG,
oracle failure, or not executed/excluded. A successful repair is not AEG value
unless the trace supports a material path change. Perceived usefulness is a
separate 1–5 rating and cannot establish success alone. Correct abstention is
valuable calibration evidence only; a successful repair after abstention is an
independent success, not an AEG-assisted success.

A relevant recommendation is above the frozen threshold and independently
judged applicable to the frozen failure mechanism before outcome review. A
material path change requires timestamped evidence that retrieval preceded
diagnosis, influenced a subsequently executed action, and that action passed the
frozen oracle. A misleading retrieval is materially inapplicable, incorrect, or
unsafe guidance that influences or would reasonably influence a repair action.
Any contaminated execution is a protocol violation and experiment-level stop.

Recommendation correctness is `correct relevant recommendations / all
above-threshold recommendations` on uncontaminated tasks. Abstention correctness
is `independently confirmed correct abstentions / all abstentions` on
uncontaminated tasks. Reports always show both integer counts and the ratio. A
zero denominator is `0/0, N/A`, never success.

Where feasible, identical isolated snapshots use the same agent configuration:
a delayed-retrieval control finishes without AEG output before the treatment
queries AEG and begins diagnosis. Any leakage invalidates the comparison. An
unpaired task may support observed path-change evidence but no causal efficiency
claim.

## Decision rule

The experiment may be labeled **initial positive signal** only with at least
three uncontaminated completed tasks, at least two objectively verified user
value tasks, at least one above-threshold recommendation that materially changes
the path and passes the frozen oracle, zero misleading retrievals, median
usefulness of at least 4/5, and all authorization, privacy, freshness, and
retrieval-timing gates passing. This is not PMF, generalized effectiveness,
causal superiority, or commercial demand.

One materially harmful recommendation, critical privacy breach, unauthorized
action, or contaminated execution stops the experiment. Outcomes are classified
separately as initial positive signal, positive retrieval signal,
calibration/abstention evidence only, inconclusive, protocol failure, harmful or
misleading retrieval, or privacy/authorization failure. Latency, tokens,
commands, interventions, or participant ratings alone cannot establish success.

Absolute ceilings are five tasks, 40 model calls, 200 commands, 100 test
executions, 40 human interventions, 15 hours, 1,000,000 tokens, and USD 100.
Per-task soft limits are six model calls, 30 commands, 15 test executions, six
interventions, and two hours. A crossing is recorded and explained before
continuation; it never increases an absolute budget.

## Promotion boundary

This experiment cannot directly promote an experience. Any candidate must first
show independent external reuse by a separate user and task, pass an objective
oracle, retain authorized provenance, pass privacy review, and receive separate
human approval for the exact `experiences/verified.json` change.
