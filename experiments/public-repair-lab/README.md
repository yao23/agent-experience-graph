# AEG Public Repair Lab

Version 0.1.3 compares fresh Codex sessions against identical public-bug fixtures:

- **baseline** receives the issue, buggy code, and regression test;
- **assisted** receives the same inputs plus a compact, sanitized AEG recovery capsule.

The default task is a dependency-free reproduction of FastAPI's nested
response-model data leak (BugsInPy `fastapi` bug 5). The original PySnooper
path-output task remains selectable. Both arms must run the same focused test.
The runner captures JSONL agent events, duration, token usage, completed commands,
actual test invocations, changed files, patches, and objective verification.

Repeated trials alternate arm order. Verdicts use paired medians and require at
least three trials. Results must still be read as evidence about the selected
task family, not as a general claim about coding-agent performance.

## Run

```bash
python3 experiments/public-repair-lab/run_experiment.py
python3 experiments/public-repair-lab/run_experiment.py --trials 5
python3 experiments/public-repair-lab/run_experiment.py --task pysnooper-path-output
```

The command requires `codex` on `PATH`. It uses ephemeral sessions and a
workspace-write sandbox. It never pushes, comments, or opens a pull request.

Validate fixture preparation without invoking an agent:

```bash
python3 experiments/public-repair-lab/run_experiment.py --prepare-only
```

Results are written under `.aeg/repair-lab/`. Review `report.md`, `report.json`,
all patches, and the raw JSONL streams together. See `RESULTS.md` for the checked
v0.1.3 validation summary and its limitations.

The public, sanitized five-pair artifact is
`results/v0.1.3-paired-results.json`. Validate its schema and independently
recompute its aggregate with:

```bash
npx --yes ajv-cli@5.0.0 validate --all-errors \
  -s experiments/public-repair-lab/paired-results.schema.json \
  -d experiments/public-repair-lab/results/v0.1.3-paired-results.json
python3 experiments/public-repair-lab/validate_paired_results.py
```

Only aggregate inputs and patch hashes are public. Raw prompts, JSONL, stderr,
complete logs, source patches, credentials, and private paths remain excluded.
