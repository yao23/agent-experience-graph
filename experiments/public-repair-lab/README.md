# AEG Public Repair Lab

Version 0.1.2 starts with one real, reproducible public bug rather than a broad
crawler. The experiment compares two fresh Codex sessions against identical code:

- **baseline** receives the issue, buggy code, and regression test;
- **assisted** receives the same inputs plus one sanitized AEG experience.

Both arms must run the same focused test. The runner captures JSONL agent events,
duration, token usage, commands, test invocations, changed files, patches, and
objective post-run verification.

## Run

```bash
python3 experiments/public-repair-lab/run_experiment.py
```

The command requires `codex` on `PATH`. It uses ephemeral sessions and a
workspace-write sandbox. It never pushes, comments, or opens a pull request.

Validate fixture preparation without invoking an agent:

```bash
python3 experiments/public-repair-lab/run_experiment.py --prepare-only
```

Results are written under `.aeg/repair-lab/`. Review `report.md`, `report.json`,
the two patches, and the raw JSONL streams together. One task validates the
instrumentation; it does not establish that AEG improves repair performance.
