# AEG experience search checklist

This restores the seven-topic list recovered from the 2026-08-21 discussion. It is a classification/search aid, not seven independent queues or seven separate budget pools. General bug repair is a work activity across topics. Resource ownership/lifecycle and regression-test gaps remain priority mechanism tags.

## Topic coverage

| Topic ID | Recovered category | Search terms | Bounded admission rule |
| --- | --- | --- | --- |
| CI_OR_DEPLOYMENT_FAILURE | CI / 部署失败 | build failed, CI regression, workflow, lockfile | Only local, deterministic build/test/package/deployment-artifact checks; no real deployment or access/secret/network-flakiness repair. |
| DEPENDENCY_OR_FRAMEWORK_UPGRADE | 依赖 / 框架升级 | breaking change, upgrade, migration, deprecated, ImportError | Pin old/new dependency versions and assert the relevant behavior or API contract. |
| TEST_FRAMEWORK_MIGRATION | 测试框架迁移 | pytest, jest, vitest, playwright, test migration | Preserve intended assertions and test semantics; a green suite alone is insufficient. |
| CROSS_MODULE_REGRESSION | 跨模块回归 | regression, wrapper, delegation, serialization, compatibility | Prefer a bounded public-API-to-implementation path with a small reproducer. |
| MULTI_AGENT_COORDINATION | 多 Agent 协作 | handoff, duplicate task, shared state, worktree, coordination | Only deterministic fixtures for handoff/state/merge defects; do not build an open-ended multi-agent benchmark or install agents. |
| MISLEADING_REPAIR_OR_REPEATED_FAILURE | 误导性修复 / 重复失败 | false positive, vacuous, revert, test gap, still failing | Preserve the rejected repair and demonstrate why existing green tests missed the actual requirement. |
| ENVIRONMENT_DRIFT | 环境变化导致经验失效 | version, Python, Node, platform, dependency, environment | Pin both environments; distinguish invalidated advice from unrelated setup failure. |

## Three work types in one candidate pool

- HISTORICAL_REPLAY: Prefer an upstream merged repair with a small regression test and immutable pre/post commits. Already solved, closed or old is allowed. A closed/unmerged proposal can be screened, but its correctness and adoption remain unverified until supported separately. Keep original authorship and source licensing/provenance. Do not repost an existing answer simply for exposure.
- LIVE_OSS_CONTRIBUTION: Relevant open issue/PR with recent actual participation and an unanswered, objectively testable contribution. Check the current thread, existing solutions and contribution policy before proposing work. Draft only; publication is disabled.
- TRANSFER_CHECK: Only the already authorized single check, currently OSS-PYSDK-3494-RESTART-LIFECYCLE. No extra transfer experiments are authorized by a candidate report.

Scope remains anthropics/skills, modelcontextprotocol/python-sdk, andrewyng/context-hub and agentskills/agentskills. SOFA is read-only. Normal dependency installation and source inspection for an in-scope case do not authorize prospecting new repositories. Do not resume old benchmark batches or legacy experiments.

## Each scan slot

1. Read the trusted policy, one current branch snapshot, the daily candidate tally, queue and prior scan cursor. Recheck relevant updates since the cursor.
2. Prefer deterministic dependency/SDK changes, lifecycle cleanup and regression-test gaps. Rotate through the seven topic tags over the week; there is no per-topic quota and no need to search every topic on every run.
3. If fewer than three qualified unique candidates exist for the local day, use the remaining slot budget to search historical small fixes/tests, initially the past 90 days, then older results if useful. Do not stop merely because one new issue was found. Stop at the daily candidate cap, available slot budget, an exhausted bounded search, or an actual access blocker.
4. Use terms in the table with repository and issue/PR filters. Live scans check open issue/PR activity; historical scans check merged repair/test PRs first. Fix/merge status must be fetched, not inferred from a title or closed issue.
5. Record reviewed/qualified/rejected counts, rejected reasons, work type/topic, cursor and stop reason even if no candidate qualifies. Write one small append-only scan report per scheduled slot, not a user notification per result. An unchanged replay of the same slot is deduplicated.
6. Rank by objective-verification likelihood, expected total minutes, evidence novelty and reuse potential. Maintainer activity affects live contributions, not historical replay. Any numeric score is a prioritization heuristic, not measured success probability.

Daily three candidates is a supply target and cap, not a requirement to fabricate candidates. Use an existing qualified backlog before scanning the same material again. A backlog of ready work should shift effort toward verification, not generate duplicate tasks.

## Minimal evidence and counting

- Freeze issue input, source revisions, relevant dependencies and the oracle before execution. Historical repair: the same regression test must fail before and pass after the repair for the intended reason. Setup/import failure unrelated to the bug is BLOCKED, not reproduced.
- An upstream test suite passing does not prove the public requirement was fixed. Use a discriminating assertion; preserve misleading fixes or diagnostic-only workarounds as such.
- Deduplicate across task revisions, source issue/PR, root-cause identity and upstream repair. One defect across two SDK versions is one experience with multiple observations. Another independent real defect with the same mechanism may be a separate case in the same mechanism family.
- Replays are not agent-independent discoveries, new upstream fixes, external adoption, or AEG transfer. Synthetic fixtures must be labeled and not counted as external bugs.
- Preserve all outcomes. Only objectively verified cases become verified Registry candidates. Failures, inapplicability and inconclusive transfer remain auditable evidence without inflating repair counts.
- Before closing a verified case, persist its portable Registry candidate and evidence or an explicit archival-blocked receipt under the existing protocol. No main-branch promotion or website deployment is authorized.
