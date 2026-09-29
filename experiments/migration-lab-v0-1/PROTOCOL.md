# AEG Migration Lab v0.1

## Purpose

The Migration Lab is the narrow proving ground for AEG.

The first question is deliberately small:

> Can verified experience from previous React 18 -> React 19 migrations make the same agent materially more efficient on the next independent migration without reducing correctness?

This phase does **not** attempt to prove a general Agent Experience Graph, general bug-fixing value, CI value, consumer-agent value, or product-market fit.

The initial migration family is **React 18 -> React 19**.

## Why this wedge

Major-version migrations have properties that are unusually useful for experience-transfer experiments:

- the same migration family recurs across independent repositories;
- a large deterministic core is already handled by docs/codemods/tools, leaving a project-specific last mile;
- builds, typechecks, unit tests and integration tests often provide objective oracles;
- successful and failed paths can be frozen and replayed;
- experience can be represented as a compact map plus triggered evidence rather than a large raw trajectory.

The experiment is intentionally designed around the hypothesis that experience primarily reduces unnecessary search.

## Core hypotheses

### H1 — Correctness-preserving transfer

A compact, verified migration experience can improve or preserve migration success on an independent target compared with a fresh agent using the repository and public documentation alone.

### H2 — Search reduction

When correctness is equal, useful prior experience reduces exploration such as:

- files opened/read;
- repository searches;
- shell/tool commands;
- failed hypotheses or reverted edits;
- test/build reruns;
- files changed;
- wall-clock time;
- model tokens, when observable.

Report the raw metrics and per-metric deltas. Do not collapse them into a single opaque efficiency score.

For a metric where lower is better, a descriptive search-reduction ratio may be reported as:

`SRR(metric) = 1 - treatment_metric / baseline_metric`

Only calculate it when the baseline is non-zero and the two runs are comparable.

### H3 — Dynamic evidence beats context dumping

A small high-level migration map plus evidence retrieved only after a discriminating trigger may outperform both:

1. no prior experience; and
2. a compact skill supplied up front without triggered retrieval.

This is the most important architectural hypothesis for AEG v0.1.

## Experimental arms

### A — Baseline / no experience

Input:

- frozen repository revision;
- migration goal;
- neutral public documentation access, when allowed by the task manifest;
- fixed environment and resource budget.

Do not provide AEG migration experience.

### B — Compact skill

Provide the same baseline inputs plus a frozen compact experience.

The compact experience should contain only:

- **Map** — major migration stages / invariants;
- **Triggers** — recognizable error or symptom classes;
- **Validation** — what must be checked before completion;
- **Applicability / exclusions** — when the experience should or should not be used.

Do not provide the full source trajectory by default.

### C — Compact skill + dynamic evidence

Provide the same compact skill as B.

Detailed evidence is initially withheld. The solver may retrieve a small evidence payload only after a trigger appears, for example:

- compiler/type error fingerprint;
- build failure signature;
- test failure category;
- dependency incompatibility;
- deprecated API usage;
- runtime warning.

Record every retrieval trigger, payload selected, whether it changed the path, and whether it was helpful, irrelevant or harmful.

## Cross-case learning rule

Case N may generate or refine experience only **after** its terminal evidence has been recorded.

That frozen experience may be used on Case N+1.

Do not inspect a target, then rewrite the treatment experience using the target answer.

This rule is more important than maximizing the number of runs.

## Target admission

Prefer public repositories that satisfy most of the following:

- React 18 is present at the frozen source revision;
- the project can plausibly migrate to React 19;
- package manager and lockfile are present;
- deterministic build/typecheck/test commands exist;
- the repository is small or medium enough for a bounded <=90 minute local run;
- the target exposes more than a trivial package-version edit;
- no security, auth, payment, production-deployment or private-infrastructure work is required;
- the oracle can distinguish a real migration from a vacuous green result.

A valid case should freeze:

- repository URL;
- source revision;
- package manager;
- Node/runtime version;
- dependency snapshot or lockfile;
- migration goal;
- predeclared verification commands;
- environment assumptions;
- exclusion conditions.

## Initial sample

Aim for **3-5 independent public repositories**.

This is not a quota. One clean paired case is more useful than several contaminated or incomparable runs.

Prefer diversity in application shape only after the first valid case is complete. Avoid broad framework expansion during v0.1.

## Experience representation

Each reusable experience should be small enough to read quickly and structured like this:

### Map

The minimum ordered mental model for the migration.

### Trigger -> interpretation -> next evidence

Example shape:

```yaml
trigger:
  kind: compiler_error
  fingerprint: "<normalized signature>"
interpretation:
  likely_issue: "<migration issue class>"
retrieve:
  evidence_id: "<small evidence payload>"
validation:
  - "<specific check>"
```

### Evidence

Detailed evidence is kept separately from the compact map and fetched only when needed.

Evidence may include:

- public documentation excerpt references;
- sanitized prior error fingerprints;
- minimal patch pattern;
- commands that disambiguated a hypothesis;
- rejected approach and why it failed;
- version-specific applicability.

### Validation

Define completion independently from the solver's own confidence.

A migration is not successful merely because files were edited or the agent says it is done.

## Correctness gate

At minimum, use the strongest available deterministic checks from:

- dependency install / lock integrity;
- typecheck;
- unit tests;
- integration tests;
- production build;
- focused regression tests for migrated behavior.

A green test suite is not enough if it does not exercise the migrated behavior.

Setup failure unrelated to the migration is **BLOCKED**, not a migration failure.

## Telemetry

For each run record, when observable:

- arm;
- fresh-context identifier;
- start/end time;
- commands executed;
- repository searches;
- files read;
- files changed;
- failed attempts;
- reverted edits;
- build/typecheck/test invocations;
- passed/failed checks;
- tokens;
- wall time;
- experience payload bytes/tokens;
- retrieval trigger count;
- relevant/irrelevant/harmful retrieval count;
- human intervention;
- stop reason.

Unknown values remain UNKNOWN.

## Contamination control

Compared arms must use fresh non-inheriting contexts.

The solver must not receive:

- another arm's patch;
- another arm's logs;
- evaluator notes;
- target answer-bearing queue fields;
- hidden expected diffs;
- post-fix source unless the protocol explicitly defines it as evaluator-only evidence.

The coordinator/evaluator may hold the oracle. The solver should receive only the solving inputs appropriate to its arm.

## Public/private boundary

The user's private/employer material is out of scope.

In particular:

- do not copy or reconstruct the eBay React 19 skill;
- do not use eBay code, logs, Confluence, internal GitHub or internal test failures;
- do not treat personal recollection of an internal exact fix as target-specific evidence.

The user's prior experience may motivate the hypothesis and metrics, but v0.1 evidence must be independently reproducible from public sources.

## Resource limits

Carry forward conservative local limits unless the operator explicitly changes them:

- max one local consumer at a time;
- max one case/task per invocation;
- max 90 agent-minutes per case;
- max 120 local agent-minutes per local day;
- max 600 local agent-minutes per rolling seven days;
- cash increment $0;
- existing model/subscription only;
- no global agent/plugin installation.

## Publication

The lab may write public-safe experiment artifacts only to the dedicated branch.

It may not, without separate approval:

- comment upstream;
- create an upstream PR;
- send messages;
- publish social content;
- merge to main;
- release/deploy.

## v0.1 outputs

Use:

- `coordination/migration-lab-v0-1/queue.json` — candidate and execution queue;
- `coordination/migration-lab-v0-1/reports/` — sourcing/coordination summaries;
- `coordination/migration-lab-v0-1/receipts/` — local CLAIM/RESULT receipts;
- `coordination/migration-lab-v0-1/evidence/` — public-safe run evidence;
- `experiments/migration-lab-v0-1/experiences/` — frozen compact experiences and evidence payloads.

Do not rewrite historical evidence from prior AEG pilots.

## v0.1 success signal

The first meaningful result is not "React 19 migration works."

It is a clean observation that, on an independent target and under comparable conditions:

1. correctness is preserved;
2. prior verified experience changes the solving path;
3. unnecessary exploration measurably decreases, or a clear counterexample shows that it does not;
4. the result is reproducible and its applicability boundary is explicit.

Negative or null results are valid outcomes.
