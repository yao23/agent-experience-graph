# Agent Experience Graph for VS Code

Retrieve verified debugging experience before your coding agent starts from
scratch.

AEG v0.1.5 is a local-first developer preview:

**Task or error → Explainable verified match → Guarded recovery capsule → Local rating**

## What is new in v0.1.5

- Verified-experience retrieval now considers lessons and subtask evidence
  without allowing long records to accumulate an unfair score advantage.
- Match explanations show the query terms that actually overlap, and nonzero
  near-matches are disclosed when AEG abstains below its retrieval threshold.

## Marketplace icon restored in v0.1.4

- Restore the original AEG Marketplace icon and package it explicitly.

## Verified-experience workflow introduced in v0.1.3

- **AEG: Try a Verified Experience** searches the bundled, validated public
  library. Candidate and malformed records are not eligible.
- Each card shows why it matched, the validated outcome, reusable lessons,
  recommended use cases, constraints, limitations, and public provenance.
- **Copy capsule** produces concise context for a coding agent with an explicit
  instruction to inspect the local code and run focused and regression tests.
- Helpful, partially helpful, irrelevant, and harmful ratings stay in
  `.aeg/verified-experience-feedback.json`; task text and ratings are not
  uploaded.
- **AEG: Open Verified Experience Challenge** opens a bundled synthetic
  transfer task so a new user can see the full product loop immediately.
- **AEG: Run Public Repair Lab** launches isolated repairs of a real,
  MIT-licensed FastAPI nested response-model bug by default.
- The baseline and assisted arms receive identical issue text, code, and tests;
  only the assisted arm receives a compact retrieved recovery capsule.
- Repeated paired trials alternate execution order. Corrected telemetry captures
  duration, completed commands, actual test runs, token usage, changed files, and
  patches under `.aeg/repair-lab/`.
- The runner uses `codex exec --ephemeral --sandbox workspace-write`; it never
  pushes code or contacts the upstream project.
- Verdicts require at least three trials and remain specific to the selected task.

Run it from the AEG sidebar or command palette. The local `codex` executable
must be available on `PATH`.

## First verified-experience retrieval

1. Open a project in VS Code.
2. Select an error or describe a task with **AEG: Try a Verified Experience**.
3. Choose a match and inspect **Why this matched** and its limitations.
4. Copy the compact capsule into the coding-agent session before it begins the
   repair.
5. Validate the result locally, then record whether retrieval was helpful.

For an immediate demo, run **AEG: Open Verified Experience Challenge**. This is
a synthetic, non-identical transfer fixture. Its prior A/B pair produced the
same successful patch in both arms; retrieval changed neither repair path nor
outcome and increased token usage and wall time. It demonstrates the workflow,
not an AEG benefit claim.

## Playwright diagnosis (from v0.1.1)

- A dedicated **AEG Playwright** sidebar and status-bar entry point.
- Failure input from selected text, the latest Playwright artifact, the active file, a copied error, or a short description.
- Ten bundled Playwright recovery playbooks:
  - timeouts
  - unstable selectors
  - authentication and session state
  - network and API mocking
  - flaky tests
  - browser-specific failures
  - test-data isolation
  - CI-only failures
  - trace and artifact diagnosis
  - accessibility failures
- Local experience receipts using the minimum AEG structure:
  - Intent
  - Context
  - Steps
  - Skills
  - Artifacts
  - Failures
  - Recovery
  - Outcome
  - Cost
- Explicit resolved/unresolved verification after a recovery attempt.
- Automatic detection of new text-based artifacts under `test-results`.

## First diagnosis

1. Open a project in VS Code.
2. Run a Playwright test and copy its error, or select an error/stack trace in the editor.
3. Click **AEG Playwright** in the Activity Bar or status bar.
4. Choose **Diagnose Playwright failure**.
5. Select a recommended playbook and try its recovery steps.
6. Re-run the test and mark the outcome **Test passed** or **Still failing**.

AEG stores the receipt under:

```text
.aeg/experiences/
```

Use **AEG: Show Playwright Experiences** to inspect prior receipts.

## Privacy

Version 0.1.5 does not upload code, task descriptions, recovery capsules, logs,
artifacts, ratings, or experience receipts.

- Receipts are local by default.
- Common authorization headers, passwords, tokens, API keys, and credential-bearing URLs are redacted from captured failure signatures.
- Artifact paths are recorded, but raw artifact contents are not written into receipts.
- Sharing is intentionally excluded until AEG has an explicit preview, consent, and redaction flow.

Review a receipt before committing `.aeg/` to source control. Add `.aeg/` to `.gitignore` if the repository should not retain local experience data.

## Existing skill commands

The v0.1.0 local-skill workflow remains available:

- `AEG: Discover Workspace Skills`
- `AEG: Recommend Skill for Current Task`
- `AEG: Rate a Skill`
- `AEG: Show Skill Metrics`

These commands scan local `SKILL.md` and `capability.json` files. Skill metrics remain local in `.aeg/skill-metrics.json`.

## Development

```bash
npm install
npm test
npm run package
```

Open the extension directory in VS Code and press `F5` to launch an Extension Development Host.

## Current limitations

- The verified public library contains only two records and supports no claim
  of general coverage.
- Verified means the recorded outcome was objectively checked; it does not mean
  AEG retrieval caused an improvement.
- Retrieval is deterministic lexical ranking, not embedding-based semantic
  search. No match above the threshold means AEG abstains.
- The bundled transfer challenge is synthetic and is not cross-project
  validation. Its prior controlled pair found no correctness or efficiency
  benefit.
- Playbook ranking is deterministic keyword/signature matching, not semantic retrieval.
- AEG cannot read arbitrary integrated-terminal output; use a selection, clipboard, file, or Playwright artifact.
- Test outcome verification is user-confirmed in this release.
- Token counts are estimates based on captured text length.

These constraints keep the first data loop understandable and auditable while
AEG recruits 5–10 seed users to test whether verified experience is useful on
their real debugging tasks. Please report a concrete retrieval outcome through
the repository issue tracker.
