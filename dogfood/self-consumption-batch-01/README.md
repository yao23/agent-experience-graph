# AEG Self-Consumption Batch 01

This directory is a durable, sequential execution queue for seven bounded AEG dogfood pilots. `execution-state.json` is the machine checkpoint; `execution-results.md` is append-only evidence. Each category freezes a public task, queries `experiences/verified.json`, executes once within its command/time budget, verifies objectively, writes a sanitized candidate record under `candidates/`, and checkpoints before the next category.

Rules: preserve negative evidence; never force retrieval; keep external repositories under `/tmp`; never promote candidates automatically; make no external writes; stop a category at its bound and continue unless a batch-wide safety condition applies.

Resume procedure: read `execution-state.json`, verify the current worktree is clean or contains only the named running category's artifacts, then continue the first project whose status is `running` or `pending`. Corrections to `execution-results.md` are appended, never rewritten.

Post-batch review starts with `evidence-audit.md`. Candidate schema validity is necessary but never sufficient for promotion; retrieval timing, blindness, source freshness, external value, acceptance, and legal/privacy evidence are audited separately.
