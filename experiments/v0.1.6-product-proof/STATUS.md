# AEG v0.1.6 product-proof status

Last updated: 2026-08-14 (America/Los_Angeles).

## Current phase

The clean-profile founder usability/discoverability gate **passed on
2026-08-14** using VSIX SHA-256
`18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`.
PR #28 remains Draft. The product-proof experiment remains **prepared, not
frozen; 0/3 arms executed**.

## Founder acceptance record — PASS

- **Date:** 2026-08-14 (America/Los_Angeles).
- **Artifact:** VSIX SHA-256
  `18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`.
- **PASS:** the first empty workspace automatically opened **AEG
  verified-experience proof loop**, and the founder completed all five steps
  through local feedback creation.
- **PASS:** the local feedback file was created successfully.
- **PASS:** a second workspace using the same profile did not force the
  walkthrough open.
- **PASS:** **AEG: Open Founder Proof Walkthrough** manually reopened it.
- **Boundary:** no repair-performance arm ran; this validates usability and
  discoverability only.

## Completed work

- Audited the v0.1.5 workflow, required evidence, both dogfood decisions, the verified challenge, natural-transfer benchmark, and GitHub Issue #12.
- Preserved the two-record verified library and fixed 0.0500 retrieval threshold.
- Added one dominant verified-experience command, honest coverage, explicit abstention, guarded handoff instructions, enforced validation-before-rating, and local query/experience/outcome-linked feedback.
- Moved Playwright, Repair Lab, skill tools, the synthetic challenge, and legacy commands under **Advanced** without deleting command IDs.
- Added a five-step founder walkthrough using supported VS Code contribution points.
- Diagnosed the closed-window command-line VSIX install gap: VS Code's generic
  auto-open path only sees extensions installed into the focused workbench
  session, while AEG previously had no startup activation or owned first-run
  state.
- Added deferred startup activation, a versioned global marker with recoverable
  `opening`/`opened`/`failed` states, manual reopen, and a visible **AEG: Start
  here** status-bar fallback.
- Prepared the non-executing baseline/fixed-generic/AEG-top-1 protocol, generic advice, strict schemas, UX audit, and founder acceptance gate.

## Tests

- Untouched v0.1.5 baseline: 20/20 extension tests passed; TypeScript compiled; baseline VSIX packaged.
- v0.1.6 extension, first-run/UX-transition, and schema suite: 39/39 tests passed; TypeScript compiled.
- Retrieval and verified-experience validation: 11/11 Python tests passed; two records validated with two unique IDs.
- Site regression suite: 8/8 tests passed.
- Disposable-profile VS Code 1.133.0 install-path smoke: the local VSIX
  installed as `agentexperiencegraph.agent-experience-graph@0.1.6`; the first
  workspace activated AEG through `onStartupFinished`, persisted the versioned
  `opened` marker, and selected the AEG founder walkthrough; a second workspace
  with the same profile activated AEG without selecting that walkthrough and
  left the marker unchanged.
- Patch whitespace and private-path/credential scans: passed.
- `experiences/verified.json` diff against `origin/main`: empty.
- VSIX content inspection: version 0.1.6, deferred startup activation,
  compiled first-run state machine, all existing command IDs, five walkthrough
  files, and exactly two verified records; packaged record hash matches the
  source library.

## VSIX

- Path: `integrations/vscode/agent-experience-graph-0.1.6.vsix` (local ignored build artifact)
- SHA-256: `18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`

## Blockers

- No founder usability/discoverability blocker remains open.
- Product-proof execution is intentionally not authorized in this checkpoint;
  the protocol remains prepared, not frozen, with 0/3 arms executed.

## Publication handoff

- Branch: `codex/v0.1.6-founder-ready-proof-loop`
- Commit chain through the onboarding fix: `f8835c0`, `6e13568`, and `5c0b010`.
- Draft PR: <https://github.com/yao23/agent-experience-graph/pull/28>
- Release/merge/Marketplace publication: not performed

## Decisions

- Use clipboard plus explicit Chat paste-and-run instructions. The documented editor-chat command is not a reliable normal-Chat handoff, and no private workbench command is used.
- Treat abstention as a successful retrieval decision and inject no generic fallback.
- Require a recorded validation outcome before usefulness feedback.
- Keep all feedback and receipts local; upload nothing from the extension.
- Do not select a target or execute an arm in v0.1.6.

## Next authorized decision

The founder UX checkpoint is complete. Selecting a target, freezing the
product-proof protocol, or executing any arm requires separate explicit
authorization. Do not run D001 or another arm as part of this acceptance
record.
