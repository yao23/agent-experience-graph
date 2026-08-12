# v0.1.5 first-user UX audit

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
