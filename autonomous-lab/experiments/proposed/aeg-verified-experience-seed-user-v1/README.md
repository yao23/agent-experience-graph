# Phase 1 seed-user proposal

Status: **proposed; bounded Stage A recruitment activates only after separate
human review and merge; participant-task execution remains unauthorized**.

This package preregisters a bounded Verified Experience Challenge with three to
five seed developers and no more than five tasks, split into a three-task Stage
A and an optional two-task Stage B that requires a separate approval. The canonical design is
`protocol.json`; `budget.json`, `stopping-policy.json`, and
`approval-record.json` are independently schema-validated. Every recruitment
artifact in `templates/` is an unsent draft.

The Stage A recruitment package in `stage-a-recruitment/` authorizes, only once
its approval record is merged to `main`, a maximum of ten individually reviewed
personalized invitations and three voluntary unpaid enrollments. It permits
minimal eligibility, task-submission, and pseudonymous consent records only.
It does not authorize participant-task execution, AEG queries, model-assisted
diagnosis or repair, private-repository access, experimental evidence retention,
external-project writes, publication, promotion, verified-library changes,
Stage B, or Scheduled Task creation or enablement.

Validate with:

```sh
python3 autonomous-lab/scripts/validate_phase1_seed_user.py
python3 autonomous-lab/scripts/lab.py validate --base-ref origin/main
python3 -m unittest autonomous-lab.scripts.tests.test_phase1_seed_user
```

The next human decision is whether to merge the separate Stage A recruitment
authorization. A draft or ready-but-unmerged pull request grants no outreach
authority, and merging it grants no participant-task execution authority.

Recruitment, participant-task execution, evidence retention, Stage B, result
publication, and experience promotion are separate approval decisions. No stage
continues automatically.
