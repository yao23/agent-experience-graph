# Situated Experience Benchmark v1

Situated Experience Benchmark v1 tests whether AEG helps when repair depends on
knowledge of version state, execution environment, historical failures,
cross-module consequences, multi-agent handoffs, and experience applicability.

It extends the narrow public repair evidence without rewriting it: the prior
five-pair experiment verified all 10 arms, reduced median completed commands by
1, and regressed median wall time by about 18.2 seconds. That result did not
establish broader AEG effectiveness. No Situated Experience Benchmark arm has
run yet.

The six ordered families are S1 dependency and version migration, S2 CI and
deployment failures, S3 cross-module regressions, S4 Planner-Coder-Tester-
Reviewer collaboration, S5 misleading repairs and repeated failure paths, and
S6 experience invalidation under environment drift. This bounded revision
implements and freezes S1 only; S2-S6 remain design-only screening contracts.

## S1 contents

Exactly two natural public source-transfer pairs are accepted:

1. Scrapy CookieJar adaptation across Python 3 decoding and request-protocol
   changes.
2. FastAPI request handling across Pydantic 1.x field representations.

Each offline fixture is a dependency-free public extract tied to upstream bug,
commit, date, license, and human-fix evidence. The transfer workspace contains a
visible failure. Controller-only directories contain the human patch and broader
tests and are never packaged for an agent. Each treatment receives only the
eight allowed compact-experience fields; no transfer patch or evaluator fact is
present.

## Validation and preflight

These commands never invoke an agent:

```sh
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py validate
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py preflight
python3 experiments/situated-experience-benchmark-v1/test_benchmark.py
```

`preflight` proves that every buggy source and transfer fails for its registered
reason, every hidden human patch passes visible and hidden suites, and generated
control and AEG-assisted bundles exclude evaluator, other-arm, and other-pair
data. Adversarial tests verify that injected evaluator files, credentials,
cross-arm sentinels, altered experiences, and fixture drift fail closed.

## Deterministic replay interface

The arm selector is explicit and frozen:

```sh
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py package-arm \
  --pair s1-01-scrapy-cookiejar --replicate 1 --mode control --output /tmp/seb-arm
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py package-arm \
  --pair s1-01-scrapy-cookiejar --replicate 1 --mode aeg-assisted --output /tmp/seb-arm-aeg
```

An arm bundle contains a one-commit transfer workspace, an immutable envelope,
the structured-result schema, and the standalone worker. It must execute on a
fresh disposable runner that has only that bundle. Running an agent from this
controller checkout is prohibited because the tracked evaluator data is
readable here. The worker requires `SEB_DISPOSABLE_RUNNER=1` and a dedicated
`SEB_RUNNER_ROOT` whose sole child is the bundle before execution. Pairwise
evaluation occurs only after both bundles return.

`schedule-s1` packages the frozen 12-arm plan (two pairs, two modes, three
replicates) without executing it. The frozen order comes from the registered
seed. Actual execution requires a disposable-runner coordinator and an
authenticated model broker that does not expose credentials to agent commands.

## Evidence boundary

Promotion and stop conditions are frozen in `s1-manifest.json` and explained in
`MEASUREMENT-CONTRACT.md`. Wall time is measured but cannot qualify positive
evidence. Negative, neutral, abstention, protocol-deviation, and infrastructure
outcomes must be retained. S1 cannot establish value for S2-S6.
