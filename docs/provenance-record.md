# Provenance Record v1

An Experience states a reusable claim together with the evidence and conditions
that support it. `provenance.record` adds attribution and external replay history
to the existing Registry format. It is optional for legacy records and versioned
independently as `schema_version: "1.0.0"`. The existing Experience ID, schema
version, verification status and frozen experiment inputs remain stable.

The complete record travels in the same Experience JSON. Existing environment,
agent, verification and failure data are referenced by JSON Pointer relative to
the containing Experience; there is no second copy to reconcile. Export the
Experience and its repository-relative evidence files together when migrating
to a website or database. Keep source commits and digest-bearing bytes intact.

## Field mapping

| Field in `provenance.record` | Purpose |
| --- | --- |
| `schema_version` | Version of this extension, currently `1.0.0` |
| `claim` | Bounded claim, including what was actually tested |
| `task_origin` | Original task or review URL, known revision or null, context |
| `prior_art` | Earlier issues, implementations, SDK documentation and other work |
| `contributors` | Public identity, role, specific contribution and source URLs |
| `models_and_harnesses_ref` | `/context/agent_context` |
| `environment_ref` | `/context/environment_fingerprint` |
| `trace_digest` | Public artifact paths, SHA-256 digests and their scope |
| `verification_ref` | `/verification_method` |
| `independent_replays` | Individually sourced external replay reports and their evidence status |
| `negative_results_ref` | `/failed_attempts`; exclusions also remain in `applicability` |
| `disputes_and_limits` | Attribution/evidence issues, unresolved gaps and source URLs |
| `license_and_consent` | AEG metadata license, scoped upstream licenses, consent evidence and reuse limits |

The schema is in `experiences/verified-experience.schema.json` under
`definitions.provenanceRecord`. A real populated example is the staged
`trace-2026-09-09-anthropics-skills-mcp-http-client-lifecycle` candidate in
`coordination/evidence/registry-candidates/`.

## Evidence is not a single ladder

Keep the existing `verification_status` values. Local execution, external
reproduction, cross-model transfer, upstream acceptance and attribution are
different claims. A replay report does not automatically advance any of them.
Do not add a `COMMUNITY_ACCEPTED` badge without a separately defined decision
process. New failures can narrow applicability or invalidate a prior conclusion;
confidence is not required to increase monotonically.

Each external replay has a stable ID, reporter, source URL and timestamp,
reported environment, tested commit (null when unknown), result and limitations:

| Replay evidence status | Meaning |
| --- | --- |
| `SELF_REPORTED` | Someone reports a result; underlying execution has not been audited |
| `EVIDENCE_ATTACHED` | Exact tested commit and digest-addressed artifacts are available; audit may still be pending |
| `AUDITED` | Artifacts were reviewed; an audit records reviewer, date, scope, independence basis and evidence URLs |

These labels describe evidence handling, not guaranteed truth. A GitHub account
or clean virtual environment alone does not establish organizational or human
independence. Audit metadata must disclose what was checked. A skip in an old
dependency branch is not a passing execution of that branch. Observed PR head
must never substitute for a replay's unknown tested SHA.

The legacy `promotionEvidence.status` additionally accepts `reported-passed`:
its `validatedCommitSha` names the commit the source reports about, not a commit
independently run by AEG. Its resolver must identify that report. Reserve
`observed-passed` for observed execution evidence and record its scope.

## Attribution and rights

Credit the original issue author, implementation author, reviewer, regression
author, reproduction reporter and assisting system for their actual roles.
Do not describe a PR author as a project maintainer without supporting evidence,
or assign AEG credit for discovering an already published historical repair.
Model and harness versions remain explicitly unknown when not captured.

Separate AEG-authored metadata from upstream code and third-party prose. A source
being public does not establish consent to republish or relicense its content.
Unknown rights permit an attribution link and a bounded original factual
summary; they do not authorize copying a raw conversation or changing a license.
Record explicit consent only with evidence. `NOT_REQUESTED` does not mean
`GRANTED`; `NONE_REPORTED` disputes does not certify that no dispute exists.

SHA-256 checks content integrity against specified bytes. A hash alone does not
prove author identity, creation time, truth, originality, consent or permanence.
Commit-addressed links and repository history add traceability; neither is an
independent certification. Do not require raw private conversations or private
machine paths to complete a public record.

## Validation and migration

Use the existing validator for schema and semantic checks. For a staged
candidate, include `--check-evidence` to check paths and actual artifact bytes:

```bash
python3 scripts/validate_verified_experiences.py \
  --library coordination/evidence/registry-candidates/trace-2026-09-09-anthropics-skills-mcp-http-client-lifecycle.json \
  --check-evidence
python3 -m unittest scripts.test_provenance_record
```

The Python `validate_evidence_files` function performs the same file/digest
checks. `validate_library` alone checks metadata, not the bytes of artifacts.
These checks do not execute upstream code.

Legacy records remain valid without this extension. New archival production
uses the extension after the consumer adopts `coordination/PROVENANCE_ARCHIVAL.md`.
Backfill only when source evidence is available, retain unknowns, and never rerun
a repair merely to fill metadata. Count a new external report as an observation
on the same Experience ID, not as another Experience.

Promotion to the public Registry and site is a separate change. The machine JSON
builder already preserves the complete Experience object, including this
extension; a staged candidate is not automatically published on the main site.
