# ML-REACT19-001: minimal fixture preparation handoff

Date: 2026-10-05. Phase: PREPARATION_ONLY. This is an evaluator task, not an A/B/C solver invocation.
Operator request: implement the smallest meaningful behavior fixture, obtain actual positive and negative controls within existing authorization/isolation/budget, or return one concrete environment decision. Do not create schedules or duplicate consumers.

## Inputs
- AEG repository: yao23/agent-experience-graph; branch codex/aeg-migration-lab-v0.1.
- Dedicated local worktree: /Users/yaoli/Documents/New project/agent-experience-graph-migration-lab-v0.1.
- Expected consumer: aeg-migration-lab-v0-1. Actual consumer/thread ID UNKNOWN.
- Read current AUTHORIZATION.json, HANDOFF.md, queue.json under coordination/migration-lab-v0-1/, experiments/migration-lab-v0-1/PROTOCOL.md, and task-packets/ML-REACT19-001-r2.md.
- Target source: microsoft/applicationinsights-react-js at 9869676e82113c336342abbc7adb424acede2940.
- Reuse existing local preparation artifacts if verified. Do not inspect upstream migration solutions, later history, other-arm artifacts, or employer materials.

## First reconcile, then prepare
1. Inspect the supported local Codex task/session inventory and pending creation state. Parent's 2026-10-02 inspection-only create returned TimeoutError without an ID; direct child listing on 2026-10-05 is empty, which is not proof that local/pending tasks do not exist.
2. Reuse the matching sole work session. Record actual ID and active execution state. Do not create a second consumer, scheduler, or controller; unresolved duplicate/admission state blocks execution.
3. Verify dedicated worktree origin, branch, HEAD, git status and unfinished operations. Do not switch or modify the original dirty checkout. Fetch the dedicated branch only; use a safe fast-forward only if the worktree is clean and not ahead/diverged. Stop on uncertainty.
4. Reconcile case/day/rolling-seven-day usage from available actual local receipts. Reserve preparation within the remaining balance. Ceilings remain 90 minutes/case, 120/day and 600/rolling seven days, incremental cash $0. Preparation counts against these same ceilings. UNKNOWN is not unused budget.
5. Verify the existing isolation boundary before any target/dependency lifecycle code runs. An isolated git worktree alone is insufficient. No credentials, personal/employer data or evaluator/other-arm answers may be reachable by target code.
6. Record a preparation-scoped CLAIM/reservation in the existing receipts directory only when prerequisites pass. This does not mark the migration queue READY or enable a formal solver.

## Smallest deliverable
Implement one React context public-behavior check against a locally built package from the pinned source, using its React18 baseline first.
- Positive: a real mounted consumer of the library's public context hook observes the exact plugin object supplied by the public provider; replacing the provider object updates the observed object.
- Negative: create a separate disposable copy of the built package with a narrowly recorded mutation that prevents the public hook from delivering the provider value. Run the identical test and assertion against that copy.
- Restore the original package and rerun the positive check.
Do not mutate the test expectation, use a forced throw, or count import/setup/compilation failure as a successful negative control. The negative run must reach and fail the same behavior assertion.
Use real React rendering. Do not substitute a registry release, alias package imports to source, or mock the public hook. Resolve and record package/React paths and tarball digests. Keep production telemetry offline.
Keep the minimal fixture separate from the proposed full React19 acceptance suite. This calibration does not establish React19 migration correctness, transfer benefit, or PMF.

## Implementation and output paths
Use existing locally permitted paths:
- coordination/migration-lab-v0-1/evidence/ML-REACT19-001/preparation/fixture/ for runnable test, package/config/lock and runner.
- coordination/migration-lab-v0-1/evidence/ML-REACT19-001/preparation/ for public-safe commands, logs, exit codes, environment/tool identities, source/build/fixture hashes and mutation description.
- coordination/migration-lab-v0-1/receipts/ for preparation CLAIM/RESULT.
Keep evaluator mutation and calibration evidence outside any future solver input bundle.
No changes to authorization, trust digest, protocol, main or scheduler state.

## Acceptance and budget stop
A successful preparation result requires three observed runs:
1. Original package: selected behavior assertion PASS, process exit 0.
2. Mutated package: the same assertion FAIL, nonzero exit caused by the intended behavior difference.
3. Restored package: PASS, process exit 0.
Record exact commands, working directories, exit codes, assertion names, stdout/stderr paths, runtime identities, dependency locks, elapsed agent time and budget spent/remaining if observable. All unrun stages stay NOT_RUN; monetary cost stays UNKNOWN unless directly observed.
Use only already-authorized available tools. No global installs, paid APIs, new virtualization/container installation, host-security changes, or executor switch.
Stop at the first actual unmet isolation, budget, admission or dependency prerequisite and report a single concrete decision with exact required action. Do not build a more elaborate controller or broaden sourcing.
If setup cannot fit demonstrably remaining budget, preserve evidence and stop rather than consume the entire ceiling blindly.

## End and formal migration boundary
Commit only public-safe deliverables to the dedicated branch and verify the remote commit/content. Dot reads the RESULT and checks controls.
Keep NEEDS_EVIDENCE and formal solver dispatch false until full environment/oracle/dependency/admission gates are separately satisfied. Preparation context must not become a baseline/treatment solver context.
No automatic continuation, polling, schedule reactivation, or migration success claim follows publication of this handoff.
