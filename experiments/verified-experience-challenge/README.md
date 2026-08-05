# Verified Experience Challenge

This bundled, zero-cold-start challenge demonstrates AEG's narrow v0.1.3
product loop:

1. describe a debugging task;
2. inspect an explainable match from the verified-only library;
3. copy a compact recovery capsule into a coding-agent session;
4. validate the agent's repair locally;
5. rate the retrieved experience locally.

It is a synthetic transfer challenge, not a new natural cross-project
benchmark. Its fixture is the existing
`public-repair-lab/tasks/protocol-resource-delegation` task, derived from the
same abstraction-boundary failure family as verified experience TR-04 but with
different names and code.

## Try it in VS Code

Install AEG v0.1.3, open this repository, and run **AEG: Open Verified
Experience Challenge**. The prefilled task deliberately does not reveal the
repair location or solution. Select the TR-04 match, inspect **Why this
matched**, and copy the capsule before asking your coding agent to repair:

```text
experiments/public-repair-lab/tasks/protocol-resource-delegation/fixture
```

Run the objective test from that directory:

```bash
python3 test_bug.py
```

Do not edit or weaken the test. Treat the capsule as a hypothesis and inspect
the local code before changing it. Ratings are stored only in
`.aeg/verified-experience-feedback.json`.

## What prior evidence says

The previously published one-pair comparison is negative evidence, not a
benefit claim. Baseline and assisted arms both succeeded in one attempt, used
four commands and two test executions, followed the same repair path, and
produced identical patches. The assisted arm used 13,842 more non-cached tokens
and took 4,288 ms longer. See
`public-repair-lab/results/tr-04-protocol-transfer-pair.json`.

This challenge therefore demonstrates discoverability, verified-only
retrieval, provenance, explainability, guardrails, and local feedback. It does
not demonstrate that retrieval improved repair correctness or efficiency.
