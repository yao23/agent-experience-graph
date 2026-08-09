# Phase 1 seed-user proposal

Status: **proposed; recruitment and execution unauthorized**.

This package preregisters a bounded Verified Experience Challenge with three to
five seed developers and no more than five tasks, split into a three-task Stage
A and an optional two-task Stage B that requires a separate approval. The canonical design is
`protocol.json`; `budget.json`, `stopping-policy.json`, and
`approval-record.json` are independently schema-validated. Every recruitment
artifact in `templates/` is an unsent draft.

Nothing in this package authorizes outreach, participant onboarding, evidence
retention, task execution, model use, external-project writes, candidate
promotion, verified-library changes, publication, release, payment, secret use,
or Scheduled Task creation or enablement.

Validate with:

```sh
python3 autonomous-lab/scripts/validate_phase1_seed_user.py
python3 autonomous-lab/scripts/lab.py validate --base-ref origin/main
python3 -m unittest autonomous-lab.scripts.tests.test_phase1_seed_user
```

The next human decision is whether to approve this preregistration and
separately authorize bounded recruitment. Approval of the protocol must not be
interpreted as approval to merge its draft PR or contact anyone.

Recruitment, participant-task execution, evidence retention, Stage B, result
publication, and experience promotion are separate approval decisions. No stage
continues automatically.
