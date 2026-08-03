# TR-04 — Tornado WebSocket `set_nodelay`

Status: complete
Owner: Codex
Category: test-repair
Started: 2026-08-02
Last updated: 2026-08-02
Attempts: 2
Time budget: full historical validation required
Current blocker: none

## Source lock

- Upstream repository: https://github.com/tornadoweb/tornado
- License and URL: Apache-2.0, https://github.com/tornadoweb/tornado/blob/master/LICENSE
- Benchmark and task ID: BugsInPy, Tornado bug 1
- Buggy commit: `6a5a0bfa370b6c0d3dbbf9589a560a98202d2baa`
- Focused test: `tornado/test/websocket_test.py`
- Expected failure signature: a public WebSocket method fails to delegate TCP_NODELAY to its underlying stream
- Evaluator-only fixed commit: `4677c54cc18bbfbdf0f4dadf11610fab6203fd63`
- Golden patch inspected: no

## Phase checklist

- [x] Isolated checkout created at the exact buggy commit
- [x] License and public provenance rechecked
- [x] Historical dependencies installed without credentials
- [x] Original failure reproduced
- [x] Root-cause hypothesis written before editing
- [x] Candidate patch frozen and SHA-256 recorded
- [x] Focused and related tests passed
- [x] Complete historical suite passed
- [x] Human fix inspected after the first candidate hash; second attempt explicitly evaluator-informed
- [x] Candidate and result artifacts validated
- [x] Experience promoted into `verified.json`
- [x] Transfer A/B experiment completed baseline-first

## Retrieval before repair

No experience will be applied unless the verified library returns a relevant
record and local evidence supports it. Retrieval evidence will be recorded with
the completed repair.

## Root-cause hypothesis

Initial hypothesis: the missing contract was on `WebSocketClientConnection`.
That hypothesis produced a green but incorrect proxy after the existing suite
failed to exercise the reported server path. Evaluator comparison showed that
`WebSocketHandler.set_nodelay` still targets the obsolete handler stream after
the active stream moved behind `ws_connection`. The corrected hypothesis is to
route the handler call through the WebSocket protocol and make that protocol
delegate to its active stream.

## Attempt 1 — rejected false positive

- Change: added a client-side proxy to `protocol.stream`
- Adapted test: passed, but modeled the wrong public surface
- Historical WebSocket tests: 46 passed, 1 skipped
- Complete suite: 1,146 tests reported OK, but Python 3.8/3.9 cancellation
  semantics produced four unrelated runner log errors without a compatibility
  shim
- Patch SHA-256: `4837b18e6cd2d044269bf7218de78a044e8f97808f712037b5994532c18455f3`
- Decision: rejected; not eligible for promotion

## Attempt 2 — verified

- Change: handler delegates to the WebSocket protocol; the abstract protocol
  contract delegates through `WebSocketProtocol13` to its active stream
- Corrected adapted regression: failed before and passed after repair
- Historical WebSocket suite: 46 passed, 1 skipped
- Complete suite: 1,146 passed, 50 skipped, exit code 0 in 9.481 seconds
- Patch SHA-256: `afa36076a2784cd709991c585d09afb0be997c2303e8f36cd13dc220856700a4`
- Human comparison: semantically equivalent production change; parameter naming differs
- Promotion: eligible and appended to `experiences/verified.json`

## Closely related transfer A/B

- Task: protocol-owned keepalive delegation, a dependency-free three-layer
  transfer from handler/protocol/stream to channel/protocol/stream
- Control: identical initial Git commit and object IDs, `gpt-5.6-sol`, Codex CLI
  `0.146.0-alpha.9.2`, ephemeral workspace-write sessions, shared prompt SHA-256
  `baf1d78dcec9a244d5b92fefea02eea84f9c1d01b51a72fb6ff2f2fb4483a729`
- Order: baseline with retrieval disabled, then assisted with verified retrieval
- Retrieved record: `trace-2026-08-03-tr-04-tornado-nodelay`, score `0.139`
- Baseline: success, 1 edit attempt, 4 commands, 2 tests, 39,308 ms,
  20,304 total non-cached tokens
- Assisted: success, 1 edit attempt, 4 commands, 2 tests, 43,596 ms,
  34,146 total non-cached tokens
- Delta: no command/test/attempt change; assisted added 4,288 ms and 13,842
  total non-cached tokens
- Repair path: unchanged; both arms followed the same inspection/test/edit/test
  sequence and produced identical patch SHA-256
  `d584a27f9924ce95d051861150f24ab3835eadf185a506f9b74782273fa949e0`
- Outcome: unchanged; both arms passed
- Public sanitized result:
  `experiments/public-repair-lab/results/tr-04-protocol-transfer-pair.json`
- Limitation: one pair is insufficient for a generalized causal claim
