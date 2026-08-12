# v0.1.6 founder UX acceptance

This is a usability gate, not an experiment arm and not evidence of repair benefit.

## Clean-install precondition

1. Uninstall any existing **Agent Experience Graph** extension from VS Code.
2. Close every VS Code window.
3. Install the v0.1.6 VSIX with `code --install-extension /absolute/path/to/agent-experience-graph-0.1.6.vsix --force`.
4. Open a disposable public or local test workspace in a fresh VS Code window.

## Exact three-minute founder test

Start a three-minute timer after the AEG walkthrough appears.

1. Confirm the walkthrough and sidebar make **AEG: Start with Verified Experience** the obvious first action, with **2 records · 2 task families** visible and legacy tools collapsed under **Advanced**.
2. Run the primary command with: `Keepalive control fails after active stream ownership moved behind a protocol object; repair the public wrapper so it delegates through the protocol without using its stale socket field.`
3. Select the above-threshold result. Confirm the panel keeps the original query visible and shows matching phrases, score, verified outcome, public provenance, constraints, limitations, and the “guidance, not a guaranteed answer” guardrail.
4. Select **Copy capsule**. Confirm the clipboard contains the capsule and the panel says exactly how to open VS Code Chat, where to paste it, and that AEG did not send or run it.
5. For this usability test, select **Did not apply**, then **Irrelevant**. Confirm `.aeg/verified-experience-feedback.json` links the original query summary, selected experience ID/task, validation outcome, rating, retrieval score, and local-only flag.
6. Start again with: `Change the website navigation background from white to blue and increase the logo size.` Confirm **No relevant verified experience** is presented as a correct outcome with score/threshold reasoning, coverage, and no injected fallback.

## Pass criteria

- The primary command is discoverable without opening a README.
- Every matched step is ordered and understandable without guessing the next action.
- The user cannot validate before copying or rate before validation.
- Match evidence and evidence limitations remain visible before handoff.
- Handoff uses only clipboard plus explicit instructions; no undocumented chat command is invoked.
- Feedback connects query, selected experience, observed validation outcome, and rating in a local workspace file.
- Abstention is calm, explicit, and informative.
- No network request, upload, model run, Repair Lab run, experiment arm, release, or Marketplace publish occurs.

Any failed item keeps the release out of the founder usability gate. Do not reinterpret a usability pass as performance, adoption, PMF, or generalization evidence.
