# Category 01 freshness gate and shortlist

Checked 2026-08-06 UTC. No fresh Pilot 02 was executed.

| Target | Reproducibility | Verifiability | Repeatability | External usefulness | License/data | Bounded cost | Total | Freshness decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mistralai/client-python#490 | 5 | 5 | 5 | 5 | 5 | 5 | 30 | Reject: current main already contains equivalent `asyncio.run` repair; historical replay only. |
| mem0ai/mem0#6830 | 4 | 5 | 5 | 5 | 5 | 3 | 27 | Defer: Windows-to-Git-Bash boundary cannot be verified faithfully on this host. |
| KooshaPari/PhenoFastMCP#13 | 3 | 3 | 4 | 3 | 5 | 4 | 22 | Reject tonight: invalid hook sources reproduce, but initialization exposes 199-file unrelated baseline churn and extensive type failures. |

The remaining previously screened candidates failed at least one gate: scikit-learn#34651 was explicitly not ready for a PR and likely flaky/concurrent; ianvs#614 had a related PR and heavyweight model setup; network-test and automated-data candidates depended on live services. Recommended future target: re-run public search and require a clean, current failing commit plus a locally faithful OS/runtime oracle before final selection.
