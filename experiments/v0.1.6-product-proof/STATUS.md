# AEG v0.1.6 product-proof status

Last updated: 2026-08-14 (America/Los_Angeles).

## Current phase

The first founder usability gate **failed on discovery**: the manual proof loop
worked, but the walkthrough did not open after the real VSIX install and the
founder needed external Command Palette instructions. The onboarding fix is
implemented and locally validated; a clean-profile founder re-test is required.
PR #28 remains Draft. Experiment status remains **prepared-not-frozen; 0/3
arms executed**.

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

- Founder discovery acceptance remains blocked pending the clean-profile
  first-window, second-window, and manual-reopen re-test.
- GitHub CLI authentication is invalid, but Git credentials pushed the branch and the connected GitHub app created the Draft PR.

## Publication handoff

- Branch: `codex/v0.1.6-founder-ready-proof-loop`
- Commit chain: `f8835c0`, status handoff `6e13568`, and this UX-fix checkpoint
  on the same branch.
- Draft PR: <https://github.com/yao23/agent-experience-graph/pull/28>
- Release/merge/Marketplace publication: not performed

## Decisions

- Use clipboard plus explicit Chat paste-and-run instructions. The documented editor-chat command is not a reliable normal-Chat handoff, and no private workbench command is used.
- Treat abstention as a successful retrieval decision and inject no generic fallback.
- Require a recorded validation outcome before usefulness feedback.
- Keep all feedback and receipts local; upload nothing from the extension.
- Do not select a target or execute an arm in v0.1.6.

## Exact founder action required next

Use a disposable profile that has never stored AEG global state, install the
VSIX above, and perform the exact first-window, proof-loop, second-window, and
manual-reopen test in [`UX-ACCEPTANCE.md`](UX-ACCEPTANCE.md). Do not give the
founder a README, command name, Command Palette instruction, or navigation
hint. Report each item as pass/fail on the Draft PR and keep the gate failed if
any item misses. Do not run an experiment arm; target selection and protocol
freeze require separate explicit authorization after the usability gate passes.
