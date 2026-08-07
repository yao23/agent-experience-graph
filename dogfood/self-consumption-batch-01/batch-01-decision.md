# Batch 01 decision record

Decision date: 2026-08-07.

Batch 01 provides technical feasibility evidence and limited external-usefulness evidence. Seven bounded tasks produced objective local or historical checks, sanitized candidate records, and one accepted product-correctness repair. This shows that AEG can support disciplined retrieval, abstention, execution, and evidence recording; it does not show that the results generalize.

## Evidence decision

- **Technical feasibility:** all seven categories produced bounded evidence. Five execution-state projects completed and two remained partial. The recorded checks include deterministic tests, before/after oracles, schema validation, permission-boundary probes, repeatable ETL output, and validator regression coverage.
- **Retrieval usefulness:** one valid pre-execution recommendation was reused in Category 03 and changed the selected repair path. The target was synthetic and there was no baseline arm, so this is mechanism-level transfer evidence rather than a causal efficiency result.
- **Correct abstention:** four abstentions were procedurally valid because AEG was queried before execution in Categories 01, 02, 04, and 07. They are evidence that the sparse library did not force weak matches, not evidence of task improvement.
- **Contaminated or non-blind results:** Categories 05 and 06 queried AEG after execution; their retrieval-effect evidence is invalid/procedurally contaminated although their execution outcomes remain recorded. Categories 01, 02, and 04 are historical/non-blind replays. Category 03's synthetic target was designed around the retrieved pattern and is not independent blindness evidence.
- **Locally verified awaiting external evidence:** Categories 03, 06, and 07. Their local or product-code checks passed, but independent cross-project reuse evidence remains insufficient for candidate promotion.
- **Historical/non-blind replays:** Categories 01, 02, and 04. They preserve useful repair and verification lessons but do not establish fresh external contribution value.
- **Partial:** Category 05. Its bounded MCP read-only surface passed, but the packaged LICENSE was not verified and graceful shutdown remained incomplete.
- **Promotion-ready verified experiences:** zero. All seven records remain candidates, and zero candidates were promoted to `experiences/verified.json`.

## Claim boundary

Batch 01 does not establish generalized AEG effectiveness or product-market fit. It lacks independent repeated cross-project reuse, causal controlled comparisons, broad external-user adoption, and sufficient upstream acceptance of candidate experiences. The merged validator repair establishes product correctness for one internal maintenance result; it does not convert that candidate into PMF or generalized-effectiveness evidence.

The appropriate next decision is to retain all seven candidates, preserve the negative and contaminated evidence, and require a separately approved Batch 02 focused on a small number of fresh external tasks with pre-diagnosis retrieval, objective pre/post oracles, and confirmed contribution paths.
