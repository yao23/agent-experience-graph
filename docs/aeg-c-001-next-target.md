# AEG-C-001 next-target preparation

This is read-only preparation. It does not execute Linkwarden, change the
Foundry candidate ledger, consume a Foundry round, or claim reproduction.

## Frozen target facts

- Candidate: `AEG-C-001`; selected family
  `PLAYWRIGHT_BROWSER_ARTIFACT_VERSION_DRIFT`; current Foundry status
  `BLOCKED_ENVIRONMENT`.
- Public report: [`linkwarden/linkwarden#1781`](https://github.com/linkwarden/linkwarden/issues/1781),
  still open when checked on 2026-09-06.
- Target repository revision: Linkwarden tag `v2.16.0`, commit
  `62f1b81ff7f66001b0f5f613202f87771f3186ee`.
- Reported platform: the official ARM64 (`aarch64`) v2.16.0 container.
- Reported failure: Playwright 1.57.0 tries to use
  `/ms-playwright/chromium-1200/chrome-linux/chrome`, but the image contains
  only `chromium_headless_shell-1200`; link archiving fails with “Executable
  doesn't exist”.
- Source consistency: the pinned Dockerfile explicitly installs only
  `chromium-headless-shell`, while `apps/web/package.json` pins Playwright
  `1.57.0` and `apps/worker/lib/browser.ts` calls `chromium.launch()` with its
  default launch options.

## Minimal baseline oracle for a later authorized Foundry round

Use a newly created standard GitHub-hosted ARM64 Ubuntu VM. During its
dependency phase, resolve and pin the immutable manifest digest for
`ghcr.io/linkwarden/linkwarden:v2.16.0`, pull that exact ARM64 image, and record
the digest and target commit above. Then disable test networking and run one
bounded container command equivalent to the production launcher:

```text
node -e 'const { chromium } = require("playwright"); chromium.launch().then(async b => { await b.close(); process.exit(0); }).catch(e => { console.error(e); process.exit(42); })'
```

The baseline oracle passes only as a reproduction when the command actually
executes, exits `42`, and its captured stderr identifies the missing
`chromium-1200/chrome-linux/chrome` executable. Also record the
`/ms-playwright` inventory. A registry failure, unavailable ARM64 runner,
missing image, timeout, or a different launch error is infrastructure-blocked,
not a reproduced defect. A successful browser launch disproves this frozen
baseline and must not be counted as reproduction.

Required network is limited to the dependency phase: GitHub checkout and the
public GHCR image pull. The oracle itself needs no network and must run with
`--network none`. Expected elapsed time is at most 15 minutes, dominated by the
image pull; actual duration and compute cost must be recorded, with unavailable
token, founder-time, and dollar values reported as `UNKNOWN`.

## Contamination and remaining block

The issue body already exposes `npx playwright install chromium` as a working
workaround. That is known-solution exposure and must be visible to any later
transfer analysis. The committed Foundry candidate currently says
`contamination: LOW`; do not rewrite that historical field. Before a repair or
transfer claim, append a reviewed follow-up note that records this discrepancy
and keeps AEG-C-001 out of held-out evidence.

The current receipt-first/next-round process is not compatible with a hosted
runner that is destroyed when its job ends. The smallest later integration is
a one-shot job entrypoint that, within one VM lifetime, (1) creates the
environment, (2) runs these qualification probes, (3) claims one already
eligible task under the existing controller intent/oracle, (4) executes and
records the result, and (5) destroys the environment. No completed canary VM
may be registered as available for a future round.
