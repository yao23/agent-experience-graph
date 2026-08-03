# Codex execution prompt

Copy the prompt below into a Codex environment configured for this repository.

---

Continue work in:

- Repository: https://github.com/yao23/agent-experience-graph
- Branch: `codex/v0.1.3-verified-repair-lab`
- Draft PR: https://github.com/yao23/agent-experience-graph/pull/6
- Queue: `experiences/work-queue/README.md`
- Status template: `experiences/work-queue/TASK-TEMPLATE.md`

Work autonomously through the public experience queue, one task at a time.
Continue pushing checkpoints to the existing branch. Do not create another PR,
merge PR #6, or mark it ready.

For each task:

1. Change its queue status to `reproducing`.
2. Create `experiences/work-queue/runs/<TASK-ID>/STATUS.md` from the template.
3. Checkout the exact buggy revision in an isolated temporary worktree or
   container.
4. Confirm the repository license and public provenance.
5. Reproduce the focused failure. If historical dependencies cannot install,
   use the benchmark-provided environment or create a dependency-free fixture
   preserving the same mechanism and label it as adapted.
6. Write root-cause hypotheses before editing.
7. Retrieve relevant AEG experience, but treat it only as guidance.
8. Attempt a minimal repair without viewing the evaluator-only fixed commit.
9. Save and hash the first candidate patch before inspecting any golden fix.
10. Run the focused test, related tests and full suite when feasible.
11. Record attempts, commands, test executions, duration, tokens when available,
    failures, recovery and limitations.
12. Write a sanitized candidate experience to
    `experiences/candidates/<TASK-ID>.json`.
13. Validate its schema, semantics and intended retrieval query.
14. Only after the candidate patch hash is recorded, compare it with the human
    fixed commit and record whether it is semantically or textually equivalent.
15. Update `STATUS.md` and the queue table. Commit a checkpoint after every
    completed task.

Boundaries:

- Maximum 30 minutes and three materially different attempts per task.
- Never access private or eBay repositories.
- Never push, comment or open a PR upstream.
- Never expose credentials, raw prompts, JSONL, stderr logs, full patches,
  private data or local absolute paths.
- Never copy the golden patch.
- Do not weaken or edit the regression test merely to make it pass.
- Do not fabricate unavailable metadata.
- A blocked or failed task is still a valuable experience; record the failure
  and recovery evidence.
- Stop the current task if it requires credentials, broader permissions,
  unlicensed source, unsafe third-party execution or more than the stated
  resource budget. Continue to the next safe task.

Execution order:

`TR-03, CI-01, AM-01, TR-04, AM-02, TR-01, CI-03, AM-03, TR-02, CI-02`

Start with only the first three tasks in this run. Stop after three tasks or
three hours, whichever comes first. This bounded batch prevents an unreviewable
overnight agent loop.

Before finishing the batch:

- run all AEG queue/schema/semantic tests;
- run retrieval smoke tests for every new candidate;
- scan committed files for secrets, raw logs, prompts, patches and local paths;
- update the PR description with a table of completed, failed and blocked tasks;
- report commit SHAs, outcomes, costs, retrieved experience, remaining
  limitations and the next queued task.

Do not claim AEG improvement merely because a repair succeeds. When possible,
compare isolated baseline and AEG-assisted attempts. Otherwise label the record
as experience collection rather than causal A/B evidence.
