# AEG technical pitch evidence update experience record

Status: completed — ready for human review
Run date: 2026-08-09
Branch: `codex/pitch-evidence-update`

This is a sanitized, repository-local dogfooding receipt. It records the human
strategy guidance, evidence audit, implementation, and validation for a focused
technical-pitch update. It is not a promoted verified experience and does not
modify `experiences/verified.json`.

## Intent

Update the public technical pitch to reflect the latest product and founder
strategy without redesigning the unified website. Make the north-star
hypothesis, operating loop, initial users, bounded evidence, current market
status, next falsifiable milestone, and design-partner experiment clear in a
five-minute read.

Give the long-term thesis “From Superintelligence to Distributed Intelligence”
special emphasis while clearly separating it from present product evidence.

## Context

- The original checkout contained unrelated uncommitted VS Code packaging
  changes. Work therefore continued in the clean linked website worktree from
  current `origin/main`; the original checkout was not cleaned, stashed, or
  modified.
- The unified product, pitch, install, and demo website was already deployed and
  visually approved. This run preserved its navigation, typography, palette,
  spacing system, responsive behavior, and evidence-first voice.
- The public repository contains two verified experience records and a shipped
  VS Code developer preview at v0.1.5.
- The bounded repair-lab result contains five baseline/assisted pairs. All ten
  arms passed; assisted runs used one fewer median completed command and added
  18,235 ms median latency.
- One related transfer pair was neutral and one preregistered failed-path result
  was not positive. Neither supports a generalized retrieval claim.
- The autonomous loop demonstrated deterministic state transitions,
  hash-chained evidence, and a stop at an approval gate. That is workflow
  validation only.
- Stage A recruitment authorization is effective on main. The public Stage A
  budget currently records zero initial invitations and zero enrolled
  participants; participant task execution remains unauthorized.

## Human strategic guidance

The human review asked the pitch to:

1. Lead with the hypothesis that AEG helps agents repeatedly improve through
   verified execution experience.
2. Position AEG as a cross-platform execution-evidence layer: real execution →
   structured evidence → verified reuse → measured outcome.
3. Focus the first wedge on engineers using coding agents, AI dev-tool and OSS
   maintainers, and—later, if transfer holds—enterprise AI-platform teams.
4. Distinguish AEG from observability, documentation, marketplaces,
   orchestrators, LangSmith replacement claims, and reputation or safety
   scoring.
5. Preserve the five-pair evidence boundary, negative and neutral transfer
   results, and the lack of customer-adoption or product-market-fit evidence.
6. Add a visually distinct long-term thesis section about a possible future of
   many human-agent systems learning locally and sharing selectively. “Billions”
   must remain a possible topology, not a present adoption claim or forecast.
7. End with a concrete invitation to bring one licensed, reproducible failure
   with an objective success check for a bounded baseline-versus-experience
   experiment.

## Baseline

- The pitch used the shared website design and passed responsive overflow checks
  at 375px, 768px, and 1280px.
- The opening described an evidence layer but did not lead with the new
  north-star hypothesis or the full execution-to-outcome loop.
- Product boundary, evidence, limitations, and next validation were present but
  the initial users, experience-record unit, current Stage A status, and
  design-partner exchange were not explicit.
- The long-term distributed-intelligence thesis was absent.

## Steps

1. Read repository instructions, product strategy, experiment policy,
   approval/stop policy, registry, ledger, current status, Phase 0 scorecard and
   decision, Stage A approval and budgets, repair results, verified library, and
   the current pitch.
2. Capture the deployed pitch at 375px, 768px, and 1280px and verify the absence
   of page-level horizontal overflow.
3. Create `codex/pitch-evidence-update` from current `origin/main` in the clean
   linked worktree.
4. Reorder and rewrite the pitch around the repeated-learning problem, operating
   loop, experience record, first wedge, long-term thesis, bounded evidence,
   limitations, market status, falsifiable milestone, design-partner experiment,
   and technical architecture.
5. Add style-compatible record and intelligence-layer components to the shared
   stylesheet. Keep Models → Context → AEG in semantic order and stack that
   sequence at narrower widths.
6. Add automated assertions for the required thesis phrases, evidence metrics,
   Stage A counts, CTA destination, section order, and unsupported-claim guard.
7. Review rendered screenshots, mobile navigation, fragment positioning,
   console output, and overflow at all three required widths.
8. Run existing repository validations and inspect the final diff for scope,
   claims, private paths, secrets, and unrelated changes.

## Artifacts

- `pitch/index.html`
- `site.css`
- `scripts/test_site.py`
- this experience record

No homepage, install, demo, product runtime, verified library, experiment
evidence, authorization, or operational record was changed.

## Failures

- The first Batch 01 evidence-validation run could not resolve the pinned AJV
  CLI package while network access was restricted.
- The in-app browser does not support a `networkidle` wait state.
- A very tall full-page browser capture rendered poorly in the review surface,
  so viewport-level section captures were used for detailed visual inspection.

## Recovery

- Re-ran the unchanged evidence validator with approved dependency access and a
  task-specific npm cache; all seven candidate schemas and the batch evidence
  checks passed.
- Used the supported page-load state and direct rendered-state checks.
- Captured the hero and long-term thesis at the exact viewport widths and paired
  screenshots with measured viewport, overflow, heading, section-order, and
  fragment-offset data.

## Outcome

Success within the requested local scope.

- The hero now states “Verified experience for the next agent run” and labels
  the north-star statement as a hypothesis that is not yet proven.
- The narrative follows real execution → structured evidence → verified reuse →
  measured outcome.
- The experience record preserves attempts, failures, recovery, verified
  outcome, cost/latency, provenance, and applicability.
- The initial wedge and user sequence are explicit without claiming adoption.
- “From Superintelligence to Distributed Intelligence” is a distinct, responsive
  section with Models, Context, and AEG layers. It labels its boundary “THESIS,
  NOT YET PRODUCT EVIDENCE.”
- The evidence section reports five pairs, ten passing arms, one fewer median
  completed command, and +18.2 seconds median assisted latency. It keeps the
  neutral and not-positive transfer results visible.
- The market-status section says recruitment is authorized while public budget
  records remain at zero invitations and zero enrolled participants.
- The design-partner CTA uses the reviewed email destination and subject “AEG
  Design Partner Experiment.”
- Page-level `scrollWidth` equals viewport width at 375px, 768px, and 1280px.
  The thesis layer order is Models → Context → AEG at every width.
- The 69px sticky header does not obscure fragment headings: target sections
  settle at 84px. Mobile navigation opens with matching `aria-expanded` and
  `data-open` state. Browser console warnings/errors: zero.

## Validation

- Repository script suite: 18 tests passed, including 7 site tests.
- Autonomous-lab regression suite: 64 tests passed.
- Autonomous-lab schema, ledger, state, status, next-action, report, Phase 1
  protocol, and Python compilation checks passed.
- Verified library: 2 records passed semantic validation.
- Public repair lab: 20 unit tests passed; the five-pair, neutral transfer, and
  preregistered failed-path result datasets all passed recomputation.
- Natural-transfer benchmark: manifest validation and self-test passed; 7 runner
  tests and 2 isolation-controller tests passed.
- Batch 01: 7 candidates and 34 evidence files passed validation.
- Batch 02: 24 screened, 0 qualified, and 18 evidence files passed validation; 2
  selection-gate tests passed.
- VS Code extension: 20 tests passed; TypeScript compilation and v0.1.5 VSIX
  packaging passed.
- Pitch HTML and shared CSS passed Prettier checks; `git diff --check` passed.

## Reusable experience

1. Treat the pitch as a claim graph: every present-tense product statement should
   map to shipped evidence, while hypotheses and long-term topology need visible
   boundary labels.
2. Public operational counts should be attributed to the public repository
   record, especially when private operational files are intentionally ignored.
3. A future-scale idea can be memorable without becoming a forecast by using
   conditional language and pairing it with an explicit evidence boundary.
4. Preserve negative and neutral transfer results next to the positive bounded
   metric; separation makes the technical thesis more credible.
5. Assert required language and prohibited overclaims in site tests so later copy
   edits cannot silently broaden the evidence boundary.

## What this run validates—and does not validate

This run validates that the revised pitch is internally consistent with the
current public repository evidence, uses the approved unified design, resolves
its internal links and CTA, and renders without page-level horizontal overflow
at the required widths.

It does **not** validate the north-star hypothesis, scientific claims about
distributed intelligence, reliable cross-project transfer, improvement on fresh
developer tasks, customer adoption, willingness to pay, commercial demand, or
product-market fit. There was no baseline-versus-treatment comparison for this
writing task, so it also does not show that AEG retrieval made the update faster,
cheaper, more correct, or more successful.

## Cost and external actions

- Paid cost: unavailable; do not infer.
- Model or token cost: unavailable; do not infer.
- Elapsed wall time: not independently metered; do not infer from command or
  conversation timestamps.
- External writes, outreach messages, participant actions, deployments,
  publications, pushes, pull requests, releases, and verified-library changes:
  zero.
