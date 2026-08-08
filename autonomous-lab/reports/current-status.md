# Autonomous Lab current status

## Operator summary

- Active experiment: `aeg-assisted-agent-failure-recovery-service-v0`
- Run ID: `a9d72df5-7fd7-4724-af9f-aaccf5120f45`
- Experiment kind: `commercial`
- Current state: `ready`
- Last completed transition: `preregistered->ready`
- Next permitted action: `transition` — next lifecycle evidence may be recorded
- Budget consumed: `{"commands": 1, "cost_usd": 0, "iterations": 1, "model_calls": 1, "tests": 1, "tokens": 0, "wall_minutes": 0}`
- Budget remaining: `{"commands": 63, "cost_usd": 0, "iterations": 7, "model_calls": 7, "tests": 127, "tokens": 0, "wall_minutes": 480}`
- Human approval required: `no`
- Another scheduled run useful: `yes`
- Exact continuation command: `python3 autonomous-lab/scripts/lab.py scheduled-step --persist-commit`
- Latest error or blocker: `None`

## Integrity

- Milestone: entered ready
- Blocker: `None`
- Experiment ledger events: 4
- Ledger head: `b02aa4af9a0d5e97343beb589f771574a7759372c84ce5cae2057f23ce3c2d56`
- Last artifact SHA-256: `ce6cf7c7e033cd5f309354a44aad153bf211c0b9a2ca0c9b18ad1d6b19fd84bb`
- State SHA-256: `411490f5a29e73bf43c5e457c99755c2a0886d4855aaadbc03b339ebf3815e94`
- Scorecard: `incomplete` / `pending`
- Model calls: `1`
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
