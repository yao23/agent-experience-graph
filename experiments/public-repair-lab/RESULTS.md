# v0.1.3 validation result

The release validation ran five paired baseline/AEG-assisted trials on the
FastAPI nested response-model fixture. Execution order alternated by trial.
Every arm began from an identical committed workspace and used a fresh,
ephemeral Codex session.

| Trial | Baseline ms | Assisted ms | Baseline commands | Assisted commands | Baseline non-cached tokens | Assisted non-cached tokens |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 41,928 | 60,754 | 6 | 4 | 23,232 | 37,016 |
| 2 | 61,510 | 55,891 | 6 | 4 | 23,894 | 23,162 |
| 3 | 47,826 | 66,061 | 5 | 4 | 23,133 | 39,441 |
| 4 | 36,394 | 60,751 | 3 | 3 | 36,657 | 35,778 |
| 5 | 81,583 | 45,754 | 5 | 4 | 53,451 | 21,577 |

All ten arms passed objective verification and produced the identical one-line
production fix. Paired median assisted-minus-baseline deltas were:

- completed commands: **-1**;
- actual test executions: **0**;
- non-cached tokens: **-732**;
- duration: **+18,235 ms**.

This demonstrates a bounded reduction in agent tool cycles without changing the
repair result. It does not demonstrate a success-rate improvement, and wall-clock
latency regressed in this sample. The experiment should be repeated across more
task families and model/service conditions before making broader claims.

Raw reports, JSONL events, stderr logs, and per-arm patches are local artifacts
under `.aeg/repair-lab/` and are intentionally excluded from source control.

## Independently recomputable evidence

The sanitized counters and SHA-256 patch digests for every pair are published
in `results/v0.1.3-paired-results.json`. It includes trial IDs, alternating
execution order, arm outcomes, completed commands, actual test executions,
non-cached tokens, durations, task IDs, and available runtime configuration.
It contains no prompts, JSONL, logs, source patches, credentials, private paths,
or workspace data.

The original event stream did not expose the model identifier or Codex CLI
version. The trials also ran before the runner changes were committed, so an
exact runner source commit cannot be established retrospectively. Those fields
are explicitly `null`; they are not inferred from a later commit.

Recompute and cross-check the published aggregate against the verified AEG
record with:

```bash
python3 experiments/public-repair-lab/validate_paired_results.py
```

The validator fails on missing arms, invalid metric types, duplicate trial IDs,
non-alternating order, inconsistent patch hashes, incorrect arm/outcome counts,
or aggregate drift. CI promotion evidence is recorded separately in
`experiences/verified.json`, because the experiment itself did not occur in the
promotion workflow and a commit cannot embed the ID of its own future run.

## TR-04 transfer pair

A baseline-first transfer pair tested a related channel/protocol/stream
keepalive repair with `gpt-5.6-sol` and Codex CLI `0.146.0-alpha.9.2`. Both arms
succeeded in one edit attempt, four completed commands, and two test executions.
They produced the identical patch SHA-256. The assisted arm added 4,288 ms and
13,842 total non-cached tokens, so verified retrieval changed neither the repair
path nor the outcome in this pair and regressed both measured cost dimensions.

This is a single pair, not evidence of a generalized retrieval effect. The
sanitized control metadata, detailed token reconciliation, retrieval evidence,
and path comparison are in `results/tr-04-protocol-transfer-pair.json`.

## Pre-registered TR-04 failed-path prevention pair

The manifest was published at commit `851ed4b36d1bb5be225709af5e43811743d227a9`
before either arm ran. Neither arm entered the registered client-side trap.
Control repaired handler initialization; treatment selected the canonical
protocol-contract recovery. Both succeeded in one attempt with two test runs
and inspected the same three files.

Treatment used one additional command and 944 additional total non-cached
tokens, while completing 7,292 ms faster. The pre-registered positive rule did
not count wall time alone: treatment had to prevent a control failure or reduce
attempts, commands, tests, or tokens without reducing correctness. The measured
result is therefore not positive. Sanitized evidence is in
`results/tr-04-failed-path-prevention-pair.json`.
