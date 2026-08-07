# 07 — AEG self-maintenance

## Operating contract

- **Project category:** bounded internal audit or deterministic maintenance check in AEG itself.
- **Independent external value:** improve reliability for AEG users through consistency, privacy, schema, package or documentation checks.
- **AEG consumption/production:** query AEG about its own maintenance, then produce a candidate limited to internal operational evidence; do not claim cross-project validation.
- **Selection criteria:** current clean batch worktree; deterministic existing or new check; ≤3 files; no conflict with pending release/PR work; objective before/after oracle.
- **Exclusions/safety:** releases, version bumps, PR merges, changes to `verified.json`, broad refactors, product claims, unrelated pending work, external publication.
- **Bounded pilot:** audit up to five maintenance candidates, score three, select one; 30 minutes/20 commands.

## Procedure

1. **Freeze:** record AEG commit/version, candidate inconsistency, exact files, current check/output, success oracle and non-interference proof; hash manifest.
2. **Retrieve:** query current verified library for schema/privacy/determinism/package/docs consistency; record matches/evidence/threshold/capsule without forcing self-match.
3. **Execute:** reproduce on the isolated batch branch; add the smallest check/fix; keep candidates staged and do not modify promoted experiences or release artifacts unless explicitly in scope.
4. **Verify:** focused regression, full AEG Python tests, schema and semantic validators, package equality/privacy scan or link checker as applicable, diff and worktree audit.
5. **Record:** internal-only candidate with attempts, tools, verification, metrics, hashes, files, limitations, retrieval effect and explicit non-PMF classification.

## Outcomes and metrics

- **Success:** real internal inconsistency reproduced and a bounded deterministic check/fix passes all relevant AEG validation.
- **Partial:** audit finds a concrete issue but repair conflicts with pending work or broader validation is incomplete.
- **Blocked:** clean isolation cannot be preserved, issue overlaps pending PR/release work, or change needs user/product decision.
- **Failure:** proposed check is nondeterministic/noisy or breaks validated behavior.
- **Metrics:** files/records audited, commands/tests, runtime, diff size, tokens/cost, retrieval score/capsule.
- **Stopping conditions:** overlap with pending work, >3 files, >20 commands/30 minutes, release/version change, external action.
- **External approval later:** merge/cherry-pick, push/PR, release, promote candidate, publish operational claims.

## Next-pilot recommendation template

`Invariant / current failure / bounded check or fix / overlap audit / verification / internal value only / approval.`
