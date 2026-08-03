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
- [ ] Transfer A/B experiment completed baseline-first

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
