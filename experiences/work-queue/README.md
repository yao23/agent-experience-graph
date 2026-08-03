# AEG Public Experience Work Queue

This queue turns public, licensed bug-fix pairs into bounded, auditable AEG jobs.
It is intentionally small: four Test Repair tasks, three Build/CI Recovery tasks,
and three API/Dependency Migration tasks.

## Rules

- Work on one task at a time in an isolated checkout, container, or worktree.
- Never push, comment, or open a PR in an upstream repository.
- Never use private/eBay code, credentials, private data, or proprietary source.
- Before the first patch is saved and hashed, do not inspect the evaluator-only
  fixed commit, its diff, or a downstream patch derived from it.
- Stop after 30 minutes or three materially different repair attempts.
- Preserve only sanitized summaries and hashes; do not commit raw prompts,
  JSONL, stderr logs, complete patches, or local workspace paths.
- A task is complete only when the buggy revision fails as expected, the
  candidate patch passes focused verification, regression verification is run,
  and an AEG experience candidate is recorded.
- Do not append to `experiences/verified.json` until promotion validation passes.

## Status vocabulary

`queued -> reproducing -> diagnosing -> patching -> validating -> recording -> complete`

Terminal alternatives: `blocked` or `rejected`.

Update both the summary table and the task's `STATUS.md` after every phase.

## Progress

| ID | Category | Project | Bug | Status | Owner | Attempts | Experience |
|---|---|---|---:|---|---|---:|---|
| TR-01 | Test Repair | Black | BugsInPy 2 | queued | Codex | 0 | — |
| TR-02 | Test Repair | HTTPie | BugsInPy 1 | queued | Codex | 0 | — |
| TR-03 | Test Repair | Scrapy | BugsInPy 1 | queued | Codex | 0 | — |
| TR-04 | Test Repair | Tornado | BugsInPy 1 | queued | Codex | 0 | — |
| CI-01 | Build/CI Recovery | Black | BugsInPy 1 | queued | Codex | 0 | — |
| CI-02 | Build/CI Recovery | Keras | BugsInPy 2 | queued | Codex | 0 | — |
| CI-03 | Build/CI Recovery | Ansible | BugsInPy 5 | queued | Codex | 0 | — |
| AM-01 | API/Dependency Migration | Sanic | BugsInPy 2 | queued | Codex | 0 | — |
| AM-02 | API/Dependency Migration | Keras | BugsInPy 4 | queued | Codex | 0 | — |
| AM-03 | API/Dependency Migration | Ansible | BugsInPy 6 | queued | Codex | 0 | — |

## Test Repair

### TR-01 — Black decorator boundary around `# fmt: on`

- Intent: repair formatting-state restoration when decorators cross a
  `# fmt: on` boundary.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/black/bugs/2/bug.info)
- Upstream: [psf/black](https://github.com/psf/black)
- License: [MIT](https://github.com/psf/black/blob/main/LICENSE)
- Python: 3.8.3
- Buggy commit: `c8ca6b2b9ff3510bee12129824cebfc2fc51e5b2`
- Focused test: `tests/test_black.py`
- Expected signature: a formatter regression involving decorators and
  `# fmt: on`.
- Evaluator-only fixed commit: `892eddacd215d685e136686b7f629ade70adca83`
- Why reusable: state-machine recovery at directive boundaries applies to
  formatters, linters, preprocessors, and snapshot normalization.

### TR-02 — HTTPie filesystem filename-length boundary

- Intent: prevent downloads from failing with `OSError: [Errno 36] File name too long`.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/httpie/bugs/1/bug.info)
- Upstream: [httpie/cli](https://github.com/httpie/cli)
- Issue: [HTTPie #451](https://github.com/httpie/cli/issues/451)
- License: [BSD-3-Clause](https://github.com/httpie/cli/blob/master/LICENSE)
- Python: 3.7.3
- Buggy commit: `001bda19450ad85c91345eea3cfa3991e1d492ba`
- Focused test: `tests/test_downloads.py`
- Expected signature: a generated download filename exceeds the filesystem's
  per-component limit, including uniqueness suffix handling.
- Evaluator-only fixed commit: `5300b0b490b8db48fac30b5e32164be93dc574b7`
- Why reusable: environment limits must be detected and applied before adding
  suffixes or extensions.

### TR-03 — Scrapy nullable `allowed_domains`

- Intent: make offsite middleware ignore null or invalid domain entries without
  raising during regex construction.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/scrapy/bugs/1/bug.info)
- Upstream: [scrapy/scrapy](https://github.com/scrapy/scrapy)
- License: [BSD-3-Clause](https://github.com/scrapy/scrapy/blob/master/LICENSE)
- Python: 3.8.3
- Buggy commit: `c57512fa669e6f6b1b766a7639206a380f0d10ce`
- Focused test: `tests/test_spidermiddleware_offsite.py`
- Expected signature: `None` reaches URL/regex matching before invalid entries
  are filtered.
- Evaluator-only fixed commit: `9d9dea0d69709ef0f7aef67ddba1bd7bda25d273`
- Why reusable: validate and normalize heterogeneous configuration lists before
  applying type-specific operations.

### TR-04 — Tornado WebSocket `set_nodelay`

- Intent: restore a previously untested WebSocket TCP_NODELAY behavior.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/tornado/bugs/1/bug.info)
- Upstream: [tornadoweb/tornado](https://github.com/tornadoweb/tornado)
- Issue: [Tornado #2611](https://github.com/tornadoweb/tornado/issues/2611)
- License: [Apache-2.0](https://github.com/tornadoweb/tornado/blob/master/LICENSE)
- Python: 3.7.0
- Buggy commit: `6a5a0bfa370b6c0d3dbbf9589a560a98202d2baa`
- Focused test: `tornado/test/websocket_test.py`
- Expected signature: a public WebSocket method no longer delegates to the
  underlying stream/socket implementation.
- Evaluator-only fixed commit: `4677c54cc18bbfbdf0f4dadf11610fab6203fd63`
- Why reusable: thin proxy APIs need contract tests that verify delegation, not
  merely method existence.

## Build and CI Recovery

### CI-01 — Black fallback when multiprocessing is unavailable

- Intent: allow formatting to complete in AWS Lambda-like environments without
  `/dev/shm` or usable multiprocessing primitives.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/black/bugs/1/bug.info)
- Upstream: [psf/black](https://github.com/psf/black)
- PR: [Black #1141](https://github.com/psf/black/pull/1141)
- License: [MIT](https://github.com/psf/black/blob/main/LICENSE)
- Python: 3.8.3
- Buggy commit: `26c9465a22c732ab1e17b0dec578fa3432e9b558`
- Focused test: `tests/test_black.py`
- Expected signature: `ProcessPoolExecutor` initialization raises `OSError`
  and aborts the build/format job.
- Evaluator-only fixed commit: `c0a7582e3d4cc8bec3b7f5a6c52b36880dcb57d7`
- Why reusable: optional parallelism should degrade to a serial executor when a
  constrained CI/serverless runtime lacks OS facilities.

### CI-02 — Keras backend-specific test failure under CNTK

- Intent: make `in_top_k` test behavior correctly account for the CNTK backend
  rather than treating all backends as identical.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/keras/bugs/2/bug.info)
- Upstream: [keras-team/keras](https://github.com/keras-team/keras)
- PR: [Keras #12336](https://github.com/keras-team/keras/pull/12336)
- License: [Apache-2.0](https://github.com/keras-team/keras/blob/master/LICENSE)
- Python: 3.7.3
- Buggy commit: `2f55055a9f053b35fa721d3eb75dd07ea5a5f1e3`
- Focused test: `tests/keras/backend/backend_test.py`
- Expected signature: CI passes on some numerical backends but fails or asserts
  an unsupported contract on CNTK.
- Evaluator-only fixed commit: `c24d16af155e20976bdf61e468ba760408e676ff`
- Why reusable: matrix CI must encode supported capability differences instead
  of assuming implementation parity.

### CI-03 — Ansible false-positive `pytest.raises` assertion

- Intent: repair a test whose assertion is placed inside a `pytest.raises`
  context and therefore never meaningfully validates the captured exception.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/ansible/bugs/5/bug.info)
- Upstream: [ansible/ansible](https://github.com/ansible/ansible)
- PR: [Ansible #67771](https://github.com/ansible/ansible/pull/67771)
- License: [GPL-3.0](https://github.com/ansible/ansible/blob/devel/COPYING)
- Python: 3.6.9
- Buggy commit: `2af76f16be8cf2239daaec4c2f31c3dcb4e3469e`
- Focused test:
  `test/units/module_utils/common/validation/test_check_required_arguments.py`
- Expected signature: a CI test appears to check exception content but code
  after the raising call inside the context is unreachable.
- Evaluator-only fixed commit: `3c3ffc09c203d1b2262f6a319cceadd727749761`
- Why reusable: a green test can be invalid evidence; assertion reachability is
  part of CI correctness.

## API and Dependency Migration

### AM-01 — Sanic `AsyncioServer` parity with Python 3.7

- Intent: expose `start_serving` and `serve_forever` through Sanic's server
  proxy to match the Python 3.7 asyncio server contract.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/sanic/bugs/2/bug.info)
- Upstream: [sanic-org/sanic](https://github.com/sanic-org/sanic)
- Issue: [Sanic #1754](https://github.com/sanic-org/sanic/issues/1754)
- PR: [Sanic #1762](https://github.com/sanic-org/sanic/pull/1762)
- License: [MIT](https://github.com/sanic-org/sanic/blob/main/LICENSE)
- Python: 3.8.3
- Buggy commit: `ba9b432993019b0af0c4827a5ed42aaa091bd17d`
- Focused test: `tests/test_app.py`
- Expected signature: methods documented on the underlying Python 3.7 asyncio
  server are missing from the framework proxy.
- Evaluator-only fixed commit: `801595e24acdf8050b8d3ffa512d424147848d32`
- Why reusable: wrapper objects must deliberately track additions to upstream
  public APIs.

### AM-02 — Keras `TFOptimizer` named-argument contract

- Intent: forward a TensorFlow optimizer's variable list using the correct named
  `var_list` argument.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/keras/bugs/4/bug.info)
- Upstream: [keras-team/keras](https://github.com/keras-team/keras)
- PR: [Keras #12106](https://github.com/keras-team/keras/pull/12106)
- License: [Apache-2.0](https://github.com/keras-team/keras/blob/master/LICENSE)
- Python: 3.7.3
- Buggy commit: `b0bfd5201da2bfced84028bcc5bda05bdfd75af7`
- Focused test: `tests/keras/optimizers_test.py`
- Expected signature: an adapter calls a dependency API positionally or with an
  incorrect contract, producing incorrect gradient-variable selection.
- Evaluator-only fixed commit: `4185cbb50bfcae9cc30b0fc7b67e81d67a50a8ac`
- Why reusable: dependency adapters should use explicit named arguments and
  contract tests at the integration boundary.

### AM-03 — Ansible dependency resolver accepts non-string versions

- Intent: make collection dependency resolution normalize or reject integer and
  floating-point version values instead of assuming a string API contract.
- Source: [BugsInPy metadata](https://github.com/soarsmu/BugsInPy/blob/master/projects/ansible/bugs/6/bug.info)
- Upstream: [ansible/ansible](https://github.com/ansible/ansible)
- PR: [Ansible #67405](https://github.com/ansible/ansible/pull/67405)
- License: [GPL-3.0](https://github.com/ansible/ansible/blob/devel/COPYING)
- Python: 3.6.9
- Buggy commit: `90898132e456ee1993db99a1531379f1b98ee915`
- Focused test: `test/units/galaxy/test_collection_install.py`
- Expected signature: dependency metadata supplies a numeric version and the
  resolver passes it into string/semantic-version operations.
- Evaluator-only fixed commit: `4881af2e7e0506ada0225fd764e874e20569d5b2`
- Why reusable: configuration formats often deserialize version-like values as
  numbers; normalize types at the boundary before semantic comparison.

## Per-task outputs

For task `<ID>`, create:

- `experiences/work-queue/runs/<ID>/STATUS.md` from `TASK-TEMPLATE.md`;
- `experiences/work-queue/runs/<ID>/result.json` with sanitized metrics and
  hashes;
- `experiences/candidates/<ID>.json` following the verified-experience schema.

After objective validation and provenance review, promote the candidate by
appending it to `experiences/verified.json`. Promotion is a separate step from
repair completion.

## Recommended execution order

1. TR-03 — compact null-boundary diagnosis.
2. CI-01 — reusable constrained-runtime recovery.
3. AM-01 — upstream wrapper API parity.
4. TR-04 — delegation contract repair.
5. AM-02 — dependency adapter contract.
6. TR-01 — parser/formatter state boundary.
7. CI-03 — invalid test-evidence detection.
8. AM-03 — configuration type normalization.
9. TR-02 — filesystem boundary behavior.
10. CI-02 — backend-matrix task; likely the most environment-sensitive.

The order intentionally alternates categories so experience from an earlier task
can be retrieved and evaluated on a later related task.
