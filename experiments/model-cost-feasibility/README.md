# Natural-transfer model-cost feasibility (no benchmark execution)

This revision compares two execution candidates without changing or executing
the frozen natural-transfer benchmark. The original manifest continues to name
`gpt-5.6-sol`. A separate, non-authorized model-specific protocol records
`gpt-5.4-mini-2026-03-17`; adopting it would require an explicit new benchmark
authorization rather than silently replacing the original model.

## Hosted candidate

GPT-5.4 mini is the lowest-cost current OpenAI model explicitly positioned for
coding while supporting reasoning, structured outputs, hosted shell,
apply-patch, MCP, skills, and tool search. GPT-5.4 nano is cheaper, but OpenAI
positions it for simple extraction, ranking, and subagent work and it lacks tool
search, so it is not treated as suitable for this repair benchmark.

One synthetic, non-benchmark repair smoke task succeeded. It used 69,845 input
tokens (60,672 cached), 811 output tokens, and 20.736 seconds. At published API
rates ($0.75/M uncached input, $0.075/M cached input, $4.50/M output), the
API-equivalent cost is $0.01508. The session used ChatGPT authentication, so its
actual subscription allocation is not observable; it must not be described as
free. A smoke-linear 30-arm floor is $0.45, a five-times-smoke planning estimate
is $2.26, and a ten-times sensitivity is $4.52. These are token-mix projections,
not benchmark measurements.

At GitHub's $0.062/minute macOS baseline, a five-times-smoke duration rounded to
two billed minutes per arm is $3.72 of runner compute, making the central
billing-equivalent total about $5.98. Standard runners are currently unbilled
for this public repository, but the compute has that published economic rate.
The 15-minute per-arm timeout gives a $27.90 runner-compute ceiling before API
cost. Main risks are token use being materially higher than the smoke task,
cache rates differing between isolated arms, model access/rate limits, and the
absence of a repository Actions API credential.

## Local gpt-oss-20b candidate

OpenAI publishes a 13.8 GB Metal artifact and requires at least 16 GB VRAM or
unified memory. The isolated standard `macos-14` runner class has 7 GB RAM and
14 GB advertised SSD, so it is below the memory requirement before any model is
downloaded. The actual CI runner measured 7.52 GB RAM and 42.14 GB free disk.
Python 3.12, Xcode, and the Metal compiler were available, so the runtime was
compatible, but memory failed the 16 GB gate. Temporary-disk reads measured
5.49 GB/s, which gives a 2.51-second best-case weight-read floor; it is not an
end-to-end initialization estimate. No model or benchmark data was downloaded.

Thirty isolated cold starts would transfer at least 414 GB of model weights and
have a purely disk-read floor of 75.36 seconds in aggregate. End-to-end load and
inference time cannot be honestly estimated on a runner that cannot hold the
model. Larger standard macOS arm64 runners documented at 14 GB also remain
below the 16 GB requirement. A genuinely sufficient GPU/unified-memory runner
would introduce separately priced compute, model-download latency, runtime
integration, and maintainability risk; no such runner is currently attached.

Official sources:

- https://developers.openai.com/api/docs/models/gpt-5.4-mini
- https://developers.openai.com/api/docs/models/gpt-5.4-nano
- https://openai.com/index/introducing-gpt-oss/
- https://developers.openai.com/cookbook/articles/gpt-oss/run-locally-ollama
- https://huggingface.co/openai/gpt-oss-20b/tree/main/metal
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
