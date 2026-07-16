# Agent Experience Graph for VS Code

An early IDE integration for discovering, recommending, rating, and measuring agent skills directly inside a developer workspace.

## MVP Features

- Discovers local `SKILL.md` and `capability.json` files.
- Recommends skills for selected code/text or a task description.
- Opens the selected skill or copies its path for use by an agent.
- Records local skill-use counts and estimated selection-context tokens.
- Lets developers rate skills from 1 to 5.
- Displays usage, estimated tokens, and average ratings.

Metrics remain local in `.aeg/skill-metrics.json` by default. This MVP does not send telemetry to a hosted service.

## Run Locally

```bash
cd integrations/vscode
npm install
npm run compile
```

Open this directory in VS Code and press `F5` to launch an Extension Development Host.

## Commands

Open the Command Palette and run:

- `AEG: Discover Workspace Skills`
- `AEG: Recommend Skill for Current Task`
- `AEG: Rate a Skill`
- `AEG: Show Skill Metrics`

You can also select text in an editor, right-click, and choose `AEG: Recommend Skill for Current Task`.

## Skill Discovery

The extension scans these workspace patterns by default:

```json
[
  "**/SKILL.md",
  "**/capability.json"
]
```

They can be changed with `aeg.skillGlobs`.

## Local Metrics Format

```json
{
  "skills/example/SKILL.md": {
    "uses": 4,
    "totalEstimatedTokens": 820,
    "ratings": [5, 4],
    "lastUsed": "2026-07-15T12:00:00.000Z"
  }
}
```

The current token number is an estimate based on text length. A production version should collect actual model usage from supported agent runtimes.

## Next Steps

- Semantic embeddings and hybrid ranking instead of keyword overlap.
- Parse richer skill manifests: inputs, outputs, tools, constraints, and compatibility.
- Connect to Codex, OpenAI Agents SDK, Claude Code, MCP, and other runtimes.
- Record actual tokens, cost, latency, retries, validation results, and success rate.
- Add trusted automatic skill loading/install with permission boundaries.
- Publish team and community skill leaderboards.
- Package and publish to the VS Code Marketplace and Open VSX.
