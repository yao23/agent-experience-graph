# Approval and stop policy

Human approval is required before paid/model execution, beginning a commercial
experiment, modifying `experiences/verified.json`, promoting a candidate,
publishing a release, opening or merging a pull request, creating or using a
secret, contacting an external person, or writing to an external project.

Autonomous work may validate repository-local records, calculate deterministic
scorecards, generate status reports, and append a single in-policy transition
when all evidence and approvals already exist.

The controller must stop after any terminal state. It must also stop and emit an
escalation when a budget is exhausted, the same failure reaches the configured
retry limit, a required oracle is missing, evidence is contaminated, or the
next action is forbidden or awaits approval. An escalation remains open until a
human records a decision; absence of a decision never implies approval.
