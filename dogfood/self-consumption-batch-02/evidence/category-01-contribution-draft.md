# Category 01 local contribution draft

Prepared locally only. Nothing was pushed or posted to Click.

## Proposed title

Flush batched progress updates before rendering completion

## Proposed description

When `update_min_steps` does not evenly divide the number of items, Click keeps the final sub-threshold updates in its interval accumulator. The progress bar is marked finished and rendered as full, but `show_pos=True` still reports the last committed position (for example, 14/20 with 20 items and a threshold of 7).

This patch commits any residual interval count when the progress bar finishes, without changing the batching threshold used during iteration. The regression forces the TTY path, iterates 20 items with `update_min_steps=7`, and asserts both a final position of 20 and an empty residual accumulator.

Closes #3571.

## Local verification

- Frozen black-box oracle: failed before, passed after.
- Focused `update_min_steps` tests: 2 passed.
- Complete `tests/test_termui.py`: 222 passed, 23 skipped.
- Full Click suite: 1940 passed, 25 skipped, 31000 deselected, 1 expected failure.
- Ruff lint and format checks: passed.

Patch SHA-256: `a52c73c2a4591b635f7d67577678224b971a1661e4bd6c98a32e37cee815ec84`.

The local reconstructed commit is `506c3d88f9e6553c8b3e1bb9231b6d55dd5e85ef`; it is not an upstream Click commit and has not been pushed.

## Post-Batch-02 superseding correction

Do not submit this draft. Public fork and upstream PRs containing the same root cause, repair direction, and tests predated Batch 02. This text is retained only as historical evidence of the independently produced local proposal; it is not an actionable external contribution.
