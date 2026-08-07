# 05 — Agent skill/MCP compatibility

## Operating contract

- **Project category:** bounded compatibility card for one public skill or MCP server.
- **Independent external value:** verify that a declared manifest, startup, discovery surface, and safe task work as documented.
- **AEG consumption/production:** retrieve tool/skill compatibility experience; produce a scoped card describing environment, permissions, failure behavior and verified operations.
- **Selection criteria:** explicit permissive license; active, small implementation; credential-free local mode; published schema/manifest; safe read-only example; deterministic startup/discovery.
- **Exclusions/safety:** private connectors, credentials, external writes, filesystem-wide access, arbitrary remote execution, unclear permissions, vulnerability probing, global ratings.
- **Bounded pilot:** one startup plus discovery and one safe task; five candidates/three scored; 30 minutes/20 commands.

## Procedure

1. **Freeze:** record repository/version/commit/license, manifest/schema, runtime, install/start/discovery commands, safe task, permission assumptions and success oracle; hash manifest.
2. **Retrieve:** query AEG for manifest, MCP, tool discovery, startup, failure-mode and permission phrases; record ranking/evidence/threshold/capsule.
3. **Execute:** install in `/tmp`; validate manifest/schema; start only a bounded local subprocess; enumerate tools/resources; invoke one non-writing example; terminate cleanly; test one documented invalid input.
4. **Verify:** exit/status/protocol messages, deterministic discovery names/schema, example result, stderr/failure contract, dependency and permission documentation.
5. **Record:** compatibility card with exact supported surface—not a global score—plus attempts, commands, hashes, metrics, limitations, and retrieval effect.

## Outcomes and metrics

- **Success:** manifest, startup, discovery and one safe task pass; failure mode is bounded and documented.
- **Partial:** schema/discovery passes but invocation or docs have a bounded defect.
- **Blocked:** credentials/private account/external write or unclear license/permissions required.
- **Failure:** declared local compatibility surface is reproducibly broken and not repaired in bounds.
- **Metrics:** install/start latency, tools/resources discovered, invocations, commands/tests, output hash, tokens/cost, retrieval score/capsule.
- **Stopping conditions:** process cannot terminate, network writes, credentials, >20 commands/30 minutes, security-sensitive behavior.
- **External approval later:** publish card, contact author, PR/comment, registry submission, candidate promotion.

## Next-pilot recommendation template

`Package/version / verified surface / permission envelope / safe task / failure behavior / missing evidence / approval.`
