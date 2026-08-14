# Situated Experience Benchmark v1 status

Last updated: 2026-08-14 (America/Los_Angeles).

- Phase: S1 execution stopped at the real-substrate gate; infrastructure-blocked.
- Accepted S1 pairs: 2 exactly.
- Rejected S1 candidates: 5, all with recorded reasons.
- Planned arms: 12 (2 pairs × 2 modes × 3 replicates).
- Generated plan: 12 frozen arms; plan SHA-256 `6e6a3b75102d03d804cf0b8e1f51b3b1194fe5e1c39802b9d0cc64043bb9582a`.
- Executed arms: 0; one non-benchmark hosted substrate canary ran; no benchmark
  hidden evaluation ran.
- S2-S6: screening rules only; no fixtures, manifests, or arms implemented.
- Fixture preflight: passed again on pinned hosted image
  `sha256:423c7064cc5a754bec9c1a40756a27bd1814f0ed428b6de68250bfbd6fe9f005`;
  four buggy failures matched registered reasons and four human patches passed
  the complete registered suites.
- Isolation/leakage/evaluator-access preflight: passed for all 12 planned one-arm
  bundles; 20 substrate unit tests and 28 hosted adversarial attempts passed.
- Manifest mutation after outcomes: prohibited.
- Frozen manifest SHA-256: `95ce8de8aca5580c8be95613b6058baecf2d473d9241831657e2a939577919c9`.
- Hosted Repair Lab CI: passed for infrastructure commit
  `be072873311621bfc7f56606db70b2f8a40d5bb5`; the separate hosted substrate
  job intentionally failed its readiness gate at the missing host inputs.
- Real substrate preflight: partially passed and still blocked. The reusable
  GitHub-hosted controller, zero-bind tmpfs repair container, strict four-tool
  bridge, separate evaluator, sanitizer, and encrypted-output path are
  implemented. Hosted run 31840751530 passed 28 adversarial fixture,
  isolation, resource, patch-export, evaluator-order, and schema checks. It
  failed closed because Actions has no `OPENAI_API_KEY` or
  `AEG_RAW_OUTPUT_CERT_PEM`, so model access, encryption, and live token/cost
  telemetry remain unproved.
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
safe next arm command until both required Actions secrets are configured and
the same hosted adversarial canary passes as recorded in
`execution/substrate-preflight.json`. Do not execute from the controller
checkout and do not expand to full historical dependency stacks yet.
