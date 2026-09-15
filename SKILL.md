---
name: agent-experience-graph
description: Use when an agent should learn from prior task-solving traces, recommend tools or skills for a new decomposed task, record reusable execution experience, or compare current subtasks with solved tasks from other agents.
version: 0.1.3
metadata:
  short-description: Learn tools and skills from prior agent traces
  openclaw:
    requires:
      bins:
        - python3
    homepage: https://github.com/yao23/agent-experience-graph
---

# Agent Experience Graph

This is a portable agent capability, not a runtime-specific plugin. It should work in any agent environment that can read markdown instructions and run Python 3 scripts. Runtime-specific metadata lives outside this file:

- `capability.json`: neutral capability manifest for launchers, registries, and importers
- `agents/openai.yaml`: Codex UI metadata
- `adapters/README.md`: install notes for Codex, Claude Code, OpenClaw, Hermes, and generic agents

Use this skill to turn prior agent runs into reusable guidance for new tasks. The preferred operating principle is **long working context, sparse external experience**: keep whatever task-local context a difficult job needs, but avoid injecting large amounts of historical experience unless the current state provides a strong reason to retrieve it.

The target loop is:

1. Describe the current task and likely subtasks.
2. Start with minimal external experience unless a strong match is already known.
3. When the task hits a recognizable failure, uncertainty, retry pattern, environment mismatch, or costly decision point, evaluate compact experience descriptors.
4. Abstain when no descriptor is a strong fit; `No relevant verified experience` is a correct result.
5. For a selected experience, inspect provenance, applicability, exclusions, and limitations before loading the fuller payload.
6. Treat the payload as evidence and a hypothesis to validate locally, not as a guaranteed answer or rigid recipe.
7. After the task, record a sanitized outcome so future routing can learn from helpful, neutral, irrelevant, harmful, stale, and failed reuse.

See `docs/experience-routing.md` for the two-layer descriptor/payload design and evaluation plan.

## Quick Workflow

Create a query with a task and optional subtasks:

```json
{
  "task": "Build an ingestion pipeline for markdown API docs",
  "subtasks": [
    {"description": "Parse markdown into structured sections"},
    {"description": "Chunk content for coding-agent retrieval"},
    {"description": "Evaluate extracted endpoint metadata"}
  ]
}
```

Run the bundled recommender against a trace file:

```bash
python3 scripts/recommend_traces.py \
  --traces experiences/verified.json \
  --query query.json
```

Use `assets/example_traces.json` for demonstrations. Prefer
`experiences/verified.json` when recommendations should come from executed,
publicly auditable work.

Use the output as evidence, not as an order. Prefer recommendations with:

- successful or partially successful outcomes
- matched subtasks or failure signatures, not only matched task titles
- narrow applicability and explicit exclusions
- clear lessons or failure notes
- provenance and verification that justify confidence
- skills/tools that are available in the current environment

For explainability, inspect each match's `evidence` array. It identifies the
task, subtask, reuse tag, recommended-use phrase, skill, tool, or relevant query
constraint that contributed to the score. Verification status and numeric
metrics do not add lexical relevance.

When a runtime supports dynamic tool use, prefer exposing retrieval as an on-demand capability instead of automatically prepending full historical payloads to every task. Up-front retrieval remains an experiment arm, not the assumed optimum.

## Recording A Trace

After finishing a task, create a compact trace with no secrets, credentials, private user data, or proprietary snippets. Keep enough detail to support future retrieval:

```json
{
  "id": "trace-2026-05-18-doc-ingestion",
  "task": "Build a structured ingestion demo for API documentation",
  "outcome": "success",
  "subtasks": [
    {
      "description": "Normalize markdown into sections",
      "skills": ["structured-ingestion"],
      "tools": ["python"],
      "outcome": "success",
      "lessons": ["Preserve headings and code blocks before chunking."]
    }
  ],
  "skills": ["structured-ingestion"],
  "tools": ["python", "ripgrep"],
  "lessons": ["Chunk metadata improves downstream retrieval."]
}
```

Append it to an existing trace library:

```bash
python3 scripts/recommend_traces.py \
  --traces traces.json \
  --append-trace new_trace.json
```

For verified shared experiences, structure the reusable information conceptually in two layers:

- **Descriptor:** concise trigger, task/failure signature, applicability/exclusions, provenance/confidence, and known staleness or negative-transfer risk.
- **Payload:** failed approaches, recovery principle, evidence, constraints, validation outcome, limitations, regressions, and detailed provenance.

Existing Registry records remain valid while this model is introduced incrementally.

## Interpretation Rules

- Similarity is a hint. Always check whether the prior environment, constraints, and outcome match the current task.
- Retrieval is optional. Do not force an experience into context merely because one is available.
- Prefer narrow triggers over broad descriptions that cause unrelated experience to be loaded.
- A tool appearing in a trace does not prove it caused success. Prefer tools attached to matched successful subtasks.
- Preserve negative evidence. Failed traces and rejected approaches are useful when their lessons explain what to avoid.
- Avoid turning a prior successful trajectory into a rigid step-by-step recipe unless the evidence shows the exact sequence is necessary.
- When traces disagree, choose the recommendation with the closest mechanism/applicability match and the best outcome evidence; abstain if the evidence is weak.
- Do not expose raw traces from private workspaces. Share redacted summaries or derived recommendations.
- When evaluating AEG, separate task-local context size from external experience retrieval. A large task may need long working context while still benefiting from sparse external experience.

## Trace Schema

For field definitions and an example trace library, read `references/trace_schema.md` when creating new datasets, validators, or import/export adapters.
Executed public records additionally follow
`experiences/verified-experience.schema.json` and the semantic promotion rules
in `experiences/README.md`.

The descriptor/payload split is currently a forward-looking routing contract documented in `docs/experience-routing.md`; schema evolution should remain backward-compatible until controlled evidence justifies mandatory descriptor fields.
