# v0.1.6 founder UX acceptance

This is a usability gate, not an experiment arm and not evidence of repair
benefit.

## Acceptance record — PASS

Founder test date: **2026-08-14** (America/Los_Angeles).

Tested VSIX SHA-256:
`18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`.

- **PASS — clean profile.** The founder tested with a fresh VS Code profile.
- **PASS — first-run discovery.** The first empty workspace automatically
  opened **AEG verified-experience proof loop** without manual command
  discovery.
- **PASS — complete proof loop.** The founder completed all five steps: task
  entry → verified record inspection → capsule copy → validation outcome →
  local feedback.
- **PASS — local persistence.** The local feedback file was created
  successfully.
- **PASS — non-repeating behavior.** A second workspace using the same profile
  did not force the walkthrough open.
- **PASS — manual reopen.** **AEG: Open Founder Proof Walkthrough** reopened the
  walkthrough successfully.
- **PASS — experiment boundary.** No repair-performance experiment arm was
  run.

**Founder usability/discoverability gate: PASSED.** The product-proof
experiment remains **prepared, not frozen; 0/3 arms executed**.

This result validates onboarding usability and discoverability only. It is not
evidence of better repair success, speed, cost, adoption, product-market fit,
or generalization.

## Clean-profile test precondition

An uninstall is not sufficient because extension global state can survive in a
VS Code profile. Use a disposable profile and extensions directory that have
never contained AEG:

```bash
code \
  --user-data-dir /absolute/path/to/aeg-founder-retest/user-data \
  --extensions-dir /absolute/path/to/aeg-founder-retest/extensions \
  --install-extension /absolute/path/to/agent-experience-graph-0.1.6.vsix \
  --force
```

Keep those two directories for both-window checks. Use a fresh disposable local
workspace with at least one folder, and do not give the founder a README,
command name, Command Palette instruction, or outside navigation hint.

## Founder test procedure

1. Launch the fresh workspace with the same disposable `--user-data-dir` and
   `--extensions-dir`. Start a three-minute timer when the window is usable.
2. Confirm the AEG founder walkthrough opens without any manual command. Also
   confirm the status bar exposes **AEG: Start here**, the sidebar reports
   **2 records · 2 task families**, and legacy tools remain collapsed under
   **Advanced**.
3. Start the primary path and enter:
   `Keepalive control fails after active stream ownership moved behind a protocol object; repair the public wrapper so it delegates through the protocol without using its stale socket field.`
4. Select the above-threshold result. Confirm the panel keeps the original
   query visible and shows matching phrases, score, verified outcome, public
   provenance, constraints, limitations, and the “guidance, not a guaranteed
   answer” guardrail.
5. Select **Copy capsule**. Confirm the clipboard contains the capsule and the
   panel says exactly how to open VS Code Chat, where to paste it, and that AEG
   did not send or run it.
6. For this usability test, select **Did not apply**, then **Irrelevant**.
   Confirm `.aeg/verified-experience-feedback.json` links the original query
   summary, selected experience ID/task, validation outcome, rating, retrieval
   score, and local-only flag.
7. Start again with:
   `Change the website navigation background from white to blue and increase the logo size.`
   Confirm **No relevant verified experience** is presented as a correct outcome
   with score/threshold reasoning, coverage, and no injected fallback.
8. Close the first window. Launch a second normal workspace window with the same
   disposable profile and extensions directory. Confirm the walkthrough does
   not force itself open again and **AEG: Start here** remains visible.
9. Open the AEG Activity Bar view and select **Guided walkthrough**. Confirm the
   walkthrough reopens manually without using the Command Palette.

## Pass criteria

- The first normal-workspace activation presents the walkthrough without
  README, Command Palette knowledge, or outside instructions.
- The primary action remains visually discoverable as **AEG: Start here** if
  automatic opening is skipped or fails.
- A second window in the same profile does not force the walkthrough open.
- The founder can reopen it from the AEG sidebar.
- Every matched step is ordered and understandable without guessing the next
  action.
- The user cannot validate before copying or rate before validation.
- Match evidence and evidence limitations remain visible before handoff.
- Handoff uses only clipboard plus explicit instructions; no undocumented chat
  command is invoked.
- Feedback connects query, selected experience, observed validation outcome,
  and rating in a local workspace file.
- Abstention is calm, explicit, and informative.
- No network request, upload, model run, Repair Lab run, experiment arm,
  release, or Marketplace publish occurs.

Any future regression on these items reopens the founder usability gate. Do not
reinterpret this usability pass as performance, adoption, product-market fit,
or generalization evidence.
