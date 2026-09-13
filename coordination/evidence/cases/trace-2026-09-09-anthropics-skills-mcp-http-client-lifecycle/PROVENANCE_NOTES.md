# Provenance update for PR #1742 — 2026-09-13

This is additional metadata and a source review, not another repair experiment.
The original PUBLIC_SUMMARY.md and two regression/fix patches remain unchanged.

## Contribution chain

- WillO-OlliW reported the original MCP import/API migration problem in
  [issue #1668](https://github.com/anthropics/skills/issues/1668).
- Kuldeeep18 authored the implementation in [PR #1742](https://github.com/anthropics/skills/pull/1742).
- yao23's [initial review](https://github.com/anthropics/skills/pull/1742#pullrequestreview-5162966723)
  identified caller-owned client cleanup and the missing lifecycle coverage.
- yao23 published [AI-assisted independent local reproduction](https://github.com/anthropics/skills/pull/1742#issuecomment-5614638047)
  and later [non-vacuous assertion feedback](https://github.com/anthropics/skills/pull/1742#issuecomment-5630437195).
  Codex assisted the analysis and local execution; the exact historical model,
  harness version and reasoning setting were not captured in the public bundle.
- The PR author [reported adopting the lifecycle correction](https://github.com/anthropics/skills/pull/1742#issuecomment-5614929511)
  at 0ba9e31cf27a69bb9b7f71f1d0e6f58c08d3ff1e, then
  [reported assertion hardening and rebase](https://github.com/anthropics/skills/pull/1742#issuecomment-5635044430).
  This establishes PR-author adoption, not maintainer acceptance or merge.
- 98zc5g5jyw-arch [reported 7/7 passing](https://github.com/anthropics/skills/pull/1742#issuecomment-5652579839)
  in a clean Python 3.11 / latest MCP 2.x / pytest 9.1 environment on September 13.
  Store this as SELF_REPORTED. No exact tested commit, exact MCP version or raw
  execution artifact accompanied the report. Identity and independence beyond
  the public account have not been verified. No AEG reuse was reported.

## Separate test subject from reported upstream state

Our existing local result covers 8a2d825fa2d5fbaf2d375554985bd80503e4eda0 plus
the frozen regression and minimal-fix patches, in MCP 1.29.1 and 2.1.1.
It does not establish that we ran the later adoption or rebased commit.

The PR was still open and unmerged when read on September 13; its observed
head was b26eba8b7fab86fa74de9bc1d76a3ca0a4f53bf9. A current head observation
does not identify the third party's tested revision. Their assertion about
the legacy skip branch is not independent execution evidence for MCP < 2.

The older promotionEvidence object associated observed-passed with the adoption
commit. The current candidate corrects that status to reported-passed and links
the PR author's report. The legacy validatedCommitSha field is the subject of
that report. Original local test results, verification_status and
last_verified_at remain unchanged; no independent workflow run is asserted.

## Rights, integrity and transfer limits

The [mcp-builder license](https://github.com/anthropics/skills/blob/8a2d825fa2d5fbaf2d375554985bd80503e4eda0/skills/mcp-builder/LICENSE.txt)
is Apache-2.0. AEG-authored metadata uses the repository's MIT-0 license;
upstream code keeps its own terms and attribution. This record links to
third-party comments and provides original factual summaries. Separate consent
to republish their full text was not requested or inferred from public visibility.

Recorded hashes cover exact public artifact bytes, not private execution traces.
They do not certify authorship, time, accuracy or rights. No model/API calls,
bug experiments, upstream comments, main changes or new transfer results are
part of this update. The source frozen at 94f25c36bab3f4729413ebc20dbb4d310c64ea23
for #3494 remains unchanged. This candidate is still STAGED_NOT_IN_MAIN and
LOCALLY_VERIFIED; token savings and cross-agent transfer are not established.
