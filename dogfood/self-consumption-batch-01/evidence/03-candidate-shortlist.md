# Category 03 candidate shortlist

| Rank | Candidate | Score | Decision |
| --- | --- | ---: | --- |
| 1 | AEG `protocol-resource-delegation` transfer fixture | 9.2/10 | Selected. MIT-0, deterministic, dependency-free, exact public wrapper/protocol/stream topology, and explicitly designed to test transfer from TR-04. |
| 2 | Tornado BugsInPy bug 1 historical replay | 7.0/10 | Rejected as duplicate evidence: TR-04 already verified this exact upstream repair and full historical suite. |
| 3 | OpenClaw plugin-config delegation issue #49495 | 4.2/10 | Rejected: large current TypeScript surface, configuration-loss risk, and likely scope beyond three files/25 commands. |

The selected fixture sacrifices fresh upstream contribution value in exchange for a clean transfer measurement. Its source file documents the related Tornado commits and Apache-2.0 license; the fixture itself is original MIT-0 code and contains no copied upstream source.
