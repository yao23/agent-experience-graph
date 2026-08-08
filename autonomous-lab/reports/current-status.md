# Autonomous Lab current status

## Operator summary

- Active experiment: `aeg-assisted-agent-failure-recovery-service-v0`
- Run ID: `2d363f36-6f80-4cd1-913a-a2bbea4bb843`
- Experiment kind: `commercial`
- Current state: `evaluating`
- Last completed transition: `running->evaluating`
- Next permitted action: `transition` — next lifecycle evidence may be recorded
- Budget consumed: `{"commands": 3, "cost_usd": 0, "iterations": 3, "model_calls": 3, "tests": 3, "tokens": 0, "wall_minutes": 0}`
- Budget remaining: `{"commands": 61, "cost_usd": 0, "iterations": 5, "model_calls": 5, "tests": 125, "tokens": 0, "wall_minutes": 480}`
- Human approval required: `no`
- Another scheduled run useful: `yes`
- Exact continuation command: `python3 autonomous-lab/scripts/lab.py scheduled-step --persist-commit`
- Latest error or blocker: `None`

## Integrity

- Milestone: entered evaluating
- Blocker: `None`
- Experiment ledger events: 6
- Ledger head: `1dcc1a3f389faff7fc25dcd094666c28e5398ebf204c5b375b7aa15e603055a6`
- Last artifact SHA-256: `ce6cf7c7e033cd5f309354a44aad153bf211c0b9a2ca0c9b18ad1d6b19fd84bb`
- State SHA-256: `2da82586f2ef9ff9bf7d70f029593c096d6c926b753036ceb9e11f65eb5edd62`
- Scorecard: `incomplete` / `continue`
- Model calls: `3`
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
