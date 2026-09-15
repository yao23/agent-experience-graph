# Defensive OSS Experience Strategy

## Decision

AEG will treat authorized public OSS maintenance as a source of real,
objectively testable experience while remaining a model-neutral evidence layer.
It will not reposition as a general AI security platform or compete with model
providers on raw memory, tracing, identity, authorization, or runtime controls.

The concise product distinction is:

> Model memory remembers what happened. AEG tests what should be reused.

## Why this wedge is useful

Public OSS maintenance can supply the elements that AEG needs for credible
evidence:

- an independently originated problem;
- immutable source revisions and public provenance;
- a local failure that can be reproduced without private data;
- a discriminating test or build oracle;
- a minimal repair and regression test;
- external maintainers or users who can later replay the result;
- related future tasks on which portability can be tested.

OpenAI's public "Defender's Window" guidance asks labs, enterprises and
maintainers to share validated findings, fixes and practical playbooks so that
one discovery can strengthen the wider ecosystem. Its recommended repair loop
also emphasizes validation, focused patches, regression tests and confirmation
that the issue no longer reproduces. These statements are market evidence for
the importance of reusable, verified maintenance knowledge; they are not
evidence that AEG already improves agent performance.

Sources:

- https://openai.com/index/the-defenders-window/
- https://openai.com/index/daybreak-for-frontline-defenders/
- https://openai.com/index/gpt-6-astra/

## Scope boundary

The first wedge is software reliability, not offensive security:

| In scope under an applicable execution policy | Out of scope without a new policy |
| --- | --- |
| Deterministic CI or package failures | Vulnerability discovery or exploit development |
| Dependency and framework migration | Authentication, authorization or permission repair |
| Test-framework migration and regression gaps | Production access or deployment |
| Resource lifecycle and cross-module regressions | Private infrastructure or customer data |
| Misleading suite-green repairs | Credential handling or irreversible external action |
| Version and environment drift | Unbounded flaky/network investigations |

Every actual run remains governed by the current authorization. This strategy
document cannot add repositories, models, paid calls, case starts, publication
rights or scheduler capacity.

## Evidence contract

An OSS case is valuable to the Registry only when the public-safe record can
separate these claims:

1. **Reproduction:** the intended defect was observed at a frozen revision.
2. **Local repair validity:** the same discriminating oracle fails before and
   passes after the repair for the intended reason.
3. **Regression coverage:** relevant broader checks do not reveal new failures.
4. **Upstream disposition:** adoption, rejection or no response is recorded
   independently from technical validity.
5. **Transfer:** a separately originated task is run without evaluator leakage.
6. **External replay:** another actor's evidence is recorded at its supported
   testimony level and does not automatically establish transfer.

Rejected repairs, inapplicability, abstention, regressions and inconclusive
results remain first-class evidence.

## Strong-model question

GPT-6 Astra creates a useful falsification test for AEG:

> When the model becomes materially stronger, does a verified prior Experience
> still improve correctness or the repair path, or does it become unnecessary
> or harmful context?

The proposed `model-strength-transfer-v1` protocol compares control and
AEG-assisted runs for Astra, GPT-5.6 Sol and one external model on the same
frozen task. It is preparation-only until a separate authorization supplies
model access, fresh-context isolation, budget and case-start allowance.

## Near-term success criterion

The north-star is not the number of traces collected. It is the count of
independently originated cases whose Experience is:

- objectively verified;
- correctly attributed and public-safe;
- replayable from immutable evidence;
- tested for portability;
- useful, neutral, harmful or inapplicable with that outcome disclosed.
