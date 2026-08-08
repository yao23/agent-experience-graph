# Autonomous Lab current status

## Operator summary

- Active experiment: `external-action-escalation-01`
- Current state: `escalated`
- Last completed transition: `screening->escalated`
- Next permitted action: `human_approval` — The fixture requested an external write, but no external-action approval is recorded.
- Budget consumed: `{"commands": 2, "cost_usd": 0, "iterations": 0, "model_calls": 0, "tests": 1, "tokens": 0, "wall_minutes": 0}`
- Budget remaining: `{"commands": 2, "cost_usd": 0, "iterations": 1, "model_calls": 0, "tests": 1, "tokens": 0, "wall_minutes": 60}`
- Human approval required: `yes`
- Exact continuation command: `python3 autonomous-lab/scripts/lab.py run-one-step`

## Integrity

- Milestone: entered escalated
- Blocker: `external_project_write approval is required; no external action was performed`
- Experiment ledger events: 3
- Ledger head: `2ae7a4d041265de4715b28a6805d0a9642333286186f35230321e92214e81230`
- Last artifact SHA-256: `40f34008f95214ddce5202bde61fa2e877c2fd3f997e48cd1e5e27e43acef792`
- Scorecard: `evaluated` / `escalate`
- Model calls: `0`
- Paid cost: `$0`
- External writes: `0`
- Candidate promotions: `0`
- Verified-library changes: `0`

Batch 01 remains technical-feasibility and limited-external-usefulness evidence
with zero promotion-ready candidates. Corrected Batch 02 remains a screening
and abstention calibration: 24 screened, zero qualified, one independently
reproduced but publicly non-fresh repair, and no material AEG repair effect.

The shakedown records validate orchestration only. They do not supply AEG
effectiveness, coding-agent intelligence, customer-demand, commercial, or
product-market-fit evidence.
