# 06 — Public data ETL/quality

## Operating contract

- **Project category:** bounded pipeline or quality check for a small public dataset/open API.
- **Independent external value:** produce deterministic, validated output and expose one real schema/quality failure.
- **AEG consumption/production:** retrieve ingestion/schema/duplicate/pagination lessons; produce a source-versioned data-quality experience.
- **Selection criteria:** credential-free, permissive/open terms, non-personal/non-sensitive data, tiny bounded sample, stable schema, deterministic local checks, clear attribution.
- **Exclusions/safety:** personal data, bulk copyrighted content, restricted licenses, scraping behind access controls, medical/financial sensitive records, huge downloads, paid APIs.
- **Bounded pilot:** ≤100 records or ≤1 MB; one pipeline and one quality assertion; five candidates/three scored; 30 minutes/20 commands.

## Procedure

1. **Freeze:** record source URL/version/date, license/terms, fields, sample bound, expected schema/quality oracle, deterministic output contract and retention policy; hash manifest.
2. **Retrieve:** query AEG for ETL, schema, duplicates, missing values, pagination, encoding/timezone and deterministic output; record scores/evidence/threshold/capsule.
3. **Execute:** download only bounded public data or store a permissible tiny fixture; normalize explicitly; handle missing/duplicate/timezone/encoding conditions; never retain unnecessary raw content.
4. **Verify:** schema validation, row counts, uniqueness/missing assertions, stable sort/serialization, repeat-run hash equality, source attribution and privacy/license scan.
5. **Record:** source provenance, transformations, failures/recovery, output hash/summary, commands, metrics, manifest hash, retention limitation, retrieval effect and reuse tags.

## Outcomes and metrics

- **Success:** bounded input produces schema-valid deterministic output and quality assertions pass after a justified repair.
- **Partial:** useful quality issue is proven but source instability or one oracle remains unresolved.
- **Blocked:** terms unclear, sensitive/personal data, credentials, or source size/availability exceeds bound.
- **Failure:** pipeline output is nondeterministic or violates frozen schema after repair.
- **Metrics:** bytes/rows/duplicates/missing values, commands/tests, runtime, output hash, tokens/cost, retrieval score/capsule.
- **Stopping conditions:** >1 MB/100 rows, terms ambiguity, sensitive fields, >20 commands/30 minutes, nondeterministic upstream without snapshot.
- **External approval later:** publish dataset/output, submit upstream patch, call write API, candidate promotion.

## Next-pilot recommendation template

`Source/license / bounded sample / quality defect / deterministic oracle / retention plan / follow-up / approval.`
