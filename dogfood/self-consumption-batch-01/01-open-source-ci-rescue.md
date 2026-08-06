# 01 — Open-source CI rescue

## Operating contract

- **Project category:** repair one real public CI or test-infrastructure failure.
- **Independent external value:** restore a failing check or runtime-specific test without weakening its oracle.
- **AEG consumption/production:** retrieve prior CI/repair evidence before execution; produce a sanitized failure-signature, recovery, and verification record.
- **Selection criteria:** permissive license; activity within 90 days; failing commit still current; open issue/check; no equivalent main-branch fix; no active repair PR; outside contributions allowed; deterministic local reproduction; ≤3 files expected.
- **Exclusions/safety:** secrets, cloud services, security issues, flaky-only failures, proprietary code, unclear license, expensive builds, external workflow triggers, existing complete fixes.
- **Bounded pilot:** up to five candidates, score three, select one; 45 minutes/25 investigative or repair commands; one local patch and one normal verification path.

## Procedure

1. **Freeze:** record repository, license, commit, issue/check URL, exact failure, environment, reproduction command, success criteria, expected scope, contribution policy, freshness checks; SHA-256 the manifest before source diagnosis.
2. **Retrieve:** query current `experiences/verified.json` with task/subtasks/constraints; record ranked scores, 0.05 threshold, evidence, capsule size, recommendation or abstention. Never override the threshold.
3. **Execute:** clone under `/tmp`; reproduce before editing; log hypothesis/evidence/action/result; make the smallest repository-style repair; do not inspect future fixes until the patch is frozen.
4. **Verify:** pre-fix failure, focused post-fix test, related suite, broader lint/build where feasible, diff audit, no new skips or weakened assertions.
5. **Record:** candidate must contain provenance, attempts, tools/skills, failure/recovery, verification, metrics, manifest and patch hashes, changed files, limitations, retrieval tags, use cases, and retrieval effect. Do not promote it.

## Outcomes and metrics

- **Success:** original failure reproduced and relevant post-fix checks pass.
- **Partial:** bounded repair evidence exists but a related/broad oracle remains unresolved.
- **Blocked:** reproduction or authorization needs unavailable credentials, OS/service fidelity, license clarity, or a non-current failing state.
- **Failure:** attempted patch does not repair the reproduced failure.
- **Metrics:** candidates screened, score dimensions, commands, test executions, elapsed milliseconds if captured, tokens/cost or `null`, files/lines changed, retrieval score/threshold/capsule length.
- **Stopping conditions:** 45 minutes, 25 commands, nondeterminism after bounded retries, scope expansion beyond three files, safety/legal issue, or discovery of a complete fix.
- **External approval later:** fork/push, issue comment, maintainer contact, PR, workflow trigger, candidate promotion.

## Next-pilot recommendation template

`Target / freshness evidence / expected oracle / unresolved risk / recommended action (execute, collect evidence, abandon) / approval needed.`
