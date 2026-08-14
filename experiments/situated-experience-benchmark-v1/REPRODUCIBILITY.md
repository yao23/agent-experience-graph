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

## 2026-08-14 execution continuation

The continuation began from clean commit
`55a9edafdda8ef4b82fe643de17bd9054929adca`. The manifest recomputed to
`95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`.
Draft PR 28 hosted run 31834107919 passed schema, fixture, controller isolation,
leakage, evaluator-access, extension, compilation, and packaging checks for
that commit. The hosted workflow does not run the site or autonomous-lab
suites; local runs passed 8 site tests and 64 autonomous-lab tests plus the
lab's validation, status, next-action, and report checks.

The frozen schedule command generated 12 bundles at
`2026-08-14T19:39:06.329005+00:00`. Its exact tracked plan is
`execution/s1-execution-plan.json`, SHA-256
`6e6a3b75102d03d804cf0b8e1f51b3b1194fe5e1c39802b9d0cc64043bb9582a`.

Execution then stopped before the non-benchmark canary and before every arm.
Tracked repository state does not identify a disposable-runner provider or an
authenticated model broker that withholds credentials from agent commands.
The available Codex process shares the controller host and cannot satisfy the
controller, evaluator, cache, conversation, workspace, or process-isolation
requirements. It was not used as a substitute. Consequently zero model calls,
zero input/output tokens, zero hidden evaluations, and zero arm outcomes were
recorded. See `execution/substrate-preflight.json` and
`execution/RESULTS.md`.

The frozen `decision-ledger.jsonl` remains unchanged because its digest is a
protected input in `freeze.json`. Post-freeze execution decisions continue its
hash chain in `execution/decision-ledger.jsonl`.

## 2026-08-14 arm-substrate deviation

Because zero arms and zero outcomes existed, execution infrastructure moved to
the tracked AEG Arm Execution Substrate without changing a frozen benchmark
input. The workflow pins `ubuntu-24.04` and container manifest
`sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
Each future matrix coordinate has its own fresh VM. The host copies only a
validated envelope and frozen one-commit task into a 32 MiB tmpfs repair
workspace with no bind mount or network; the host model client exposes four
strict functions whose operations run only through the container worker.

Hosted run 31840751530 used runner image `ubuntu24` version
`20260810.271.1` and produced container image
`sha256:423c7064cc5a754bec9c1a40756a27bd1814f0ed428b6de68250bfbd6fe9f005`.
All four registered failure signatures and all four human patches passed in
that image. The canary passed 28 isolation and enforcement attempts, removed
its plaintext raw file, and executed zero benchmark arms. It remained blocked
before a model request because the repository had no Actions secrets named
`OPENAI_API_KEY` or `AEG_RAW_OUTPUT_CERT_PEM`. Therefore live control and
treatment telemetry, cost accounting, and encrypted artifact retention remain
unverified. The exact sanitized record is tracked in
`execution/substrate-preflight.json`.
