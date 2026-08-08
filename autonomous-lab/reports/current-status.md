# Autonomous Lab current status

## Operator summary

- Active experiment: `aeg-assisted-agent-failure-recovery-service-v0`
- Run ID: `None`
- Experiment kind: `commercial`
- Current state: `completed`
- Last completed transition: `evaluating->completed`
- Next permitted action: `human_approval` — Phase 0 is complete; Phase 1 recruitment and every external action remain blocked.
- Budget consumed: `{"commands": 4, "cost_usd": 0, "iterations": 4, "model_calls": 4, "tests": 4, "tokens": 0, "wall_minutes": 0}`
- Budget remaining: `{"commands": 60, "cost_usd": 0, "iterations": 4, "model_calls": 4, "tests": 124, "tokens": 0, "wall_minutes": 480}`
- Human approval required: `yes`
- Another scheduled run useful: `no`
- Exact continuation command: `python3 autonomous-lab/scripts/lab.py run-one-step`
- Latest error or blocker: `Phase 1 recruitment is not approved`

## Integrity

- Milestone: Phase 0 completed; awaiting a human decision on Phase 1 seed-user recruitment
- Blocker: `Phase 1 recruitment is not approved`
- Experiment ledger events: 7
- Ledger head: `2c03f761117c1d5295c2d27d24529498e5c6e4b0af12534bb1b2427da1573d7d`
- Last artifact SHA-256: `ce6cf7c7e033cd5f309354a44aad153bf211c0b9a2ca0c9b18ad1d6b19fd84bb`
- State SHA-256: `5cf2314cdb78bd6f162daa966e6d590efb4ea8819f78b2a9bb8512c8f4305a36`
- Scorecard: `evaluated` / `complete`
- Model calls: `4`
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
