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
- Policy unchanged: authorization, budget, qualification, oracle, and fixed
  expiry values were not modified.
- Verification: dedicated tests cover same-error streak reset and quarantine,
  channel-local auth pause, continued work on an unrelated active channel, and
  normal schema validation. Full validation results are recorded in the Draft
  PR after execution.
