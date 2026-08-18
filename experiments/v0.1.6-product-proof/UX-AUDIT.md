# v0.1.5 audit and v0.1.6 founder-discovery incident

Audit date: 2026-08-11. Baseline: `origin/main` at `544874c`, extension version 0.1.5.

The untouched baseline compiled, passed all 20 extension tests, and produced a local VSIX. The individual features worked, but a first-time user had no clearly dominant workflow:

- **Try a Verified Experience**, **Open Verified Experience Challenge**, Playwright diagnosis, outcome marking, receipt history, Repair Lab, and skill tools appeared at similar prominence across the sidebar, command palette, editor context menu, view title, and status bar.
- The Activity Bar view was named **Verified Experience & Playwright**, so product identity and a legacy diagnosis vertical competed before the user entered a task.
- The primary verified card explained a match and copied a guarded capsule, but did not tell the user exactly which chat input to use or advance through an explicit validation state.
- Four usefulness buttons were available before any observed outcome was recorded. Feedback linked the query and experience, but not a validation result.
- The UI did not foreground the two-record/two-family coverage boundary. Abstention appeared as a transient notification, which could read like failure rather than calibrated retrieval.
- The README carried the only end-to-end explanation; there was no first-install walkthrough that tracked completion.

The v0.1.6 decision is one reversible path: **Start with Verified Experience → inspect match or abstention → copy with explicit paste instructions → record objective validation → save local rating**. Playwright, Repair Lab, skill discovery, and all legacy command IDs remain available under **Advanced**.

The supported VS Code command list documents `vscode.editorChat.start`, which starts editor chat, but does not document a stable command for an extension to open and prefill the normal Chat view. v0.1.6 therefore uses the supported clipboard API and tells the user exactly how to open Chat, paste, and run; it does not depend on a private workbench command.

## v0.1.6 founder result: discovery gate failed

The founder installed the local v0.1.6 VSIX successfully. After receiving
external Command Palette instructions, the founder completed the verified path
end to end: match, evidence inspection, guarded capsule copy, validation, and a
local feedback record. The saved row retained the query, experience ID, score,
`validationOutcome: "not-applied"`, `rating: "Irrelevant"`, and
`localOnly: true`.

That functional result does not pass the usability gate. The first-install
walkthrough did not appear, and no primary AEG action drew the founder into the
flow. The overall founder gate is **failed; re-test required**.

## Precise root cause

The v0.1.6 package contributed a valid walkthrough, but relied entirely on VS
Code's generic “open on install” behavior. In VS Code, that behavior is driven
by an in-memory set populated by the focused window's extension-install event.
Only a newly registered walkthrough whose extension ID is in that same-session
set is selected for automatic opening. A command-line VSIX install performed
while all VS Code windows are closed has no focused workbench session to receive
the install event. On the next launch, the walkthrough is registered as new,
but its extension ID is not in the session-install set, so it is not opened.

AEG had no startup activation event and no first-run code of its own. Its only
activation paths were the AEG view and AEG commands—the exact surfaces the
founder did not yet know to use. Therefore neither the walkthrough nor the
status-bar action was guaranteed to appear in the real install-then-launch path.

## Minimal first-run fix

- `onStartupFinished` activates AEG after startup without blocking the startup
  path.
- First activation in a normal workspace opens the founder walkthrough through
  a fire-and-forget call.
- A global, versioned marker records `opening`, `opened`, or `failed`. `opened`
  suppresses later windows; `failed` retries; a one-minute stale `opening`
  marker recovers from a killed or reloaded extension host without allowing two
  simultaneous windows to race the walkthrough open.
- Marker reads and writes are best effort. Any failure leaves startup running
  and the visible fallback available.
- **AEG: Start here** stays in the status bar after deferred activation and
  invokes the primary verified-experience path. The AEG sidebar retains a
  direct **Guided walkthrough** item and the manual reopen command remains
  registered.

## Follow-up founder acceptance — PASS

On 2026-08-14, the founder re-tested VSIX SHA-256
`18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`
in a clean VS Code profile:

- the first empty workspace automatically opened **AEG verified-experience
  proof loop**;
- all five steps completed and the local feedback file was created;
- a second workspace using the same profile did not force the walkthrough
  open; and
- **AEG: Open Founder Proof Walkthrough** manually reopened it successfully.

The founder usability/discoverability gate is therefore **passed**. No
repair-performance arm ran. The product-proof experiment remains prepared, not
frozen, with 0/3 arms, and this usability result supports no claim about repair
success, speed, cost, adoption, product-market fit, or generalization.
