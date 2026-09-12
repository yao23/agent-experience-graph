# anthropics/skills PR #1742 — MCP HTTP client lifecycle

## Classification

- AEG record: staged Registry candidate, not promoted into `main`
- Verification level: locally verified, transport-isolated regression
- AEG cross-agent transfer: not tested
- Token savings: not measured

## Source and current upstream state

- Repository: <https://github.com/anthropics/skills>
- Pull request: <https://github.com/anthropics/skills/pull/1742>
- Independently tested head: `8a2d825fa2d5fbaf2d375554985bd80503e4eda0`
- Upstream adoption commit: `0ba9e31cf27a69bb9b7f71f1d0e6f58c08d3ff1e`
- Current head checked on 2026-09-12: `b26eba8b7fab86fa74de9bc1d76a3ca0a4f53bf9`
- Current state checked on 2026-09-12: OPEN, not merged
- Applicable source license: Apache-2.0 from `skills/mcp-builder/LICENSE.txt`

## Problem signature and root cause

When custom headers are present, `MCPConnectionHTTP` creates the SDK HTTP client and passes it into the streamable HTTP transport. The caller-owned client was not registered on the connection's existing `AsyncExitStack`, so it stayed open after both normal context exit and an expected `ClientSession.initialize()` failure.

The pre-existing connection tests still passed. Two focused lifecycle regressions failed only at the final `client.is_closed is True` assertion, exposing a resource-lifecycle gap rather than a transport-functional failure.

## Environment and objective results

- CPython 3.11.15
- MCP SDK 1.29.1: unmodified `5 passed, 2 failed`; corrected `7 passed`
- MCP SDK 2.1.1: unmodified `5 passed, 2 failed`; corrected `7 passed`
- Existing tests after the correction: `5 passed, 2 deselected` in each environment
- Normal context exit: covered
- Expected initialization failure: covered
- Import checks and `evaluation.py --help`: passed in both environments
- Original evidence reported `git diff --check` and bytecode compilation passing

The tests used real SDK HTTP client objects and the real streamable HTTP transport context. Network writes and `ClientSession` responses were isolated. This was not a live-network end-to-end test.

## Minimal intervention

Register the caller-owned client's async close callback immediately after creation:

```python
if http_client is not None:
    self._stack.push_async_callback(http_client.aclose)
```

## Applicability and abstention

Apply when a wrapper creates and owns a custom async HTTP client that it injects into an SDK transport, and when the wrapper already has a lifecycle stack that covers normal and exceptional exit.

Abstain when the transport exclusively owns the client, when the client is intentionally shared across connections, or when registering cleanup would introduce double-close ownership. Reconfirm the ownership boundary before applying this pattern.

## Evidence integrity

- Sanitized regression patch SHA-256: `3f658520fa24c58a1d2eb5d350295a5ae5e6a5682f68b7ad05a8405a8848f49a`
- Sanitized minimal-fix patch SHA-256: `140b6ac6c4467734985e88e998adb566b72050ead6e4455816b9ffe278daf291`
- Deduplication key: `anthropics/skills#1742:mcp-http-client-lifecycle:8a2d825fa2d5fbaf2d375554985bd80503e4eda0`

The original raw local evidence was not uploaded. No GitHub comment was sent and the upstream pull request was not modified by this archival action.

## Limitations

- This record does not demonstrate AEG experience reuse, cross-agent transfer or token savings.
- The current upstream head includes later test hardening and rebase work that was not rerun during this archival action.
- Model, reasoning, complete command count, retries, duration, tokens and cost were not captured in the portable evidence.
- Upstream adoption is distinct from AEG Registry promotion; this candidate remains staged outside `main`.
