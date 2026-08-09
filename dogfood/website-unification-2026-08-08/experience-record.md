# AEG website unification experience record

Status: completed — ready for human review
Run date: 2026-08-08
Branch: `codex/aeg-tuesday-meeting-site`

This is a sanitized, repository-local dogfood receipt. It follows the AEG
Playwright receipt vocabulary while adding claim boundaries and reproducible
validation for this website run. It is not a promoted verified experience and
does not modify `experiences/verified.json`.

## Intent

Prepare the homepage, pitch, VS Code installation guide, and 60-second demo for
a short technical founding-team conversation. Make the work itself auditable as
an AEG dogfooding run.

## Context

- The original checkout was 85 commits behind `origin/main` and contained
  unrelated uncommitted VS Code packaging changes.
- Work therefore runs in a linked worktree from current `origin/main`; the
  original working tree remains untouched.
- The homepage existed only on `gh-pages`; the other three routes were canonical
  on `main`.
- Current public evidence supports shipped infrastructure and bounded verified
  artifacts. It does not support generalized retrieval benefit, cross-project
  transfer, customer adoption, or product-market fit.

## Baseline

- Homepage: external `styles.css` and navigation focused on page sections.
- Pitch: 307-line standalone document with inline CSS, hidden mobile nav, and
  broader business/traction claims than the latest evidence supports.
- Install guide: 560-line standalone document with inline CSS and 618px page
  width at a 375px viewport.
- Demo: 221-line standalone document with inline CSS and no site navigation.
- Existing checks: 11 script tests and 42 autonomous-lab tests passed. The two
  broad discovery commands for `experiments/` and `dogfood/` found no tests
  because those trees are not Python packages; focused commands are recorded in
  the final validation section.

## Steps

1. Read repository instructions, product strategy, experiment policy,
   approval/stop policy, registry, ledger/status, verified library, experiment
   results, and recent commits.
2. Capture structural and responsive baseline for all four published routes.
3. Move the homepage source to `main` and create one shared design system.
4. Rewrite the four pages around problem, value, loop, evidence, next
   experiment, and explicit calls to action.
5. Validate repository checks, links, routes, browser console, keyboard/mobile
   navigation, 375px and desktop layouts, and public claim boundaries.
6. Review and commit locally. Do not push, publish, deploy, or open a PR.

## Skills

- repository inspection and evidence review
- semantic HTML and responsive CSS
- browser-based visual and interaction testing
- AEG receipt capture and claim-boundary review

## Artifacts

- `index.html`
- `pitch/index.html`
- `docs/install-vscode-extension.html`
- `docs/60-second-demo.html`
- `site.css`
- `site.js`
- `favicon.svg`
- this record

## Failures

- Initial `git fetch` failed because sandboxed DNS access was unavailable.
- Initial local HTTP server bind failed under sandbox restrictions.
- Browser `networkidle` waiting is unsupported by the in-app browser interface.
- Baseline install page overflowed horizontally at 375px (`scrollWidth: 618`).

## Recovery

- Re-ran the authorized fetch with network approval and based the branch on
  current `origin/main`.
- Started a local-only server with the approved command boundary.
- Used `domcontentloaded`, then inspected rendered DOM and screenshots.
- Replaced page-local layout rules with a shared responsive system using
  shrink-safe grid columns, wrapping code blocks, and a tested mobile nav.

## Outcome

Success within the requested local scope.

- All four routes share `site.css`, `site.js`, primary navigation, footer,
  buttons, cards, status treatments, type, color, and spacing.
- The homepage source now lives on `main`; the Pages workflow copies canonical
  homepage assets and removes the obsolete `styles.css` / `script.js` pair from
  the assembled branch.
- Browser checks at 375×812 and 1280×800 found no horizontal overflow on any
  route. The original 618px mobile install-page width is now 375px.
- Mobile navigation opens with accurate `aria-expanded` state. The demo lookup
  reveals and focuses the evidence result.
- Every route has one `h1`, one `main`, primary navigation, a footer, English
  document language, a skip link, no duplicate IDs, and no unlabeled
  interactive control. The demo textarea has an associated `<label>`.
- Browser console warnings/errors: 0 across all four routes.
- Static internal-link and fragment checks pass. GitHub repository, evidence,
  extension-source, challenge, and Marketplace URLs returned HTTP 200.
- No unsupported public claim or public mention of the meeting counterparty was
  added.

## Commands executed

Read-only discovery and evidence review used `git status`, `git log`, `git
ls-tree`, `git show`, `git diff`, `find`, `rg`, `sed`, and `jq`. Execution and
validation commands were:

```text
git fetch --prune origin
git worktree add -b codex/aeg-tuesday-meeting-site /private/tmp/aeg-tuesday-meeting-site origin/main
git worktree add --detach /private/tmp/aeg-published-baseline origin/gh-pages
python3 -m http.server 4173
python3 -m http.server 4174
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 -m unittest discover -s autonomous-lab/scripts/tests -p 'test_*.py' -v
python3 scripts/test_recommend_traces.py
python3 scripts/test_validate_verified_experiences.py
python3 scripts/test_site.py
python3 scripts/validate_verified_experiences.py
python3 dogfood/self-consumption-batch-01/validate_evidence.py --base-ref origin/main
python3 scripts/validate_verified_experiences.py --library dogfood/self-consumption-batch-02/candidates/category-01-click-progressbar.json
python3 dogfood/self-consumption-batch-02/validate_evidence.py --base-ref origin/main
python3 dogfood/self-consumption-batch-02/test_selection_gate.py
python3 experiments/public-repair-lab/test_run_experiment.py
python3 experiments/public-repair-lab/test_validate_paired_results.py
python3 experiments/public-repair-lab/validate_paired_results.py
python3 experiments/natural-transfer-benchmark/run_benchmark.py validate
python3 experiments/natural-transfer-benchmark/run_benchmark.py self-test
python3 experiments/natural-transfer-benchmark/test_run_benchmark.py
python3 experiments/natural-transfer-benchmark/test_isolation_controller.py
python3 autonomous-lab/scripts/lab.py validate --base-ref origin/main
python3 autonomous-lab/scripts/lab.py status
python3 autonomous-lab/scripts/lab.py next
python3 autonomous-lab/scripts/lab.py report --check
PYTHONPYCACHEPREFIX=/private/tmp/aeg-site-pycache python3 -m compileall -q autonomous-lab/scripts
npm_config_cache=/private/tmp/aeg-site-npm-cache npm ci
npm test
npm run compile
npm run package
git diff --check
curl -L ... (five public links; read-only status validation)
```

Browser validation used the in-app browser against the two local servers for
rendered screenshots, DOM checks, interaction checks, responsive dimensions,
and console logs.

## Checks passed

- Baseline: 11 repository script tests; 42 autonomous-lab regression tests.
- Updated site: 3 focused static site tests.
- Recommender and verified-library unit tests: 11.
- Autonomous-lab regression tests: 42; validation/status/next/report checks
  passed; three scripts plus five test modules compiled.
- Public repair lab: 20 unit tests; paired-results validation passed.
- Natural transfer: manifest validation, self-test, 7 runner tests, and 2
  isolation-controller tests passed.
- Batch evidence: Batch 01 and corrected Batch 02 validators passed; 2 selection
  gate tests passed.
- VS Code extension: 20 tests passed; TypeScript compilation passed; v0.1.5
  packaged as a 45-file, 145.8 KB VSIX.
- Static/browser site checks and external-link checks passed as described above.

## Checks failed and recovered

- Two initial Batch validator invocations used obsolete guessed flags. Both
  rejected the arguments without mutating evidence. Recovery: read the CI
  workflow and reran each with `--base-ref origin/main`; both passed.
- Initial Python compile attempted to write Apple’s default bytecode cache
  outside the sandbox. Recovery: set a task-specific cache under `/private/tmp`;
  compile passed.
- Initial `npm ci` could not write the default log directory; the cache-local
  retry then exposed sandboxed DNS failure. Recovery: used the task-specific
  cache and approved network access; install completed with zero reported
  vulnerabilities.

## Reusable experience

1. When a published homepage exists only on a deployment branch, move its source
   to the canonical branch before consolidating the system; update both path
   triggers and assembly logic.
2. Inspect rendered `scrollWidth` at the exact required viewport. The baseline
   install page looked plausible in source but measured 618px on a 375px screen.
3. Evidence status is a reusable content primitive: `shipped`, `bounded
   verified`, and `hypothesis` make negative and neutral results legible without
   weakening the product thesis.
4. A static HTML link/landmark test complements browser checks cheaply and
   prevents the four entry routes from drifting again.
5. Preserve a dirty checkout by using a linked worktree from the current remote
   base; do not clean, stash, or rewrite unrelated user work.

## What this run proves—and does not prove

This run proves that an AEG-style receipt can preserve the website task’s
intent, context, steps, failures, recovery, artifacts, outcome, and validation
in a reusable repository-local record. It also produced a coherent, tested
local website implementation.

It does **not** prove that AEG retrieval caused the implementation to be faster,
cheaper, more correct, or more successful. There was no randomized baseline,
no treatment/control separation, and no measured retrieval intervention. It
does not establish generalized transfer, production adoption, customer demand,
or product-market fit.

## Cost

- Paid cost: unavailable; do not infer.
- Model/token cost: unavailable; do not infer.
- Elapsed wall time: not independently metered; do not infer from conversation
  or command timestamps.
- External writes: 0.
- Deployments, pushes, pull requests, or external communication: 0.
