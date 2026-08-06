# 03 — Regression-test gap

## Operating contract

- **Project category:** repair a green-suite false positive or missing public contract test.
- **Independent external value:** ensure tests exercise the actual public ownership/delegation boundary.
- **AEG consumption/production:** test transfer from TR-04 when score permits; create reusable contract-test and wrong-surface detection evidence.
- **Selection criteria:** permissive active project; historical/public defect or demonstrable untested boundary; fast deterministic tests; public entry point; ≤3 files; no visible complete fix before freeze.
- **Exclusions/safety:** invented behavior without issue/docs evidence, private APIs, security bugs, snapshot-only subjective changes, large integration harnesses.
- **Bounded pilot:** one contract and one focused regression; five candidates/three scored; 45 minutes/25 commands.

## Procedure

1. **Freeze:** record public contract, commit, existing green command, missing assertion/path, expected pre-fix false green and post-fix oracle; hash manifest before future patch inspection.
2. **Retrieve:** query AEG with public-surface, wrapper/proxy/delegation, false-green and fixture terms; record TR-04 score/evidence and obey 0.05 threshold.
3. **Execute:** trace the public entry point through ownership boundaries; first add or adapt a test that fails for the defect; minimally repair the correct layer; reject plausible wrong-surface fixes.
4. **Verify:** legacy suite remains green, new regression fails before/pass after, exact delegate/call contract asserted, broader suite/lint feasible, diff audited.
5. **Record:** contract, false-positive mechanism, attempts, rejected paths, verification, metrics, manifest/patch hashes, retrieval effect and transfer judgment.

## Outcomes and metrics

- **Success:** focused test proves a real gap and passes only with a minimal correct-surface repair.
- **Partial:** gap demonstrated but repair or broader suite is incomplete.
- **Blocked:** no authoritative contract, evaluator contamination, or integration-only reproduction beyond bounds.
- **Failure:** test exercises the wrong surface or patch only masks the defect.
- **Metrics:** boundary hops, commands/tests, elapsed/tokens, files changed, retrieval score/capsule, wrong paths prevented.
- **Stopping conditions:** contract ambiguity, security relevance, >3 files, 25 commands/45 minutes, non-hermetic dependencies.
- **External approval later:** upstream issue/PR/comment, CI trigger, experience promotion.

## Next-pilot recommendation template

`Public contract / currently untested boundary / failing regression design / transfer relevance to TR-04 / scope / approval.`
