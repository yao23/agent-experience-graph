# 60-Second Demo Talk Track

## Goal

Show one memorable moment:

> An agent starts a task, retrieves experience from previous agents, and changes its execution plan.

This demo is intentionally lightweight. It is not meant to prove the final architecture. It is meant to make the product abstraction easy to understand in a short meeting.

## Demo Script

Open `docs/60-second-demo.html` in a browser.

Say:

> Suppose I am building a documentation ingestion pipeline for an agent coding assistant.
>
> Today, an agent would usually start from scratch: search docs, try a parser, retry failures, adjust chunking, and eventually discover a workable pipeline.
>
> Agent Experience Graph changes the starting point. Before execution, it searches prior execution traces — not just documents — and finds similar workflows, tool choices, validation patterns, and known failures.

Click **Run Experience Lookup**.

Then say:

> Here it finds a similar RAG/API documentation ingestion workflow. It recommends a proven tool chain, warns about a parser that previously caused retry loops, and adds guardrails such as timeout limits and validation before indexing.
>
> The goal is not to replace the model. The goal is to help the model start with collective execution experience instead of an empty slate.

When the metrics appear:

> In the real version, these metrics would be computed from observed traces: token cost, retries, latency, success rate, and validation outcomes. Every execution can make future agents more reliable.

## Core Message

Today's agents share foundation models, but they do not share execution experience.

Agent Experience Graph explores whether execution traces — workflows, tool choices, failure modes, validation signals, and constraints — can become reusable assets for agent developers.

## Questions to Ask

- What is the right abstraction for reusable agent skills?
- Are failure patterns more reusable than successful workflows?
- Should skills be prompts, tools, workflows, policies, or all of the above?
- Where would this fit in the current agent developer ecosystem?
- What would make this useful for real developers rather than just an interesting demo?
