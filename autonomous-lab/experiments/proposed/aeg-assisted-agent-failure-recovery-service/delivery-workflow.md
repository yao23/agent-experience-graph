# Proposed delivery workflow

This is a future workflow design, not an executed service.

1. **Qualify:** apply the [intake](intake-questionnaire.md),
   [eligibility](eligibility-checklist.md), license, privacy, freshness, and
   contribution gates.
2. **Freeze:** record source revision, task statement, oracle, budgets, allowed
   paths, and blindness conditions before diagnosis.
3. **Retrieve:** query AEG before diagnosis; record recommendation or abstention
   and whether any retrieved experience is eligible.
4. **Diagnose:** use ordinary coding-agent capability to reproduce and identify
   the root cause. Do not attribute this work to AEG unless retrieval materially
   changed it.
5. **Recommend:** propose the smallest recovery or repair supported by evidence.
6. **Verify:** run the frozen pre/post oracle and relevant regression suite.
7. **Report:** produce the [customer report](customer-report-template.md) with
   provenance, limitations, and acceptance status.
8. **Capsule review:** propose a sanitized reusable experience only when legal,
   privacy, freshness, reuse, and external-evidence gates justify it. Promotion
   remains separately approved.

Phase 0 performs none of these steps on a real customer task. Phase 1 entry
requires every gate in the [future protocol](baseline-treatment-protocol.md).
