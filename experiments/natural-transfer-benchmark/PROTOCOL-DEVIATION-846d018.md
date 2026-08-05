# Pre-execution isolation deviation from 846d018

No benchmark arm had executed when the local isolation preflight demonstrated
that a `workspace-write` Codex session could read a sentinel in a sibling arm
directory. Commit `846d018` therefore remains the frozen experimental design,
but its sibling-worktree execution mechanism is superseded before execution.

The replacement uses one fresh GitHub-hosted `macos-14` arm64 VM per arm. A
controller job packages a single sanitized arm envelope. The arm VM receives
only that envelope; the agent process is launched with a scrubbed environment
that contains no GitHub or Actions artifact credential. Other arm workspaces,
logs, patches, caches, the full manifest, and hidden evaluator data are not
present. Artifacts are uploaded only after the isolated process terminates, and
hidden human-patch evaluation is reserved for a separate evaluator job.

The manifest and environment lock remain byte-for-byte identical to `846d018`.
Their SHA-256 values are enforced by the isolation controller. This deviation
does not change task pairs, source experiences, prompts, treatment payloads,
thresholds, randomized order, evaluation criteria, budgets, or dependencies.

The 30-arm execution remains prohibited until the adversarial isolation jobs
pass on the actual `macos-14` execution substrate and a job-scoped model
credential is configured. Absence of that credential is an execution blocker,
not a reason to weaken isolation or alter the frozen protocol.
