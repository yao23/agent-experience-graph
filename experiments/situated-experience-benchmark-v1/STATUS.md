# Situated Experience Benchmark v1 status

Last updated: 2026-08-14 (America/Los_Angeles).

- Phase: S1 manifest frozen before execution; ready for disposable-runner handoff.
- Accepted S1 pairs: 2 exactly.
- Rejected S1 candidates: 5, all with recorded reasons.
- Planned arms: 12 (2 pairs × 2 modes × 3 replicates).
- Executed arms: 0.
- S2-S6: screening rules only; no fixtures, manifests, or arms implemented.
- Fixture preflight: passed for both source and both transfer fixtures; four buggy failures matched registered reasons and four hidden human patches passed all registered suites.
- Isolation/leakage/evaluator-access preflight: passed for all 12 planned one-arm bundles; 9 adversarial controller tests passed.
- Manifest mutation after outcomes: prohibited.
- Frozen manifest SHA-256: `95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`.

The current public evidence remains narrow: 10/10 prior repair-lab arms passed,
median completed commands improved by 1, and median wall time regressed by about
18.2 seconds. No broad effectiveness claim is supported.

After this status, manifest, and controller are committed and CI passes, the
next allowed command is:

```sh
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py schedule-s1 \
  --output /tmp/situated-experience-benchmark-v1-s1-95ce8de8
```

This creates the immutable 12-arm plan. Each bundle must then run on a separate
disposable runner satisfying the worker's credential and sole-bundle checks.
Do not execute from the controller checkout.
