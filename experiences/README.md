# Verified shared experiences

This directory is the public, reusable experience library for Agent Experience
Graph. Unlike `assets/example_traces.json`, these records describe work that was
actually executed and verified.

Each library file is a JSON array compatible with
`references/trace_schema.md`. Records may add provenance, verification, metrics,
and retrieval metadata when those fields make the experience easier to audit and
reuse. `verified-experience.schema.json` defines this verified-experience
extension; `scripts/validate_verified_experiences.py` enforces unique IDs,
cross-field relationships, regression disclosures, and redaction rules that
JSON Schema cannot express.

## Retrieve an experience

```bash
python3 scripts/recommend_traces.py \
  --traces experiences/verified.json \
  --query '{"task":"repair duplicated JSONL event metrics"}'
```

Matches include explainable evidence naming the contributing trace field,
query phrase, matched phrase, lexical similarity, and weighted contribution.
`reuse.retrievalTags` and `reuse.recommendedFor` participate directly in
ranking. Constraints contribute only when the query supplies constraints.

## Validate the library

```bash
npx --yes ajv-cli@5.0.0 validate --all-errors \
  -s experiences/verified-experience.schema.json \
  -d experiences/verified.json
python3 scripts/validate_verified_experiences.py
python3 experiments/public-repair-lab/validate_paired_results.py
```

Experiment evidence and promotion evidence are separate. Experiment evidence
points to sanitized, recomputable trial data. Promotion evidence identifies the
workflow and how to resolve the run for the commit containing the record; it
does not hard-code a workflow run that validated an older commit.

## Promotion requirements

Store an experience here only when it:

- has an objective success, partial, or failure outcome;
- links to public provenance or describes a locally reproducible verification;
- preserves reusable steps, constraints, and negative evidence;
- contains no credentials, secrets, private user data, raw conversations, or
  proprietary source;
- summarizes logs and patches instead of copying them wholesale;
- states important regressions and limitations alongside improvements.
- separates experiment evidence from CI promotion evidence;
- uses `null` plus an explanation for metadata the original run did not capture.

Use stable IDs and append new records to `verified.json`. A corrected record may
replace an older record with the same ID when its provenance and lessons remain
the same logical experience.
