# Verified shared experiences

This directory is the public, reusable experience library for Agent Experience
Graph. Unlike `assets/example_traces.json`, these records describe work that was
actually executed and verified.

The same canonical `verified.json` records generate the public
[`/experiences/`](index.html) Registry, its human detail pages, copyable
Markdown and Agent instructions, the machine index at `index.json`, and one
complete JSON endpoint per published Experience under `data/`. See
[`docs/experience-registry.md`](../docs/experience-registry.md) for generation,
measurement, and contribution boundaries.

Each library file is a JSON array compatible with
`references/trace_schema.md`. Records may add provenance, verification, metrics,
and retrieval metadata when those fields make the experience easier to audit and
reuse. `verified-experience.schema.json` defines this verified-experience
extension; `scripts/validate_verified_experiences.py` enforces unique IDs,
cross-field relationships, regression disclosures, and redaction rules that
JSON Schema cannot express.
The schema accepts both paired A/B metrics and bounded single-repair collection
metrics; a single repair is experience evidence, not causal evidence of AEG
improvement.

## Evidence labels

- **Candidate** records are sanitized but remain outside `verified.json` until
  their outcome and provenance satisfy promotion validation.
- **Verified experience** means the recorded repair or experiment has an
  objective, reproducible outcome. It does not by itself mean AEG caused an
  improvement.
- **Replay evidence** reproduces the source task and confirms that the lesson
  still describes a valid repair.
- **Cross-task reuse evidence** evaluates a non-identical transfer task. It may
  be positive, neutral, or negative.
- **Cross-project evidence** requires a transfer into a different public
  project; AEG v0.1.3 does not yet have this evidence.
- **Causal AEG evidence** requires a controlled comparison where retrieval is
  the intentional difference. The current bounded comparisons did not improve
  correctness and must not be presented as generalized benefit.

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
points to sanitized, recomputable trial data. Promotion evidence identifies an
observed workflow run and its exact validated commit. That commit must contain
the promoted record; later wording or product changes do not rewrite the
historical promotion event.

For the canonical `experiences/verified.json` library, every declared evidence
artifact must be a repository-relative path that stays inside the repository
and resolves to a regular file. Validation of a portable candidate supplied via
`--library` checks record semantics without assuming the AEG repository layout.

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
