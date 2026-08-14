# S1 reproducibility record

The tracked manifest is the sole source of task identity, task inputs, fixture
hashes, public commits, experience payloads, seed, budgets, arm order, metrics,
promotion criteria, and stop conditions. Local `.aeg` data, chat history,
screenshots, caches, upstream working trees, and untracked files are excluded.

## Frozen inputs

- Manifest SHA-256: `95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`.
- Freeze time: `2026-08-14T18:46:10Z`, before any arm execution.
- Pairs: 2; modes per pair: 2; replicates per mode: 3; planned arms: 12.
- Randomization seed: `situated-experience-benchmark-v1-s1-2026-08-14`.
- Arm budget: 900 seconds, 40 completed commands, 3 distinct production attempts.
- Model: `gpt-5.6-sol`; any unavailable input/output token telemetry remains
  `null` with a reason.
- Fixtures: dependency-free public extracts staged in this directory; execution
  and evaluator tests need no package or source download.

`freeze.json` protects the manifest, family registry, candidate screening,
measurement contract, runner, standalone worker, schema tree, and fixture tree.
The runner refuses validation or packaging if any protected digest changes.

## Reproduction commands

Run from the repository root:

```sh
python3 autonomous-lab/scripts/lab.py validate
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py validate
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py preflight
python3 experiments/situated-experience-benchmark-v1/test_benchmark.py
git diff --check
```

The preflight uses fresh temporary Git repositories. It confirms every buggy
source and transfer failure before applying any human patch, applies each
controller-only patch to a new copy, adds hidden tests only inside the evaluator
copy, and verifies the complete suite. Packaging audits every planned arm and
does not invoke Codex.

## Isolation handoff

`schedule-s1` creates one bundle per coordinate in frozen order. A bundle has
only a one-commit transfer workspace, `arm.json`, the agent-result schema, and
the standalone worker. The worker requires a dedicated `SEB_RUNNER_ROOT` whose
only child is that bundle, rejects credential-shaped environment variables,
and refuses an envelope whose `--mode` differs from `control` or
`aeg-assisted`. Controller-only hidden tests and human patches are used only by
`evaluate-arm` after the agent process has terminated.

No arm has been executed while preparing this record.
