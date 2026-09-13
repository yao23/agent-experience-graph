# Provenance archival addendum — 2026-09-13

This additive format change follows the operator's request to persist minimal
provenance in AEG Experiences. It changes archival metadata only. It does not
replace `AUTHORIZATION.json`, grant new execution or publishing authority,
increase budgets, change schedules, or reopen completed experiments.

## New archival work

For each newly verified Registry candidate, populate the optional-for-legacy
`provenance.record` extension described in `docs/provenance-record.md` and the
existing Experience schema. Use existing context/verification/failure fields
through the defined JSON Pointers. Capture source URLs, contributor roles,
prior work, digest-addressed public evidence, external replay reports and
scoped rights information while doing the already authorized task.

Unknowns are acceptable when explicit: null unknown source/tested revisions,
unknown model/harness versions with reasons, empty external replay list if none
has been found, and unrequested or unknown consent. Never fabricate a replay,
license grant or causal benefit. Missing evidence needed for a verified claim
still produces the existing `ARCHIVAL_BLOCKED` outcome. Missing optional
historical metadata is not a reason to rerun a completed repair.

For a later third-party report, update the same Experience ID; preserve prior
history through non-force Git commits. Deduplicate by source URL and replay ID.
Distinguish `SELF_REPORTED`, `EVIDENCE_ATTACHED` and `AUDITED`. A source URL alone
is not an audited replay. Do not change verification status, token savings or
transfer claims merely because a comment, hash or new provenance field exists.

Before a terminal archival receipt:

1. Validate schema and metadata with the existing validator.
2. Validate all referenced files and SHA-256 bytes using the validator's
   `--check-evidence` option (or its `validate_evidence_files` function).
3. Check stable ID/slug uniqueness in a temporary merged Registry and confirm
   generated machine JSON retains the extension.
4. Preserve existing redaction, patch-integrity and non-force write checks.
5. State the candidate commit, artifact paths and archival outcome in the
   existing RESULT receipt. Count the case once; reports and version rows are
   observations. Include archival time in existing shared budgets.

## Local task adoption

The operator should supply the immutable GitHub commit containing this addendum
to the existing Mac Codex task. That supplied commit is the format reference;
it does not replace the trusted execution-policy commit/digest already stored
outside the writable branch.

Read the addendum, schema and validator at the supplied commit. Update only the
archival instructions of `aeg-experience-foundry-pilot-v0-1` in place: future
eligible candidates must include `provenance.record` v1.0.0 and pass the checks
above. Store the format commit alongside the existing policy reference. Preserve
the task's enabled state, current schedule, model, reasoning, deadline, scope,
budgets, claims, completed results and workspace changes. Apply the prompt change
at a safe configuration boundary; do not interrupt an in-flight solver or alter
its inputs. Do not create another task or scheduler.

This adoption is configuration-only: do not run a queued experiment, regenerate
#1742, send upstream comments or modify main. Read back the saved prompt and
report the actual task ID, before/after prompt hashes, format commit, unchanged
policy digest and whether a scheduled run has used the new format. If the prompt
already contains the same format revision, verify it instead of appending again.
Use the existing authorized non-force receipt protocol for an adoption receipt;
record `scheduled_execution_occurred: false` for this setup operation. Public
receipt evidence does not expose local absolute paths or account secrets.

## Frozen sources

#1742's candidate may gain current provenance at a later coordination commit.
Its frozen source at `94f25c36bab3f4729413ebc20dbb4d310c64ea23` remains the input
selected for #3494. This addendum does not change that source, the target issue,
oracle, solver contexts, task ID/revision, existing result or deduplication state.

No automatic promotion into `experiences/registry.json`, no site deployment and
no mass backfill are part of this update. Current new-format availability on
GitHub and actual adoption by a scheduled local consumer are separate facts.
