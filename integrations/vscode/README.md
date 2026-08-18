# Agent Experience Graph for VS Code

AEG v0.1.6 is a local-first product-proof release with one primary workflow:

**Task or error → verified match or explicit abstention → evidence and limitations → guarded capsule handoff → observed validation → local feedback**

AEG retrieves guidance. It does not automatically solve, send, or run the task.

## Install a local build

```bash
cd integrations/vscode
npm ci
npm test
npm run package
code --install-extension agent-experience-graph-0.1.6.vsix --force
```

Open any test workspace in a fresh VS Code window. On first activation in a
normal workspace, the five-step walkthrough opens once and stores a versioned
profile marker. Later windows do not force it open. It remains available from
the AEG sidebar as **Guided walkthrough** and through **AEG: Open Founder Proof
Walkthrough**. If automatic opening is skipped or fails, the status bar still
shows **AEG: Start here**.

The initial founder run exposed a discovery failure, and the onboarding fix was
then re-tested successfully in a clean profile on 2026-08-14 using VSIX
SHA-256
`18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`.
The founder usability/discoverability gate passed: first-workspace auto-open,
all five steps, local feedback creation, second-workspace suppression, and
manual reopen were confirmed. The product-proof experiment remains prepared,
not frozen, with 0/3 arms executed.

## Golden path

1. Select error text or run **AEG: Start with Verified Experience** and enter a task.
2. AEG searches the bundled verified-only library locally.
3. If a result clears the fixed threshold, select it and inspect the exact matching phrases, weighted score, verified source outcome, provenance, constraints, and limitations.
4. Select **Copy capsule**. Open VS Code Chat from the Chat menu (macOS: Control+Command+I; Windows/Linux: Ctrl+Alt+I), paste into the chat input with the original task, and press Enter. For another coding agent, paste into its normal task or prompt input before it starts.
5. Run focused and regression checks. Record **Checks passed**, **Partially passed**, **Still failing**, or **Did not apply**.
6. Rate the selected experience **Helpful**, **Partially helpful**, **Irrelevant**, or **Harmful**.

The panel keeps the original query and selected experience ID visible through validation and rating. It will not enable validation before handoff or rating before validation.

## Honest coverage and abstention

The public library contains exactly two verified records in two narrow task families:

- agent evaluation and telemetry integrity;
- delegation and API contract repair.

Retrieval is deterministic lexical ranking with a fixed 0.0500 threshold. **No relevant verified experience** is a correct outcome: AEG explains the best score or zero-score result, shows current coverage, and injects no candidate or generic fallback guidance.

Verified means the recorded source outcome was objectively checked. It does not mean AEG retrieval improved correctness, success, speed, cost, or generalization.

## Handoff API decision

VS Code documents `vscode.editorChat.start` for editor chat, but no stable extension API to open and prefill the normal Chat view. v0.1.6 therefore uses the supported clipboard API plus explicit paste-and-run instructions. It does not call an undocumented or private workbench command and never submits the capsule automatically.

## Local feedback

Feedback is appended to:

```text
.aeg/verified-experience-feedback.json
```

Each row links a local proof-loop session, redacted query summary, selected experience ID and task, retrieval score, observed validation outcome, and rating. Review or ignore `.aeg/` before committing it.

## Advanced capabilities

The sidebar keeps prior capabilities under a collapsed **Advanced** section, and every existing command ID remains registered for backward compatibility:

- bundled synthetic transfer challenge;
- Playwright artifact diagnosis, local receipts, and outcome marking;
- Public Repair Lab;
- workspace skill discovery, recommendation, rating, and local metrics;
- legacy getting-started content.

The synthetic challenge demonstrates the interaction flow only. Its prior pair produced the same successful patch and repair path in both arms while assisted tokens and wall time were higher. The legacy Repair Lab and Playwright tools are not part of the default v0.1.6 path.

## Privacy

AEG v0.1.6 does not upload code, task descriptions, prompts, recovery capsules, logs, artifacts, ratings, receipts, or private data.

- Search, ranking, clipboard handoff, and feedback are local.
- Common credentials are redacted from captured Playwright failure signatures.
- Raw Playwright artifact content is not written into receipts.
- There is no telemetry or sharing path in the verified-experience workflow.

## Development

```bash
npm ci
npm test
npm run compile
npm run package
```

`npm test` compiles TypeScript, runs extension retrieval, proof-loop, and
first-run state-transition tests, validates the product-proof protocol/result
schemas, and verifies walkthrough assets. Packaging synchronizes the unchanged
two-record verified library into the VSIX.

## Current limitations

- The verified library has only two records and does not provide broad coverage.
- Retrieval is lexical, not embedding-based semantic search.
- The user confirms objective validation outcomes; AEG does not independently run or observe the checks.
- The normal Chat handoff is manual because no documented stable prefilled-Chat API is used.
- Automatic onboarding is scoped to the first activation with a workspace; an
  empty window keeps the marker unset and exposes the status-bar fallback.
- The bundled challenge demonstrates discoverability and interaction, not performance benefit.
- Prior transfer evidence is neutral or negative and supports no claim of improved success, speed, cost, PMF, adoption, or generalization.
