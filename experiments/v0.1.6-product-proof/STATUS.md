# AEG v0.1.6 product-proof status

Last updated: 2026-08-11 (America/Los_Angeles).

## Current phase

Implementation and local validation complete; ready for the founder usability gate. Branch pushed and Draft PR #28 open. Experiment status remains **prepared-not-frozen; 0/3 arms executed**.

## Completed work

- Audited the v0.1.5 workflow, required evidence, both dogfood decisions, the verified challenge, natural-transfer benchmark, and GitHub Issue #12.
- Preserved the two-record verified library and fixed 0.0500 retrieval threshold.
- Added one dominant verified-experience command, honest coverage, explicit abstention, guarded handoff instructions, enforced validation-before-rating, and local query/experience/outcome-linked feedback.
- Moved Playwright, Repair Lab, skill tools, the synthetic challenge, and legacy commands under **Advanced** without deleting command IDs.
- Added a five-step first-install walkthrough using supported VS Code contribution points.
- Prepared the non-executing baseline/fixed-generic/AEG-top-1 protocol, generic advice, strict schemas, UX audit, and founder acceptance gate.

## Tests

- Untouched v0.1.5 baseline: 20/20 extension tests passed; TypeScript compiled; baseline VSIX packaged.
- v0.1.6 extension, UX-transition, and schema suite: 29/29 tests passed; TypeScript compiled.
- Retrieval and verified-experience validation: 11/11 Python tests passed; two records validated with two unique IDs.
- Site regression suite: 8/8 tests passed.
- Patch whitespace and private-path/credential scans: passed.
- `experiences/verified.json` diff against `origin/main`: empty.
- VSIX content inspection: version 0.1.6, five walkthrough files, and exactly two verified records; packaged record hash matches the source library.

## VSIX

- Path: `integrations/vscode/agent-experience-graph-0.1.6.vsix` (local ignored build artifact)
- SHA-256: `8a5b53dfe5597ba42403edec5c780dbf352c5be3cf151cbff5558859e4b0f498`

## Blockers

- No product, experiment-design, packaging, or publication blocker is open.
- GitHub CLI authentication is invalid, but Git credentials pushed the branch and the connected GitHub app created the Draft PR.

## Publication handoff

- Branch: `codex/v0.1.6-founder-ready-proof-loop`
- Commits: `f8835c0` plus the status-only handoff update
- Draft PR: <https://github.com/yao23/agent-experience-graph/pull/28>
- Release/merge/Marketplace publication: not performed

## Decisions

- Use clipboard plus explicit Chat paste-and-run instructions. The documented editor-chat command is not a reliable normal-Chat handoff, and no private workbench command is used.
- Treat abstention as a successful retrieval decision and inject no generic fallback.
- Require a recorded validation outcome before usefulness feedback.
- Keep all feedback and receipts local; upload nothing from the extension.
- Do not select a target or execute an arm in v0.1.6.

## Exact founder action required next

After the final VSIX path is recorded here, clean-install that VSIX and perform the exact three-minute test in [`UX-ACCEPTANCE.md`](UX-ACCEPTANCE.md). Report each pass/fail item on the Draft PR. Do not run an experiment arm; target selection and protocol freeze require a separate explicit authorization after the usability gate passes.
