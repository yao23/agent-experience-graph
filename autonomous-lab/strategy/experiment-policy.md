# Experiment policy

An experiment advances only when its current milestone has complete evidence
and the next transition is allowed by the state machine. Goals, hypotheses,
oracles, minimum comparison sizes, metrics, budgets, stop conditions, allowed
actions, forbidden actions, and approval gates are frozen by the end of
`preregistered`.

Fresh public tasks require deterministic searches for issue timelines,
development links, upstream and fork pull requests in every state, backlinks,
linked commits, issue-number references, defect wording, public tests or
patches, contributor branches, and recent default-branch changes. Queries,
URLs, timestamps, and results are evidence.

The lab stops or escalates on missing evidence, budget exhaustion, repeated
failure, contamination, privacy or license uncertainty, unavailable objective
oracles, or an approval-gated action. It never interprets correct retrieval
abstention as affirmative repair benefit.

The execution rule is: autonomously iterate within the defined safety and
budget boundaries until measurable acceptance thresholds are reached.
Otherwise stop with an evidence-backed failure report and recommended next
action. “Continue until successful” is never a permitted goal.
