# Autonomous Lab Agent Rules

These rules apply throughout `autonomous-lab/`.

1. Validate before proposing a state transition.
2. Never skip lifecycle stages or rewrite an existing ledger event.
3. Never execute a treatment before the goal and oracle are preregistered.
4. Stop when evidence, freshness, contribution availability, budget, privacy,
   legal status, or an approval is unresolved.
5. Treat publishing, candidate promotion, verified-library changes, releases,
   paid execution, secret creation, external communication, and external writes
   as approval-gated actions.
6. One invocation may make at most one state transition.
7. Record every escalation as JSON and surface it in the human report.
8. Never claim generalized effectiveness or product-market fit from local,
   historical, contaminated, non-blind, or non-contributable evidence.
