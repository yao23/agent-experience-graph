# Agent Experience Graph

Agent Experience Graph helps coding agents retrieve verified debugging
experience instead of solving every problem from scratch.

The v0.1.6 product-proof release gives the VS Code extension one honest path:
a task or error becomes an explainable verified match or explicit abstention;
an above-threshold match exposes evidence and limitations before a guarded
capsule is copied; the user then records an objective validation outcome and
local usefulness rating. It retrieves guidance and does not automatically
solve, send, or run the task.

Think of it like a shared memory of successful work patterns. When an agent starts a new task, it can look at previous tasks, see which parts were similar, and learn which tools, skills, and approaches helped before.

For example:

- Your agent needs to solve a task with subtasks `A`, `B`, and `C`.
- Another agent previously solved a related task with subtasks `A`, `C`, and `D`.
- That earlier agent used skills `Y` and `Z` successfully for `A` and `C`.
- Agent Experience Graph can suggest that `Y` and `Z` may also help your current agent.

The goal is simple: agents should not start from zero every time. They should be able to reuse lessons from past work, just like people do.

## Living Pitch

Open the investor- and partner-friendly living pitch:

- [Experience Infrastructure for AI Agents](pitch/index.html)

The pitch covers the vision, problem, architecture, initial product, early progress, business model, roadmap, founder, and current ask.

## v0.1.6 VS Code quick start

The v0.1.6 clean-profile founder usability gate passed on 2026-08-14 using the
local VSIX with SHA-256
`18ef493b9290e28832e54527d7fb92624387a17d749ec228b60087c3b6917224`.
On first activation in a normal workspace, AEG opens the founder walkthrough
once. If opening is skipped or fails, the persistent **AEG: Start here**
status-bar action is the primary entry without README or Command Palette
knowledge. The walkthrough also remains available from the AEG sidebar.

Then follow this quick start:

1. Run **AEG: Start with Verified Experience** and describe a task or select an error.
2. Inspect the score, matching phrases, provenance, constraints, and limitations—or accept **No relevant verified experience** as a correct outcome.
3. Copy an above-threshold guarded capsule. Open VS Code Chat, paste it into the chat input with the original task, and press Enter.
4. Run focused and regression checks, record the observed outcome, then rate the selected experience locally.

The sidebar shows the honest boundary up front: **2 verified records · 2 task
families**. Playwright diagnosis, Repair Lab, skill discovery, the synthetic
challenge, and legacy commands remain available under **Advanced**.

The founder pass validates usability and discoverability only. The product-proof
experiment remains prepared, not frozen, with 0/3 arms executed; it supports no
claim of better repair success, speed, cost, adoption, product-market fit, or
generalization. See
[`experiments/v0.1.6-product-proof/UX-ACCEPTANCE.md`](experiments/v0.1.6-product-proof/UX-ACCEPTANCE.md).

For zero-cold-start onboarding, use the walkthrough's bundled guided task. The
Advanced **Open Bundled Transfer Challenge** command uses a synthetic fixture and reports
that its prior controlled pair found no repair-path or outcome improvement and
higher assisted token and wall-time cost. See
[`experiments/verified-experience-challenge/`](experiments/verified-experience-challenge/).

### Example verified experience card

> **Restore Tornado WebSocket TCP_NODELAY delegation** · outcome: success ·
> verification: passed
>
> **Reusable lesson:** When resource ownership moves behind an abstraction,
> public controls must follow the ownership chain instead of retaining a stale
> direct reference.
>
> **Recommended for:** repairing a public wrapper after resource ownership
> moves behind a protocol object; testing delegation through multiple layers.
>
> **Constraint:** the first suite-green candidate changed the wrong client-side
> surface and was rejected; the successful second attempt was evaluator-informed.
>
> **Limitation:** this source repair is verified, but it is not causal evidence
> that AEG retrieval improves repairs.
>
> **Provenance:** Apache-2.0 Tornado, BugsInPy bug 1; public SHAs and full
> validation evidence are recorded in `experiences/verified.json`.

## 60-Second Demo

Select the visible **AEG: Start here** status-bar action or use the bundled task
in the walkthrough. The demo shows task entry,
verified-only retrieval, weighted match evidence, a compact guarded capsule,
explicit paste instructions, validation, and local usefulness feedback.

Use [`docs/60-second-demo.md`](docs/60-second-demo.md) for a short meeting talk track.

## Why This Matters

Modern AI agents can use many tools: browsers, code editors, search systems, databases, GitHub, terminal commands, design tools, and specialized skills. But choosing the right tool at the right time is still hard.

Agent Experience Graph gives agents a way to ask:

- Has anyone solved a similar task before?
- How did they break the task into smaller steps?
- Which tools or skills helped?
- Which tools failed or wasted time?
- What should I watch out for?

Whether this makes agents more reliable or efficient is an open question that
requires controlled evidence beyond the current two-record library.

## A Non-Technical Example

Imagine a new employee joining a company. They could try to figure everything out alone, or they could ask:

> "Who has done something like this before, and what worked for them?"

Agent Experience Graph gives AI agents that same kind of workplace memory.

Instead of sharing private files or raw conversations, it stores short, cleaned-up summaries:

- what the task was
- what smaller steps were involved
- which tools or skills were used
- whether the attempt succeeded
- what lesson future agents should remember

## What It Does

It is intentionally runtime-neutral:

- `SKILL.md` contains the instructions an agent can load directly.
- `capability.json` describes the capability for launchers, registries, and importers.
- `scripts/recommend_traces.py` ranks similar traces and recommends reusable skills/tools.
- `references/trace_schema.md` defines the trace data contract.
- `experiences/verified.json` stores sanitized, executed, and objectively verified shared experiences.
- `integrations/vscode/` exposes the v0.1.6 verified-experience golden path and
  keeps prior Playwright, Repair Lab, and skill tools under Advanced.
- `experiments/verified-experience-challenge/` supplies a transparent bundled
  transfer demo.
- `experiments/public-repair-lab/` runs the first baseline-versus-AEG public bug repair experiment.

## Public Repair Lab (v0.1.3)

AEG includes two narrow, reproducible A/B tasks derived from MIT-licensed public
bugs. The default reproduces FastAPI's nested response-model data leak; the
original PySnooper path-output task remains available. Fresh Codex sessions
receive identical issues, buggy code, and regression tests. The assisted arm
also receives a compact, sanitized recovery capsule injected directly into its
prompt.

The runner supports repeated paired trials with alternating execution order and
records objective verification, completed commands, actual test invocations,
token usage, duration, changed files, patches, and raw JSONL events. It requires
at least three trials before reporting an efficiency verdict.

```bash
python3 experiments/public-repair-lab/run_experiment.py --prepare-only
python3 experiments/public-repair-lab/run_experiment.py --trials 5
```

In the v0.1.3 five-pair validation, all ten arms produced the same verified
one-line fix. AEG-assisted runs used one fewer completed command in the paired
median and 732 fewer non-cached tokens, while wall time regressed by 18.2 seconds.
This is a bounded tool-cycle/cost signal on one task family, not a general speed
or success-rate claim. See `experiments/public-repair-lab/RESULTS.md`.

## Situated Experience Benchmark v1

`experiments/situated-experience-benchmark-v1/` stages a broader, ordered test
of whether AEG helps when repair depends on version state, execution environment,
historical failures, cross-module consequences, multi-agent handoffs, and
experience applicability. Its six families run from dependency migration (S1)
through experience invalidation under environment drift (S6).

Only S1 is implemented. Exactly two natural public source-transfer pairs,
Scrapy/Python CookieJar and FastAPI/Pydantic field representations, are frozen
with offline fixtures, hidden evaluators, deterministic three-replicate arm
orders, common measurement rules, and fail-closed isolation/leakage preflights.
No benchmark arm has run, and S2-S6 remain screening rules only.

```bash
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py validate
python3 experiments/situated-experience-benchmark-v1/run_benchmark.py preflight
```

In plain English, this repository contains:

- a guide that tells an agent how to use prior experience
- a simple data format for saving agent work summaries
- a small script that compares a new task against past tasks
- example traces so people can try the idea quickly
- a short demo that makes the product idea easy to explain

## Reuse verified experiences

The public library under `experiences/` contains compact records backed by
execution evidence and explicit limitations. Its reuse tags and recommended-use
phrases participate directly in explainable retrieval. Retrieve from it directly:

```bash
python3 scripts/recommend_traces.py \
  --traces experiences/verified.json \
  --query '{"task":"repair duplicated JSONL event metrics"}'
```

The Repair Lab's five-pair counters are published separately as a sanitized,
machine-readable artifact whose medians are recomputed and cross-checked in CI.
Experiment provenance is distinct from promotion-workflow provenance, and
unavailable original-run metadata is explicitly `null`. See
`experiences/README.md` for schema, audit, promotion, and redaction requirements.

## Who It Is For

This project may be useful for:

- people experimenting with AI agents
- teams building agent workflows
- researchers studying agent memory and tool use
- open-source developers creating reusable skills
- companies that want agents to learn from internal playbooks without exposing sensitive data

## Privacy First

Agent Experience Graph is designed around sanitized traces, not raw logs.

The v0.1.6 extension bundles its public verified library and performs retrieval
locally. It does not upload task text, code, prompts, logs, recovery capsules,
receipts, ratings, or private data. Local validation outcomes and ratings are
stored under `.aeg/`; review or ignore that directory before committing it.

That means shared traces should not contain:

- passwords, tokens, or credentials
- private user data
- proprietary source code
- customer documents
- full conversations or raw prompts

Instead, traces should capture the reusable lesson:

> "For this kind of task, this decomposition worked, these tools helped, and this warning matters."

## Try It

```bash
python3 scripts/recommend_traces.py \
  --traces experiences/verified.json \
  --query '{"task":"repair a public wrapper after resource ownership moved behind a protocol"}'
```

The public verified library currently contains two records. Existing evidence
supports verified source repairs and bounded controlled comparisons, not broad
coverage, cross-project transfer, or a generalized correctness/efficiency
benefit. AEG is seeking 5–10 seed users willing to report concrete helpful,
neutral, irrelevant, or harmful retrieval outcomes on real debugging tasks.
Bring a public GitHub issue or failing test and see whether AEG finds a reusable
verified lesson.

## Install

- Codex: copy this directory to `$CODEX_HOME/skills/agent-experience-graph`
- Claude Code: copy this directory to `.claude/skills/agent-experience-graph` or `~/.claude/skills/agent-experience-graph`
- OpenClaw: install from ClawHub with `clawhub install agent-experience-graph`
- Generic agents: load `SKILL.md` as instructions and expose `scripts/recommend_traces.py` as a helper

## Record A Trace

Create a sanitized JSON trace with `id`, `task`, `outcome`, optional `subtasks`, `skills`, `tools`, and `lessons`, then append it:

```bash
python3 scripts/recommend_traces.py \
  --traces traces.json \
  --append-trace new_trace.json
```

Do not include secrets, credentials, private user data, proprietary snippets, or raw customer content in shared traces.

## License

MIT-0
