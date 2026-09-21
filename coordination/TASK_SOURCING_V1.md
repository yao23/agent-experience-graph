# Evidence-first task sourcing v1

Operator-requested configuration change, 2026-09-20 America/Los_Angeles. This document specifies candidate discovery and attention management, not a new execution authorization, product release or completed experiment. The implementation commit must be supplied through trusted task prompts; future edits are not automatically adopted.

## Purpose and precedence

Find a useful, independently verifiable contribution to an actual problem; reuse existing mechanisms and assets; stop gathering work when execution is the bottleneck. The daily three-candidate figure remains a cap and an aspiration, never a requirement to fill the queue. Within discovery/triage only, this operator-requested rule replaces older instructions to keep searching merely because fewer than three candidates were found. All policy limits and hard exclusions still control.

Keep `coordination/AUTHORIZATION.json` unchanged. Keep the local execution spec pinned at 573d3b45c6b806fb030a7c95729eb2787c3e3c0a, including its CODEX_ENTRY.md and SEARCH_CHECKLIST.md. Preserve the separately accepted provenance-format commit 74c73ef335f5ecc87a26204d4a50ee839f96d620. Current-tip checklist changes are for cloud sourcing, not a replacement for the local frozen checklist. Read dynamic queue, receipts, budget and pause state at a single current snapshot, verifying current authorization against the trusted digest.

No new scheduler, repository, model, paid API, concurrency, deadline, schema migration, outreach or execution is authorized. Do not modify existing frozen task identity/revision, source, oracle, threshold, budget or valid claim to implement this sourcing change. Startup OS remains the sole runtime tasks.json writer. Existing #1742, legacy intake/OAC-01 and #3494 restrictions are preserved. All work stops at the original 2026-09-24 23:59 America/Los_Angeles deadline.

## Two primary entry points and one matching aid

1. ACTIVE_PR_VALIDATION_GAP: an actual participant needs a regression test, independent reproduction, version check or clarification of a specific failure path. Existing assignees, a proposed patch or green CI are not automatic exclusions. Verify current thread, latest head, existing coverage and contribution policy; distinguish an implementation author from a maintainer.
2. WORKAROUND_PAIN: a user is pinning/downgrading, carrying a local patch, disabling functionality or repeating manual work, and there is evidence they still want to remove that workaround. A workaround alone is not purchase intent or current urgency.
3. EXPERIENCE_NEIGHBOR is a matching aid, not a separate quota: connect a candidate to a verified source mechanism, its applicability/ownership conditions and an executable asset. Similar words or similar code are only hypotheses, not verified bugs or demand. Do not leak a target answer into frozen transfer solver inputs.

Stay in anthropics/skills, modelcontextprotocol/python-sdk, andrewyng/context-hub and agentskills/agentskills; SOFA remains read-only. Historical replay remains valid for research with fixed pre/post commits and a discriminating test. It does not require an active buyer or recent maintainer participation. Do not reopen a previously exhausted broad stale-PR campaign or use the new sourcing approach to expand repositories.

## Evidence instead of numerical scores

For every shortlisted deliverable record five checks: an identifiable need, observable acceptance, recurrence evidence, bounded effort and a concrete reusable output. Use SUPPORTED / UNSUPPORTED / UNKNOWN / NOT_APPLICABLE with original references, observation time and limitations; claims and inferences must be distinguishable. UNKNOWN is an evidence gap, not a pass and not an automatic permanent rejection. No 0-100 task-value or commercial-confidence scores.

Separate LIVE_DELIVERY evidence from RESEARCH_REPLAY and TRANSFER_EVALUATION. These are report labels, not replacements for existing task_type values. Willingness to pay and buyer identity are optional observations for technical triage; do not fabricate them or use their absence to reject authorized historical replay. They remain required where the separate PMF frontier policy requires them before ACTIVE_PMF_CANDIDATE promotion. Public technical demand is not willingness to pay; a PR author's acceptance is not organization-wide adoption.

Cut an issue into a useful small deliverable: in a pinned environment, verify or improve one behavior, with one discriminating check and explicit exclusions. Confirm that this slice would help the intended recipient when live demand is claimed. A time cap is a stop rule, not a promise of success. Setup failure unrelated to the defect is BLOCKED, not reproduction or useful delivery by default.

## Three-stage triage

A. READ: inspect public metadata/source only. Check whether the need is current, whether another change solved it, actual participant activity and a plausible bounded check. `updated_at` is not last human activity; closed is not merged; no linked PR does not prove nobody is working on it. Stop excluded work before any installation/execution.

B. PROBE: choose exactly one cheapest next action resolving the most important unknown. Examples: inspect the latest related commit, identify an existing test entry, draft one clarification question, or verify a second independent case shares the mechanism. Sending the question remains draft-only. Local dependency installation, test execution and environment probes require the existing local authorization, budget admission and isolation; cloud triage never starts them.

C. EXECUTE_READY: only Startup OS may promote an otherwise eligible bounded task under the unchanged queue contract. A triage recommendation is not READY, CLAIM or authority. The local consumer alone performs authorized preflight/execution. Use actual receipts, not stale queue labels, to infer execution state.

Use advisory dispositions EXECUTE / PROBE_ONE_GAP / WAIT / DROP inside existing reports, not as new executor states. WAIT means unconfirmed or temporarily blocked, not no demand. DROP must state an observed reason. Preserve frozen work; do not retrofit an evidence card as a new eligibility gate for existing tasks.

## Backpressure and work in progress

Keep at most one active execution globally, including any authorized transfer. When none is active, keep at most one selected dispatch-ready next task. Maintain at most two actively pursued evidence-gap cards across runs, not two per schedule or per repository. Existing qualified backlog stays intact and does not count as active probing; do not delete or clone it to satisfy the limit.

Before broad discovery, reconcile current queue, claims/results and prior sourcing reports. Pause broad acquisition when any of these holds:
- an active execution or already selected READY task needs completion;
- two evidence-gap cards already occupy attention;
- existing qualified work is blocked by a shared execution prerequisite, such as isolation or unresolved budget accounting.

Under pressure: recheck only material status changes and, when useful, the one most important existing evidence gap; preserve the scan cursor, charge actual/UNKNOWN cost, and record BACKPRESSURE_EXISTING_WORK or EXECUTION_BLOCKED_NOT_SUPPLY. Do not search for more tasks to avoid a shared blocker. After a terminal result, real invalidation or resolved capacity gap, reuse existing qualified backlog before fresh search. Report access failure as access failure, not exhausted supply. A zero-candidate slot is valid.

This is a prospective acquisition/attention rule, not an automatic rewrite of frozen priorities or an instruction to rerun #3494. No new case may displace an existing valid claim. Do not reset UNKNOWN reservations, failed-call costs or case counters. Read-only maintenance still costs budget; stop rather than performing a nominally free scan when the shared slot/day allowance is exhausted.

## Minimal evidence card

Embed compact cards as optional advisory data in the existing role's report, e.g. `task_sourcing_v1`. Keep all existing report fields. If a strict reader cannot accept additive fields, use an adjacent Markdown report in the same authorized role directory; do not change queue/Registry schemas or build another database.

```json
{
  "candidate_key": "stable source + root cause + deliverable identity",
  "source_url": "UNKNOWN",
  "observed_at": "UNKNOWN",
  "source_revision": "UNKNOWN",
  "entry_point": "ACTIVE_PR_VALIDATION_GAP",
  "evidence_lane": "LIVE_DELIVERY",
  "deliverable": "One behavior, pinned environment, check and exclusions",
  "checks": {
    "need": {"state": "UNKNOWN", "evidence": []},
    "acceptance": {"state": "UNKNOWN", "evidence": []},
    "recurrence": {"state": "UNKNOWN", "evidence": []},
    "bounded_effort": {"state": "UNKNOWN", "evidence": []},
    "reusable_output": {"state": "UNKNOWN", "evidence": []}
  },
  "experience_connection": "UNKNOWN; include applicability and counterconditions",
  "main_unknown": "One decision-blocking gap",
  "next_probe": "One permitted, cheapest information-gain action",
  "likely_wasted_work_reason": "Strongest reason this may be pointless",
  "stop_condition": "Observed exit condition; within remaining authorized budget",
  "disposition": "PROBE_ONE_GAP",
  "buyer_or_wtp": "UNKNOWN",
  "cost_actual_or_unknown": "UNKNOWN"
}
```

This is an illustrative template, not a real candidate. Do not persist it as a reviewed/qualified case. Evidence items should identify the source/actor, statement or observation, time and scope; no invented URLs or activity. A family spanning multiple versions is one defect with multiple observations. A genuinely independent defect can be a new case in the same mechanism family.

## Role changes

OSS scan: use the pressure check before acquisition, prefer the two entry points, attach evidence cards only for actual shortlists, and write at most one idempotent small report per existing slot under coordination/reports/oss-scan/. Never write tasks.json or contact upstream.

Startup OS: reconcile receipts and reservations first; preserve frozen queue entries; use the evidence cards to select a bounded next action, not to add readiness bureaucracy. Track the single execution/selected next task and up to two evidence gaps in existing reports. Only this role may write tasks.json. The evening digest remains the sole daily digest and may include one most informative blocker/action. Do not repeatedly add candidates when execution is blocked.

Local Codex: a small optional prompt addendum may be adopted only through a supported in-place update and readback of the existing consumer. Keep the fixed execution and provenance trust anchors, schedule/model/permissions/budgets/expiry intact. Do not read new sourcing docs or full evidence cards into transfer solvers. Execute no new sourcing scans. Consume only the eligible existing queue under the original execution rules; evidence cards are not mandatory for previously frozen tasks. When naturally available in a permitted result/evidence record, identify the produced reusable test/script/check and actual outcome; unknowns remain unknown.

## Calibration and acceptance

Use existing reports and receipts; no dashboard or new scheduled review is needed. Track source -> shortlisted -> qualified -> READY -> CLAIM -> verified -> reusable artifact -> external response/adoption -> repeat request/payment, keeping denominators and costs. These are distinct events, not automatic upgrades. Human/agent minutes unavailable to observation remain UNKNOWN. History replay, original discovery, external adoption, paid demand and AEG incremental transfer remain separate.

Occasionally review a soft-rejected candidate using a cheap read-only check within existing budget to detect overly strict filtering. Never relax hard exclusions or execute a rejected task just to audit the filter.

Acceptance scenarios for configuration review (synthetic rules, not experiment results):
- green active PR + explicit test gap -> inspect the gap; do not reject for green CI;
- recent bot-only activity -> human demand stays UNKNOWN;
- known solved fix -> research replay may qualify; not new live demand;
- technical replay with buyer UNKNOWN -> not rejected solely for missing WTP;
- two SDK versions of one defect -> one case, two observations;
- one READY plus a shared isolation blocker -> pause broad search, report blocker;
- two evidence-gap cards -> no third active probe;
- install/test proposed by cloud scout -> defer to authorized isolated local flow;
- existing frozen case lacks new card -> preserve it; apply original admission;
- valid claim/UNKNOWN reservation -> no replacement claim or budget reset;
- new transfer/model-strength idea -> PROPOSED_NOT_AUTHORIZED, no arm;
- configuration saved/read back -> not a scheduled run, repair or PMF result.
