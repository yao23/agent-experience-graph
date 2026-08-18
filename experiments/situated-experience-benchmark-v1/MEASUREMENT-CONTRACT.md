# Common measurement and evaluation contract

This contract applies unchanged to every future family. `arm-result.schema.json`
is the machine-readable record. Missing token telemetry is `null` with a reason;
no unavailable value is inferred.

## Arm measurements

- **Regression-free success:** the final production patch passes the visible
  focused test and every controller-only regression test without changing any
  test, task, experience, or evaluator file.
- **Attempts:** distinct non-empty production patch snapshots. Reformat-only
  snapshots with the same normalized diff are one attempt.
- **Completed commands:** completed agent command-execution events. Controller
  preflights and evaluator commands are recorded as tests but not agent commands.
- **Tests run:** every detected agent test invocation plus focused, hidden, and
  broader evaluator commands, with scope and result.
- **Files inspected and changed:** repository-relative paths only. Inspection is
  derived from command arguments and structured agent output; changed files are
  authoritative from Git.
- **Patch size:** added lines, deleted lines, and changed-file count from the
  production diff.
- **Wall time:** monotonic milliseconds from agent process start through exit;
  evaluator time is separate and cannot qualify a result.
- **Tokens:** input and output usage emitted by the model runner, or `null` with
  the exact unavailability reason.
- **Historical paths repeated:** pre-registered path IDs whose patterns match
  the stated approach, first patch, or final patch.
- **Environment assumptions checked:** each registered assumption, whether it
  was checked, and local evidence.
- **Experience disposition:** every experience is recorded as retrieved, used,
  rejected, or abstained with a reason. Control records an abstention because no
  experience is available.
- **Negative transfer:** paired evaluator result; true when treatment introduces
  a regression, loses regression-free success, or materially worsens at least
  two effort measures without a correctness gain.
- **Evaluator findings:** focused and hidden outcomes, test-file protection,
  prohibited artifact changes, patch applicability, and protocol deviations.

## Pair and benchmark evaluation

Evaluate a replicate only after both modes have terminated. Evaluate each pair
across its three replicates before computing benchmark medians; replicates are
not independent tasks. A repair-path improvement is interpretable only when a
pre-registered historical path is avoided, an environment assumption is checked
earlier, an inapplicable experience is explicitly rejected, or correctness is
preserved while at least two of attempts, commands, or tests improve. Token and
wall-time deltas alone are not repair-path improvements.

Treatment token overhead is `(median_treatment - median_control) /
median_control`, using input plus output tokens when both are available. If more
than half of arms lack token telemetry, the overhead criterion is unevaluable
and promotion fails closed.

## Pre-registered promotion criteria

All criteria are required:

1. no reduction in regression-free success;
2. at least one interpretable repair-path improvement;
3. no leakage or contamination;
4. treatment token overhead no greater than 30% at the median;
5. wall-time improvement alone cannot qualify as positive evidence.

## Pre-registered stop conditions

Stop the benchmark and do not interpret arm outcomes if:

1. hidden evaluator data is reachable by an agent;
2. one arm can read another arm's artifacts;
3. treatment contains or reveals the transfer patch;
4. a task, threshold, or metric changes after outcomes are observed;
5. both accepted pairs are trivial one-shot tasks with identical repair paths;
6. treatment causes additional regressions.

Infrastructure failure, model unavailability, or missing token telemetry is not
silently converted into a repair failure. It is recorded as a protocol finding
and evaluated under the fail-closed rules above.
