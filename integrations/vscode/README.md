# Agent Experience Graph for VS Code

AEG v0.1.2 preserves the Playwright diagnosis workflow and adds one auditable
public repair experiment that measures baseline Codex against AEG-assisted Codex.

The extension is an early, local-first implementation of the Agent Experience Graph:

**Failure context → Recovery skill → Execution steps → Verified outcome**

## What is new in v0.1.2

- **AEG: Run Public Repair Lab** launches two isolated repairs of one real,
  MIT-licensed PySnooper bug.
- The baseline and assisted arms receive identical issue text, code, and tests;
  only the assisted arm receives a sanitized AEG recovery experience.
- Objective verification and JSONL telemetry capture duration, commands, test
  runs, token usage, changed files, and patches under `.aeg/repair-lab/`.
- The runner uses `codex exec --ephemeral --sandbox workspace-write`; it never
  pushes code or contacts the upstream project.
- The experiment is explicitly an instrumentation trial, not a statistical
  performance claim.

Run it from the AEG sidebar or command palette. The local `codex` executable
must be available on `PATH`.

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

Version 0.1.2 does not upload code, logs, artifacts, or experience receipts.

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

- Playbook ranking is deterministic keyword/signature matching, not semantic retrieval.
- AEG cannot read arbitrary integrated-terminal output; use a selection, clipboard, file, or Playwright artifact.
- Test outcome verification is user-confirmed in this release.
- Token counts are estimates based on captured text length.

These constraints keep the first data loop understandable and auditable while AEG validates the Playwright failure-diagnosis wedge.
