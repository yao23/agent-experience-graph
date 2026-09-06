# Control improvement: channel-local failure gates

- Observed problem: the charter required repeated infrastructure failures and
  auth or quota failures to stop only the affected execution channel, but the
  controller enforced this only as prose and model-worker auth or quota failure
  paused the entire pilot.
- Change: every work item now names a machine-readable execution channel.
  Non-active channels are excluded from task claiming. Two consecutive
  identical infrastructure failures quarantine that channel; auth or quota
  failure pauses that channel; an unavailable disposable runtime remains
  `BLOCKED_ENVIRONMENT` without stopping public discovery.
- Intent vocabulary: native automation updates now have their own external
  effect type; an attempted use of the Draft PR type was recorded as
  `NOT_PERFORMED` before any scheduler update occurred.
- Remote-ref freshness: the SHA from the local tracking ref is now provisional.
  Every claimed round must record a public-read intent and freeze the current
  remote branch SHA before stage work; a round cannot finish without that
  observation.
- Weekly and terminal evidence: weekly reports now include target-relative
  progress, qualification rate, outcome counts and highlight, separate founder
  hours and compute dollars, worker starts, quota visibility, bottleneck, next
  focus, and decision queue. The final report exposes every continuation gate
  and returns only `CONTINUE`, `NARROW`, or `STOP`.
- Expiry persistence: an active pilot reconciles an already-pushed checkpoint
  before writing `EXPIRED` and `final.md`. The scheduler is instructed to audit
  and push that terminal checkpoint. An explicit operator pause remains
  network-quiet and requires human resolution if an effect is still pending.
- Budget-safe recovery ordering: active-run daily and total budget gates now
  precede push reconciliation. A budget-blocked invocation leaves the committed
  pending intent untouched instead of creating an uncommitted receipt that
  would make the following scheduled validation dirty. Expiry still reconciles
  first so the terminal checkpoint includes the verified effect.
- Experience and transfer integrity: release-review and held-out-positive counts
  now come only from first-class Experience and transfer-evaluation records.
  Experience artifacts are exact-shape, code-only JSON with pinned SHA-256
  digests. A transfer freezes its decision rule and experimental configuration,
  uses isolated baseline and assisted contexts/workspaces/environments, retains
  ordered command/exit/oracle evidence for every attempt, and requires an
  independent deterministic-oracle executor. A release-ready Experience must
  have a completed transfer that did not participate in construction. Git
  history validation rejects rewrites of committed Experience versions,
  preregistered freezes, and terminal transfer outcomes.
- Candidate, behavior, and adoption integrity: committed candidate
  classifications are immutable exact-shape records. Independently verified
  behavior now requires a first-class baseline-failure/repaired-success record
  with frozen revisions and an independent deterministic-oracle verifier.
  External reuse has a separate evidence ledger; self-reports and founder,
  Foundry-agent, or project-CI activity cannot enter either the verified-user
  gate or the external-success numerator.
- Resource and reporting integrity: scheduled worker starts are charged at
  claim time so crashed rounds cannot disappear from the daily budget. New
  round and worker receipts distinguish configured model, observed model and
  attestation, call method, tokens, retries, quota, actual-cost basis, and
  source-backed market estimates; unknown values remain `UNKNOWN`. Weekly
  reports include release, user, external-reuse, per-qualified-task cost, ratio,
  canary, and model-usage evidence, and are synthesized as bounded controller
  work when no ordinary task is ready.
- Pause durability: the single pause-and-push entry now reconciles an existing
  pushed checkpoint before committing the pause. It still pauses locally first
  when a non-push effect cannot be verified or an active round must reach a safe
  checkpoint, and reports that persistence is deferred instead of claiming a
  remote pause.
- Control-contract immutability: `pilot.json` is now a closed v2 schema. The
  controller fixes the original activation timestamps, all zero-spend and
  separate-authorization boundaries, cadence, concurrency, model policy,
  source identity, six-week targets, and continuation gates as one exact
  contract. Shifting the whole 42-day window, lowering a target, expanding an
  authorization, changing model/schedule/execution policy, or adding an
  unreviewed field all fail before a round can start. Report denominators and
  terminal gates read the same machine values instead of parallel hard-coded
  numbers.
- Disposable-runtime enforcement: state schema v3 adds immutable, exact-shape
  qualification receipts and permanent one-time environment claims. Clone,
  install, and frozen-oracle intents now require an active
  `DISPOSABLE_RUNTIME` task, an unexpired receipt proving no sensitive mounts or
  credentials and separately bounded dependency/test networking, and an
  environment ID not claimed by another round. Maintenance mode cannot create
  these intents, and status reports both receipt and available-runtime counts.
- Stage-evidence enforcement: state schema v4 permits a round to claim multiple
  distinct one-time environments for isolated arms while permanently preventing
  cross-round reuse. Frozen-oracle completion now records immutable revision,
  command, exit, observed result, evidence digest, and summary codes atomically.
  Reproduction, repair, verification, transfer, and release-material success
  each fail closed unless their corresponding current-round first-class evidence
  is present; a generic `PASSED` label cannot complete those stages.
- Policy unchanged: authorization, budget, qualification, oracle, and fixed
  expiry values were not modified.
- Verification: dedicated tests cover same-error streak reset and quarantine,
  channel-local auth pause, continued work on an unrelated active channel,
  count-spoof rejection, immutable artifact digests, exact artifact fields,
  independent-transfer release gating, arm isolation, outcome consistency, and
  fail-closed malformed targets. Full validation results are recorded in the
  Draft PR after execution.
