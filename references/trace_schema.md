# Trace Schema

A trace is a sanitized summary of one agent attempt. It should be small enough for retrieval and specific enough to support skill/tool recommendations.

## Trace Fields

- `id` string, required: stable identifier.
- `task` string, required: human-readable goal.
- `outcome` string, required: `success`, `partial`, or `failure`.
- `subtasks` array, recommended: decomposed work units with local evidence.
- `skills` array, recommended: skills used across the task.
- `tools` array, recommended: tools used across the task.
- `constraints` array, optional: environment, policy, cost, latency, or compatibility constraints.
- `lessons` array, optional: reusable observations.

## Subtask Fields

- `description` string, required: what the agent tried to accomplish.
- `skills` array, optional: skills that helped or were attempted.
- `tools` array, optional: tools that helped or were attempted.
- `outcome` string, optional: `success`, `partial`, or `failure`.
- `lessons` array, optional: local insight, including warnings.

## Example Library

```json
[
  {
    "id": "trace-api-doc-ingestion",
    "task": "Build an ingestion pipeline for markdown API docs",
    "outcome": "success",
    "subtasks": [
      {
        "description": "Parse markdown into structured sections",
        "skills": ["structured-ingestion"],
        "tools": ["python"],
        "outcome": "success",
        "lessons": ["Keep headings, examples, and auth hints attached to the same section."]
      }
    ],
    "skills": ["structured-ingestion"],
    "tools": ["python", "ripgrep"],
    "lessons": ["Structure-aware chunks give agents better retrieval context than raw text slices."]
  }
]
```

## Redaction Rules

- Remove secrets, credentials, user data, proprietary source snippets, and raw customer content.
- Prefer abstracted lessons over full prompts or full command output.
- Keep enough fields to explain why a skill or tool recommendation is relevant.

## Verified-experience extension

`experiences/verified-experience.schema.json` extends this compact retrieval
schema for executed, publicly auditable records. It requires structured public
source provenance, separate experiment and promotion evidence, verification
evidence, numeric paired aggregates, retrieval metadata, and explicit
limitations. The base fields above remain unchanged, so verified experiences
remain consumable by the same recommender.

JSON Schema validates record shape and types. The semantic validator at
`scripts/validate_verified_experiences.py` additionally enforces unique IDs,
evidence consistency, regression/no-success-rate disclosures, and public-data
redaction rules.
