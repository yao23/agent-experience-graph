# AEG v0.1.6 product-proof preparation

Status: **prepared only; not frozen; 0/3 arms executed**.

This directory prepares one bounded three-arm test of the v0.1.6 product hypothesis: whether a top-1 verified capsule changes the outcome or effort on a naturally occurring public repair when compared with both no added context and fixed generic debugging advice.

It does not authorize or run a model, spend money, select a target, inspect a human patch, or change the verified library.

## Three arms

1. **Baseline:** the frozen public task, code, failure, budget, and objective checks; no AEG records or added advice.
2. **Fixed generic:** identical inputs plus [`generic-advice.txt`](generic-advice.txt); no AEG record access.
3. **AEG top-1:** identical inputs plus only the automatically retrieved and frozen top-1 guarded capsule.

Model, settings, prompt template, budget, environment, focused checks, regression checks, and evaluation are identical. The intentional context difference is the arm definition above.

## Freeze gate before any execution

A separate authorized phase must freeze all currently `null` fields in [`protocol.json`](protocol.json) before an arm can run:

- a naturally occurring target from a predeclared candidate pool in a public repository with an explicit license;
- repository and buggy commit, task hash, objective check hashes, and freeze time before inspecting its human patch;
- a source experience whose timestamp predates the target;
- verified-library hash, fixed 0.0500 threshold, retrieval score, top-1 experience, and guarded-capsule hash;
- identical model, settings, prompt template, budget, oracle, and randomized arm order.

Exclude eBay, private, internal, proprietary, credentialed, or capsule-derived targets. If no verified result clears the frozen threshold, record a retrieval abstention and stop without executing any arm.

Each arm must use a separate sanitized repository and worktree directory with no shared Git metadata, writable cache, AEG access for controls, human patch, other-arm artifacts, or evaluator feedback.

## Results

[`result.schema.json`](result.schema.json) requires:

- success, attempts, completed sanitized commands, and test executions;
- focused and regression check results;
- non-cached tokens and duration;
- repository-relative files inspected and changed;
- patch hash and identical-setting hashes;
- limitations, protocol deviations, and a privacy attestation.

Publish negative, neutral, abstention, and protocol-deviation outcomes. Do not publish code, prompts, task text, raw logs, ratings, receipts, or private data. Do not change thresholds or outcome rules after observing a result.

## Validation only

The extension test suite validates both experiment schemas and checks valid completed, abstention, missing-measurement, and wrong-arm-order cases:

```bash
cd integrations/vscode
npm test
```

This command does not execute an experiment arm.

## Evidence boundary

AEG currently contains two verified records in two narrow task families. The bundled challenge demonstrates the interaction flow, not a performance benefit. Prior controlled and transfer evidence was neutral or negative. Nothing in this preparation supports a claim of improved success, speed, cost, PMF, adoption, or generalization.
