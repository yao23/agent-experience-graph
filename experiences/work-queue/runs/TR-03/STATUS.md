# TR-03 — Scrapy nullable `allowed_domains`

Status: partial
Owner: Codex
Category: test-repair
Started: 2026-08-02
Last updated: 2026-08-02
Attempts: 1
Time budget: 30 minutes
Current blocker: complete upstream regression coverage requires the historical Python 3.8.3 dependency environment

## Source lock

- Upstream repository: https://github.com/scrapy/scrapy
- License and URL: BSD-3-Clause, https://github.com/scrapy/scrapy/blob/master/LICENSE
- Benchmark and task ID: BugsInPy, Scrapy bug 1
- Buggy commit: `c57512fa669e6f6b1b766a7639206a380f0d10ce`
- Focused test: `tests/test_spidermiddleware_offsite.py` plus an adapted direct null regression
- Expected failure signature: `TypeError` when null reaches `re.Pattern.match`
- Evaluator-only fixed commit: `9d9dea0d69709ef0f7aef67ddba1bd7bda25d273`
- Golden patch inspected: yes, only after candidate SHA-256 was recorded

## Phase checklist

- [x] Isolated checkout created at the exact buggy commit
- [x] License and public provenance rechecked
- [x] Dependencies installed without credentials
- [x] Original focused failure reproduced through an adapted direct regression
- [x] Failure signature sanitized and recorded
- [x] Root-cause hypothesis written before editing
- [x] Baseline attempt completed
- [x] Candidate patch hash recorded
- [x] Focused test passed
- [x] Relevant regression tests passed
- [x] Full suite attempted or reason for omission recorded
- [x] No upstream push/comment/PR performed
- [x] No raw prompt/log/patch/private path committed
- [x] Experience candidate written
- [x] Candidate schema and semantic validation passed
- [x] Retrieval smoke test passed
- [x] Promotion decision recorded

## Intent and context

Ignore null entries before applying regex validation. Python 3.9.6 and isolated
current dependencies were used because the benchmark Python 3.8.3 runtime was
unavailable. The upstream focused file passed six tests before repair because
its historical null-case setup override was misnamed; an adapted direct test
reproduced `TypeError` without changing the upstream regression.

Existing AEG retrieval returned no record above `0.05`; no recommendation was
used. The absence of a relevant match is retained as negative evidence.

## Root-cause hypothesis

The URL regex executes on every list element before the later null-filtering
comprehension. Direct invocation with `["example.com", None]` confirmed it.

## Attempt 1

- Patch intent: prefilter null values before all regex operations
- Files changed: `scrapy/spidermiddlewares/offsite.py`
- Focused result: adapted regression passed
- Regression result: adapted test plus six upstream offsite tests passed
- Patch SHA-256: `96f70229d8d68ac038bfc31388869cb95edd903070f9521ead170305782a2421`
- Cost: 1 attempt, 12 completed task commands, 3 test executions; duration and token usage unavailable

## Validation

| Check | Result |
|---|---|
| Upstream focused before repair | 6 passed; intended null setup was unreachable |
| Adapted regression before repair | 1 error, `TypeError` |
| Focused and related after repair | 7 passed |
| Full suite | omitted: historical runtime/dependency parity unavailable within budget |
| Candidate schema and semantic checks | passed |
| Retrieval smoke test | candidate retrieved at `0.1401` for a natural null-before-regex query |

## Evaluator comparison

The candidate and human fix share the null-before-regex root cause. They are not
textually identical or fully semantically equivalent: the human fix also omits
URL-shaped entries from the final allowlist and repairs the upstream test setup.
No evaluator information was viewed before hashing the candidate.

## Promotion

Decision: retain as a partial candidate, not yet append to `verified.json`.
Focused null handling is verified, but full historical regression coverage and
URL-entry parity are incomplete.
