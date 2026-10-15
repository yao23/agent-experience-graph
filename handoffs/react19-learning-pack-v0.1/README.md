# React 19 learning-pack v0.1 — local handoff for Dot

Review date: 2026-10-14 (America/Los_Angeles). This directory is outside the existing Pages deployment inputs. The current workflow copies the public root assets plus docs/, pitch/ and experiences/; it does not copy handoffs/ or .github/.

## Delivery and repository isolation

- Repository remote checked: https://github.com/yao23/agent-experience-graph.git (fetch and push).
- Starting Migration Lab HEAD: 0297d94c85fbf8e8616f8b73b978400bc6fc27b1. Its untracked contribution-checks/ and coordination/migration-lab-v0-1/evidence/ were preserved. The checkout was not switched, cleaned or edited.
- Fetched origin/main before creation: 999efa64e9ba016efc9d3327df4b70e1fc79b804. The requested branch did not previously exist.
- Isolated branch: codex/react19-learning-pack-v0.1. Worktree: /private/tmp/aeg-react19-learning-pack-v0.1. It was clean at creation. Final local commit identity is in the delivery manifest.
- No applicable ancestor/root AGENTS.md was found. The only repository AGENTS.md is scoped to autonomous-lab/, outside the changed paths; that area was not entered.
- No ML-REACT19-001 claim, experiment receipt dependency, queue/authorization/Registry/model/scheduler change, third-party target execution, A/B/C run or model experiment occurred. No employer code, employer skill, private fix or internal log was used as a content source.
- Work stayed local: no push, PR, merge, deployment, test issue or external message. Local HTTP preview requests are not publication.

## Changed files

- docs/react19-migration-pack/pack.md — complete shared English source: six stable IDs, applicability, instructions, status criteria, primary links, version/date and evidence limits; blank local receipt and one feedback destination.
- docs/react19-migration-pack/index.html — generated, readable static page; reuses unchanged site.css, site.js and favicon.svg; page-scoped styles handle reading layout and code contrast. All check text is generated from Markdown without browser-side fetching.
- .github/ISSUE_TEMPLATE/learning-pack-feedback.yml — separate low-friction public feedback form. Only check ID, actual action/result, and public-information confirmation are required; project, environment, agent/model and sanitized logs are optional.
- scripts/test_site.py — adds the new page to the existing site smoke checks (one path).
- handoffs/react19-learning-pack-v0.1/build_page.py — small stdlib renderer for this document's Markdown subset; regenerate after Markdown edits. It does not install a framework or alter root assets.
- handoffs/react19-learning-pack-v0.1/check_pack.py — exact generated-file parity, six IDs and required content fields, evidence/date labels, copy targets, local paths/fragments and unique feedback destination.
- handoffs/react19-learning-pack-v0.1/browser_check.cjs — local browser checks using existing Playwright and installed Chrome; no downloads or dependency installation.
- handoffs/react19-learning-pack-v0.1/evidence/ — browser result JSON and desktop/narrow screenshots; these describe the content page, not a React migration replay.
- This README — handoff, source map, actual checks, gaps and manual publication draft.

## Public source review

Original synthesis and proposed acceptance procedures are distinguished from official React changes in each check. Sources were read before writing; no third-party repository code was run. Full source links and check-specific version/limitations appear in both public formats.

| Check | Primary sources consulted | Claim boundary |
| --- | --- | --- |
| R19-01 | [React upgrade guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide#installing), [version diagnostic](https://react.dev/errors/527), [duplicate React resolution](https://react.dev/warnings/invalid-hook-call-warning#duplicate-react), [Testing Library v16.3.0 manifest](https://github.com/testing-library/react-testing-library/blob/v16.3.0/package.json) | Documented constraints and one pinned dependency example; no all-library compatibility matrix. |
| R19-02 | [React codemod guidance](https://react.dev/blog/2024/04/25/react-19-upgrade-guide#codemods), [React codemod maintainers](https://github.com/reactjs/react-codemod), [type codemod maintainers](https://github.com/eps1lon/types-react-codemod#available-transforms) | Coverage must be bound to actual tool/transform versions; completion is not acceptance. |
| R19-03 | [React 19 TypeScript changes](https://react.dev/blog/2024/04/25/react-19-upgrade-guide#typescript-changes), [React 19 ref changes](https://react.dev/blog/2024/12/05/react-19#ref-as-a-prop), [type transform limitations](https://github.com/eps1lon/types-react-codemod#no-implicit-ref-callback-return-react-19) | Official type/ref changes versus proposed consumer checks. |
| R19-04 | [React controlled input troubleshooting](https://react.dev/reference/react-dom/components/input#my-input-caret-jumps-to-the-beginning-on-every-keystroke), [W3C UI Events composition model](https://w3c.github.io/uievents/#events-compositionevents) | General editing acceptance; no confirmed general React 19 caret defect. Native IME coverage remains separate. |
| R19-05 | [React 19 ref cleanup](https://react.dev/blog/2024/12/05/react-19#cleanup-functions-for-refs), [Strict Mode diagnostics](https://react.dev/reference/react/StrictMode#fixing-bugs-found-by-re-running-ref-callbacks-in-development), [Effect lifecycle](https://react.dev/reference/react/useEffect#parameters) | Official lifecycle behavior versus proposed resource/interaction invariants. |
| R19-06 | [React test renderer context](https://react.dev/blog/2024/04/25/react-19-upgrade-guide#deprecated-react-test-renderer), [test-utils warning](https://react.dev/warnings/react-dom-test-utils), [Git diff](https://git-scm.com/docs/git-diff), [Git worktree](https://git-scm.com/docs/git-worktree) | Recovery/receipt design is this pack's recommendation, not a React requirement. |

Source check date: 2026-10-14. Blog URLs describe React 19's introduction; live reference docs and maintainer main branches are mutable. The pack deliberately does not choose a current “latest” React patch or extrapolate Testing Library 16.3.0 ranges to other releases. It requires users to bind decisions to their own exact versions.

## Actual local checks

Commands run from the isolated worktree:

```sh
python3 handoffs/react19-learning-pack-v0.1/build_page.py
python3 handoffs/react19-learning-pack-v0.1/check_pack.py
python3 scripts/test_site.py
git diff --check
```

Results: generation/parity/content/assets passed; existing site suite passed all 9 tests including the new page; whitespace check passed. Ruby's installed YAML parser parsed the issue form and verified that exactly the three intended logical fields are required, including the nested checkbox requirement.

The existing Playwright package and installed Chrome were used against localhost. See evidence/browser-report.json for browser version and final results. Verified: HTTP 200; six sections; all six brief copies include the shared rules plus the selected instruction; shared-rule and receipt copy; downloaded Markdown filename and exact bytes; a single intended feedback URL; clipboard-denial manual route and focus; content/download present with JavaScript disabled; no JavaScript errors or external requests. Widths checked: 1440, 390 and 320 pixels, on fresh loads after viewport changes. No horizontal overflow was observed in those final loads.

Screenshot review checked desktop and narrow typography, section reading, and agent instructions. It caught inherited light code text on a light background; page-scoped text colors were fixed and checked again. Screenshots are samples, not a full accessibility audit. The browser script uses reduced motion for deterministic scroll capture. Source/browser checks were repeated only after content-page changes or observed failures.

Local sandbox restrictions initially blocked Git metadata writes and localhost binding. The single safe alternative for these operations was the reviewed local permission path; it succeeded. Playwright's default browser revision was absent, so the existing installed Chrome was used; no browser was downloaded. No further environment repair or new service was introduced.

## Preview and recheck

The working preview URL is http://127.0.0.1:8765/docs/react19-migration-pack/ while a local server is running. To reopen after this session or from the extracted delivery snapshot:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory /private/tmp/aeg-react19-learning-pack-v0.1
```

For an extracted archive, serve its site-snapshot/ directory instead. Open /docs/react19-migration-pack/ on that localhost server. No build is needed for preview. Directly opening the HTML also displays its complete static content; clipboard/download behavior is best reviewed on localhost.

To reproduce browser checks, use the installed Playwright location rather than installing dependencies. This session used:

```sh
PACK_PLAYWRIGHT_MODULE=/Users/yaoli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright node handoffs/react19-learning-pack-v0.1/browser_check.cjs
```

Run it from the full worktree against the local server. The script's Chrome channel requires an existing Chrome installation. PACK_PREVIEW_ORIGIN may override localhost's origin; use only an authorized local preview.

## Known gaps and next decision

- Every public check remains **source-backed guidance; not independently replayed**. No actual React migration behavior, native IME, regression suite or restore procedure was executed for a target app.
- Real usage and participant count: UNKNOWN. A prepared feedback form and local content tests are not evidence that anyone used a check.
- GitHub issue-form rendering and availability: UNKNOWN until the template is on the default branch. The URL's repository/template path is checked, but no issue was submitted. The public page explains this publication dependency.
- Other browser engines, real devices, screen-reader behavior and full keyboard/contrast accessibility coverage: UNKNOWN. Desktop/narrow Chrome screenshots and the explicit copy fallback were checked.
- No AEG causal benefit, PMF, cross-model validation or quantified efficiency claim. The Registry remains untouched.
- Session start: 2026-10-14 23:05 PDT (2026-10-15 06:05 UTC). Final packaging time is in the delivery manifest. Work was bounded by the requested 90 minutes; no paid API, analytics SDK, new framework, database or account system was added. Additional cash spending: $0. Actual tokens and subscription cost: UNKNOWN (not exposed).

All reversible content preparation is local. After review, the maintainer decides whether to push this branch, review/integrate the three public deliverables, and publish. The existing deployment workflow reacts to docs/ changes on main; merging there may deploy the page. Ensure the issue template is on the default branch before sharing the feedback invitation. Then use the short draft below manually. Do not post it automatically.

## Short English publication draft

I put together a React 19 Migration Acceptance Pack: six practical checks for developers and coding agents, with copyable instructions and a Markdown download. Try one on a real migration and tell us which check you used, what happened, and what did not apply. Failures, skipped checks, and read-only feedback are welcome. This is source-backed guidance, not evidence of AEG effectiveness. GitHub feedback requires an account and is public; please leave out private code, personal information, and raw agent transcripts.

Before posting, add the published pack page link. Its page contains the single feedback destination. Keep this draft and handoff outside the site deployment.
