# Task Packet: ML-REACT19-001
Packet revision: 2 (static proposal, 2026-10-02).
Status: NEEDS_EVIDENCE. NOT ADMITTED. All commands and tests below are proposed and NOT_RUN. This file alone never authorizes execution.

## Goal and scope
Migrate the library at https://github.com/microsoft/applicationinsights-react-js/tree/9869676e82113c336342abbc7adb424acede2940 from its React 18 development/runtime baseline to React 19.0.0, preserving its public React integration and telemetry behavior.
Source revision: 9869676e82113c336342abbc7adb424acede2940.
Scope: library only: applicationinsights-react-js/, necessary shared Rush dependency lock/configuration, and focused tests/consumer fixture. Shared build tools may receive only changes demonstrably needed for this library.
The sample application is excluded. Do not use its tests as an acceptance oracle. No unrelated refactor, SDK upgrade, publication, or deployment.
The delivered package must retain the existing named exports, prop pass-through, context, event, engagement-metric, error-boundary, and page-view functionality. Preserve package entry points and declaration generation.

## Exact proposed target constraints
All listed direct development dependencies use exact versions, without ^ or ~:
- react: 19.0.0
- react-dom: 19.0.0
- @types/react: 19.0.0
- @types/react-dom: 19.0.0
- @testing-library/react: 16.1.0
- @testing-library/dom: 10.4.0
- typescript: 5.1.6
- jest: 29.7.0
- jest-environment-jsdom: 29.7.0
- ts-jest: 29.2.5
- @types/jest: 29.5.12
- @types/node: 20.16.1

Retain source-lock resolutions for unrelated direct dependencies, including @testing-library/jest-dom 5.17.0, @testing-library/user-event 12.8.3, rollup 2.79.2 and @microsoft/api-extractor 7.52.1. Do not upgrade the Application Insights SDK as a shortcut.
Proposed published React peer constraint: >=19.0.0 <20.0.0. React 18 compatibility is outside this single-target case; no untested backward-compatibility claim. Keep existing history and tslib peer contracts.
Do not add React or React DOM as bundled/private runtime copies. Consumers supply React. The target graph must resolve the fixture and library to the same React 19.0.0 instance and React type major 19. @types/react-dom's wildcard must not float to another major. Freeze all target transitive versions/integrities before admission; this list is not a resolved lockfile.
A changed constraint or extra tooling upgrade requires a packet revision and renewed preflight before a solver starts.

## Proposed environment (not yet frozen)
- Node 20.18.0; npm 9.9.3; Rush 5.148.0.
- Linux x86_64, Ubuntu 22.04.5 userspace proposed; immutable image digest UNKNOWN.
- Disposable isolated workspace, dedicated HOME/cache, no user credentials, no unrelated mounts, no production endpoint access.
- CI=true, TZ=UTC, fixed locale; no telemetry network traffic. Collect telemetry in spies/local fakes.
These are controlled historical experiment pins, not current production deployment recommendations.
Admission must supply immutable image/runtime identities, source and target lock digests, approved lifecycle-script policy, local package-tool paths, and a hash-addressed evaluator fixture. None is certified by this proposal.

## Input, dependency, and command contract
Source input is exactly the pinned repository and its common/config/rush/npm-shrinkwrap.json (Git blob db1beed647743fda6bad44d5e2487c51d72b0ee3). The root yarn.lock is present but is not the chosen package manager.
No root npm install/postinstall, global tool install, floating npx, --force or --legacy-peer-deps. Preflight must establish a project-local Rush bootstrap and replay route. Baseline and target graphs are separate immutable snapshots; permitted migration lock changes must be reviewed against the target constraints and replayed without further resolution.
Any one-time dependency resolution belongs to separately admitted preparation, is logged and frozen before the arm, and does not include source-code fixes. Do not mistake it for a replay or a passing migration.
Proposed command sequence after isolation and budget admission, with every exit code/log captured:
1. Repository root: node --version; npm --version; git rev-parse HEAD.
2. Repository root: node common/scripts/install-run-rush.js install
3. Repository root: node common/scripts/install-run-rush.js check
4. Repository root: node common/scripts/install-run-rush.js rebuild --to @microsoft/applicationinsights-react-js --verbose
5. applicationinsights-react-js/: node node_modules/typescript/bin/tsc -p tsconfig.json --noEmit
6. applicationinsights-react-js/: npm test -- --runInBand
7. applicationinsights-react-js/: npm pack --ignore-scripts --json --pack-destination <admitted-artifact-directory>
8. Evaluator fixture directory: npm ci --ignore-scripts; npm run typecheck; npm test -- --runInBand.

Step 8 refers to a proposed fixture, not an existing file or executable oracle. Before admission the evaluator must implement, review and hash its scripts/lock/configuration and replace the directory placeholder. Its package dependency must point to the tarball from step 7, with verified SHA-256/SRI. Reject a fixture that resolves the published registry release or aliases imports to src/. Record require.resolve and package version for the library, React, React DOM and React types. Run smoke/behavior checks through the package main, check module output/exports and declarations, and ensure React remains external.
The full production build, including minification and declaration generation, is required. A source-only compilation does not replace it.
Preflight must validate command syntax against pinned Rush, prove all tools are local, classify pre-existing command failures, and finalize commands identically for any compared arms. The proposed commands have not been run.

## Acceptance behavior (test design only; NOT_RUN)
All checks use real React 19 DOM rendering; do not mock React, the library, or its hooks. Mock only telemetry transport and control clocks. Each test must make assertions that fail when the corresponding library behavior is removed.
- Package and public typing: all existing exports resolve from the built package. A typed TSX consumer compiles using the packaged declarations, props with required fields remain enforced (include expected-error negative fixtures), and invalid hook event data is rejected. No blanket any, @ts-ignore or skipLibCheck introduced to evade React compatibility.
- Context: a provider supplies the exact plugin instance to a nested hook consumer; rerendering with a replacement provider updates the consumer.
- Error boundary: a healthy child renders without telemetry. A child render error produces the requested fallback and one exception record for one committed failure, including the original error, error severity and component stack. Assert React's caught-error channel in a controlled way; do not rely on errors being rethrown. Do not suppress unexpected errors/warnings globally.
- Engagement HOC: preserve child props and requested class/component names. At a positive fixed clock origin, mount, interact, advance 1000 ms and unmount: one metric with average 1 second, name 'React Component Engaged Time (seconds)', sampleCount 1 and correct component name. No interaction means no metric. For the idle/resume case: first activity at t=100000 ms, idle threshold reached at t=105000, resume at t=108000, unmount at t=110000; advance the 100 ms clock ticks deterministically and expect 2 seconds of engagement. After unmount no timer-driven work remains.
- Engagement hook: run equivalent active/no-activity and idle/resume assertions, including custom properties and cleanup after unmount. Use a real component that invokes the returned activity handler.
- Event hook: default initial render skips the initial event; updating data produces the correct event name/payload; skipFirstRun=false sends the initial event. Rerenders without dependency changes do not send extra events. Verify event-name/plugin changes and unmount/remount semantics against the declared API.
- React development StrictMode: mount/unmount replay without interaction sends no phantom engagement metric and leaves no live intervals after final unmount. With the event hook's default initial-skip setting, initial replay sends no event; one subsequent data change sends one event. Do not demand that opt-in initial effects run once under StrictMode; test skipFirstRun=false once in ordinary mode and label StrictMode replay separately.
- Page-view regression: preserve initial pathname and navigation payload behavior with fake history/analytics; after plugin teardown and a new navigation, no new page-view record is emitted. Avoid redefining unrelated existing route-debounce semantics.
- Warning/resource checks: fail unexpected legacy-renderer, outdated-transform or unwrapped-act warnings; allow only the deliberately induced boundary error with exact matching. Check timer cleanup and no external network requests.
- Integrity: source and target replay do not silently rewrite their frozen snapshots; every target runtime/type/tool version matches the contract. Full build/test failures cannot be dismissed because the consumer smoke check passed.

## Results and exclusions
Observed failure signature: NOT_OBSERVED. No public failure log is a prerequisite for this migration task.
All baseline, target, fixture, package, type, build and behavior results: NOT_RUN.
Do not report PASS until the actual checks have run. Setup/environment failure is BLOCKED; insufficient evidence is INCONCLUSIVE. If admitted preparation establishes only a trivial version edit with no substantive migration, return the candidate for reassessment rather than manufacture scope.
Stop for unauthorized security/auth/payment work, private dependencies, required global installation, unresolved graph replay, insufficient budget, or contamination.

## Solver boundary and dispatch
Proposed arm: A_BASELINE_NO_EXPERIENCE only. This is not a comparative result.
Use a fresh non-inheriting solver context with only this packet, pinned source, frozen environment/fixture contract, neutral first-party docs and its own run evidence. Do not provide evaluator reports, prior sourcing conversations, solution history, upstream migration PRs, later target revisions, experience payloads or other-arm artifacts. No broad candidate search.
Before dispatch the coordinator must reconcile receipts/local-task admission, confirm isolation and remaining case/day/rolling-week budget, reserve budget, finalize READY through the existing process, and create the required CLAIM. Remaining budget is UNKNOWN; the 90-minute case ceiling is not a balance. One consumer and one task per invocation. This static pass neither claims nor dispatches anything.
The local interface currently requires another trigger. No automatic resumption or polling is promised or enabled.

## Neutral public documentation
- https://react.dev/blog/2024/04/25/react-19-upgrade-guide
- https://react.dev/reference/react-dom/client/createRoot
- https://testing-library.com/docs/react-testing-library/intro/
- https://rushjs.io/pages/commands/rush_install/
Exact package versions were checked against npm registry metadata; full dependency replay remains unverified.
