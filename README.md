# Agent Experience Graph

Agent Experience Graph helps AI agents learn from how other agents solved similar problems.

Think of it like a shared memory of successful work patterns. When an agent starts a new task, it can look at previous tasks, see which parts were similar, and learn which tools, skills, and approaches helped before.

For example:

- Your agent needs to solve a task with subtasks `A`, `B`, and `C`.
- Another agent previously solved a related task with subtasks `A`, `C`, and `D`.
- That earlier agent used skills `Y` and `Z` successfully for `A` and `C`.
- Agent Experience Graph can suggest that `Y` and `Z` may also help your current agent.

The goal is simple: agents should not start from zero every time. They should be able to reuse lessons from past work, just like people do.

## Why This Matters

Modern AI agents can use many tools: browsers, code editors, search systems, databases, GitHub, terminal commands, design tools, and specialized skills. But choosing the right tool at the right time is still hard.

Agent Experience Graph gives agents a way to ask:

- Has anyone solved a similar task before?
- How did they break the task into smaller steps?
- Which tools or skills helped?
- Which tools failed or wasted time?
- What should I watch out for?

This can make agents more reliable, faster to start, and easier to improve over time.

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

In plain English, this repository contains:

- a guide that tells an agent how to use prior experience
- a simple data format for saving agent work summaries
- a small script that compares a new task against past tasks
- example traces so people can try the idea quickly

## Who It Is For

This project may be useful for:

- people experimenting with AI agents
- teams building agent workflows
- researchers studying agent memory and tool use
- open-source developers creating reusable skills
- companies that want agents to learn from internal playbooks without exposing sensitive data

## Privacy First

Agent Experience Graph is designed around sanitized traces, not raw logs.

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
  --traces assets/example_traces.json \
  --query '{"task":"Build markdown API docs ingestion","subtasks":[{"description":"parse markdown into sections"},{"description":"evaluate endpoint metadata extraction"}]}'
```

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

MIT-0.
