# Situated Experience Benchmark v1 status

Last updated: 2026-08-14 (America/Los_Angeles).

- Phase: S1 execution stopped at the real-substrate gate; infrastructure-blocked.
- Accepted S1 pairs: 2 exactly.
- Rejected S1 candidates: 5, all with recorded reasons.
- Planned arms: 12 (2 pairs × 2 modes × 3 replicates).
- Generated plan: 12 frozen arms; plan SHA-256 `6e6a3b75102d03d804cf0b8e1f51b3b1194fe5e1c39802b9d0cc64043bb9582a`.
- Executed arms: 0; no canary or hidden evaluation ran.
- S2-S6: screening rules only; no fixtures, manifests, or arms implemented.
- Fixture preflight: passed for both source and both transfer fixtures; four buggy failures matched registered reasons and four hidden human patches passed all registered suites.
- Isolation/leakage/evaluator-access preflight: passed for all 12 planned one-arm bundles; 10 adversarial controller tests passed.
- Manifest mutation after outcomes: prohibited.
- Frozen manifest SHA-256: `95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`.
- Hosted CI: passed for commit `55a9edafdda8ef4b82fe643de17bd9054929adca`.
- Real substrate preflight: blocked. Tracked state has no disposable-runner
  coordinator, model credential broker, private raw-output sink, or sanitized
  result return channel. The available controller process shares the checkout,
  evaluator data, process state, and caches.
- Classification: `infrastructure-blocked`; promotion is not supported and
  fails closed because correctness, repair-path, leakage, and token-overhead
  criteria are not evaluable.

The current public evidence remains narrow: 10/10 prior repair-lab arms passed,
median completed commands improved by 1, and median wall time regressed by about
18.2 seconds. No broad effectiveness claim is supported.

The plan-generation command has now run exactly once:

```sh
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py schedule-s1 \
  --output /tmp/situated-experience-benchmark-v1-s1-95ce8de8
```

The exact plan is tracked at `execution/s1-execution-plan.json`. There is no
safe next arm command until an actual disposable coordinator and credential
broker pass the adversarial canary in `execution/substrate-preflight.json`.
Do not execute from the controller checkout and do not expand to full
historical dependency stacks yet.
