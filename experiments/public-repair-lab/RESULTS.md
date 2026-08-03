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
