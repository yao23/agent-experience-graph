# Verified shared experiences

This directory is the public, reusable experience library for Agent Experience
Graph. Unlike `assets/example_traces.json`, these records describe work that was
actually executed and verified.

Each library file is a JSON array compatible with
`references/trace_schema.md`. Records may add provenance, verification, metrics,
and retrieval metadata when those fields make the experience easier to audit and
reuse.

## Retrieve an experience

```bash
python3 scripts/recommend_traces.py \
  --traces experiences/verified.json \
  --query '{"task":"validate a repeatable agent repair experiment in CI"}'
```

## Promotion requirements

Store an experience here only when it:

- has an objective success, partial, or failure outcome;
- links to public provenance or describes a locally reproducible verification;
- preserves reusable steps, constraints, and negative evidence;
- contains no credentials, secrets, private user data, raw conversations, or
  proprietary source;
- summarizes logs and patches instead of copying them wholesale;
- states important regressions and limitations alongside improvements.

Use stable IDs and append new records to `verified.json`. A corrected record may
replace an older record with the same ID when its provenance and lessons remain
the same logical experience.
