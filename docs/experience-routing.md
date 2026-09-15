# Dynamic Experience Routing

AEG is evolving from an experience store that is read up front into an experience layer that can be consulted on demand.

This document records the current product hypothesis. It is a design and evaluation target, not a claim that every runtime or Registry surface already implements dynamic routing.

## Product principle

**Long working context, sparse external experience.**

A complex task may need a large working context containing the task's own code, state, plans, files, tool results, and prior actions. That does not imply that large amounts of external historical experience should be injected at task start.

External experience should be loaded only when the current task provides a strong reason to consult it, for example a recognizable failure signature, an uncertainty boundary, a repeated retry pattern, an environment/version mismatch, or a high-cost decision point.

The router must be allowed to abstain. "No relevant verified experience" is a correct outcome.

## Two-layer experience contract

Each reusable experience should be separable into a compact descriptor and a fuller payload.

### Experience descriptor

The descriptor exists to decide whether the experience is worth loading. It should remain short enough to rank or inspect cheaply.

Recommended descriptor fields:

- **concise trigger** — the narrow condition that should cause this experience to be considered;
- **task/failure signature** — symptoms, error signatures, task family, or mechanism that identifies the situation;
- **applicability** — where the experience applies and explicit exclusions;
- **provenance/confidence** — source, verification state, and confidence/evidence level;
- **cost/risk hints** — known negative-transfer risk, staleness, or expensive prerequisites when available.

Descriptors should avoid broad wording that causes unrelated experiences to enter context.

### Full experience payload

The payload is loaded only after the descriptor is selected or explicitly requested. It may contain:

- failed approaches and why they failed;
- recovery principle or reusable lesson;
- evidence and verification method;
- constraints and environment/version details;
- validation outcome and measured regressions;
- limitations, stale conditions, and negative evidence;
- provenance details and replay/transfer evidence.

The payload should guide local investigation, not prescribe a rigid model-specific recipe unless the evidence shows that the exact recipe is necessary.

## Preferred runtime flow

```text
Task starts with minimal external experience
        |
        v
Agent works with its task-local context
        |
        v
Failure / uncertainty / decision signal
        |
        v
AEG router evaluates compact descriptors
        |
   +----+----+
   |         |
abstain   strong match
             |
             v
    expose descriptor + evidence
             |
             v
 load full payload only if useful
             |
             v
      validate locally
             |
             v
 continue / adapt / reject experience
             |
             v
 record retrieval usefulness and outcome
```

The initial trigger can be agent-initiated, tool-initiated, or policy-initiated. AEG should not assume that task-start retrieval is always optimal.

## Evaluation plan

When infrastructure allows, compare at least these strategies on the same frozen task family:

1. **Baseline** — no prior experience.
2. **Up-front experience** — relevant experience supplied at task start.
3. **Dynamic retrieval** — experience available on demand during execution.
4. **Dynamic retrieval with abstention policy** — retrieval occurs only above an explicit trigger/confidence threshold.

Measure correctness first, then cost and behavior:

- objective success / partial / failure;
- commands and tool calls;
- token usage;
- wall time;
- retries;
- irrelevant retrievals;
- harmful steering / negative transfer;
- retrieval trigger precision and false-trigger rate when measurable;
- whether retrieval changed the repair path or merely restated a solution the model already found.

A single successful retrieval is experience evidence, not evidence that the routing policy improves agents generally.

## Registry implications

The public Registry should increasingly optimize for two different consumers:

- **router/index consumer** — needs compact descriptors, applicability, evidence level, and abstention-safe ranking signals;
- **agent/human consumer** — needs the full evidence-backed payload after selection.

Existing Registry records remain valid. Schema changes should be backward-compatible until the descriptor layer has enough evidence to justify making fields mandatory.

## Research questions

Current open questions include:

- Which signals should trigger experience lookup: task intent, error signatures, retries, evaluator feedback, tool state, or model uncertainty?
- How much descriptor information is sufficient for routing without leaking the full payload into context?
- When should a complex task use long task-local context but still keep external experience sparse?
- When does a stronger model make retrieval unnecessary?
- How should confidence decay under model, dependency, environment, or policy drift?
- Can the system learn when *not* to retrieve from helpful, neutral, irrelevant, and harmful outcomes?

These questions are part of AEG's evidence program and should be answered through controlled experiments rather than product claims.
