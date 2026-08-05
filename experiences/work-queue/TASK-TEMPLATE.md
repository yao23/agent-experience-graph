# <TASK-ID> — <short title>

Status: queued
Owner: Codex
Category: <test-repair | build-ci-recovery | api-dependency-migration>
Started: —
Last updated: —
Attempts: 0
Time budget: 30 minutes
Current blocker: none

## Source lock

- Upstream repository:
- License and URL:
- Benchmark and task ID:
- Buggy commit:
- Focused test:
- Expected failure signature:
- Evaluator-only fixed commit:
- Golden patch inspected: no

Do not inspect the evaluator-only fixed commit or its diff until the first
candidate patch has been saved and its SHA-256 recorded.

## Phase checklist

- [ ] Isolated checkout created at the exact buggy commit
- [ ] License and public provenance rechecked
- [ ] Dependencies installed without credentials
- [ ] Original focused failure reproduced
- [ ] Failure signature sanitized and recorded
- [ ] Root-cause hypothesis written before editing
- [ ] Baseline attempt completed
- [ ] Candidate patch hash recorded
- [ ] Focused test passed
- [ ] Relevant regression tests passed
- [ ] Full suite attempted or reason for omission recorded
- [ ] No upstream push/comment/PR performed
- [ ] No raw prompt/log/patch/private path committed
- [ ] Experience candidate written
- [ ] Candidate schema and semantic validation passed
- [ ] Retrieval smoke test passed
- [ ] Promotion decision recorded

## Intent

What observable behavior must be repaired?

## Context

- Runtime and dependency versions:
- Test scope:
- Failure type:
- Failure signature:
- Environment constraints:
- Related prior AEG experience retrieved:
- Retrieval score/evidence:

## Reproduction

Commands:

```bash
# exact commands only; remove local absolute paths
```

Observed result:

- Exit code:
- Failing tests:
- Sanitized error summary:
- Duration:
- Reproduction confidence: <high | medium | low>

If reproduction fails because historical dependencies no longer install, prefer
the benchmark container or create a dependency-free fixture that preserves the
failure mechanism. Mark any adapted fixture clearly; do not silently substitute
it for the upstream project.

## Root-cause hypotheses

Write these before editing.

| # | Hypothesis | Evidence for | Evidence against | Test |
|---:|---|---|---|---|
| 1 | | | | |

Selected hypothesis:

## Attempts

### Attempt 1

- Patch intent:
- Files changed:
- Commands:
- Focused result:
- Regression result:
- Patch SHA-256:
- Failure or recovery lesson:
- Cost: duration, commands, tests, non-cached tokens when available

### Attempt 2

Only create after Attempt 1 produces new evidence.

### Attempt 3

Final allowed attempt.

## Validation

| Check | Command | Result | Duration |
|---|---|---|---:|
| Original failure before patch | | | |
| Focused test after patch | | | |
| Related tests | | | |
| Full suite | | | |
| Candidate schema | | | |
| Retrieval smoke test | | | |

Changed-file allowlist:

Regression limitations:

## Experience record

Candidate path: `experiences/candidates/<TASK-ID>.json`

Record:

- Intent
- Context and failure signature
- Diagnostic steps
- Skills and tools actually used
- Sanitized artifacts and hashes
- Failed attempts and negative evidence
- Recovery pattern
- Objective outcome
- Cost: wall time, commands, test executions, attempts and tokens when available
- Public provenance, license and commit SHAs
- Limitations and generalization boundary
- Retrieval tags and recommended-for queries

Do not claim success if only the candidate patch was created. Success requires
objective focused verification. Use `partial` when regression coverage is
incomplete and `failure` when the budget expires without a verified patch.

## Evaluator comparison

Complete only after the first candidate patch hash exists.

- Fixed commit inspected:
- Candidate patch semantically equivalent:
- Candidate patch textually identical:
- Unexpected alternative solution:
- Information leakage detected:

The human fixed commit is validation evidence, not an answer source.

## Promotion

Decision: pending

Promotion requirements:

- [ ] objective outcome
- [ ] reproducible or adapted fixture documented
- [ ] public provenance and license
- [ ] sanitized record only
- [ ] schema and semantic validation
- [ ] negative evidence retained
- [ ] retrieval query returns the candidate for the intended task family
- [ ] no unsupported generalization claim

Reason:
