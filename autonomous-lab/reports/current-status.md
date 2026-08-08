# Autonomous Lab current status

## Operator summary

- Active experiment: `aeg-assisted-agent-failure-recovery-service-v0`
- Run ID: `0e3b7d22-15fb-49fe-800a-ad090d8986df`
- Experiment kind: `commercial`
- Current state: `running`
- Last completed transition: `ready->running`
- Next permitted action: `transition` — next lifecycle evidence may be recorded
- Budget consumed: `{"commands": 2, "cost_usd": 0, "iterations": 2, "model_calls": 2, "tests": 2, "tokens": 0, "wall_minutes": 0}`
- Budget remaining: `{"commands": 62, "cost_usd": 0, "iterations": 6, "model_calls": 6, "tests": 126, "tokens": 0, "wall_minutes": 480}`
- Human approval required: `no`
- Another scheduled run useful: `yes`
- Exact continuation command: `python3 autonomous-lab/scripts/lab.py scheduled-step --persist-commit`
- Latest error or blocker: `None`

## Integrity

- Milestone: entered running
- Blocker: `None`
- Experiment ledger events: 5
- Ledger head: `79f356d830cdb6d67e9779eb809906aaaba8785a3bb444c1c1499cea81f5ce08`
- Last artifact SHA-256: `ce6cf7c7e033cd5f309354a44aad153bf211c0b9a2ca0c9b18ad1d6b19fd84bb`
- State SHA-256: `04fb299ad4a490bb567d863d1c6c51b56abb797570c571621aa960b390d994e1`
- Scorecard: `incomplete` / `pending`
- Model calls: `2`
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
