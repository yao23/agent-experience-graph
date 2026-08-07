# Category 05 candidate shortlist

| Rank | Candidate | Reproducibility | Verifiability | Repeatability | External usefulness | License/data | Bounded cost | Total | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `@modelcontextprotocol/server-filesystem@2026.7.10` | 5 | 5 | 4 | 4 | 3 | 4 | 25 | Selected. Official, active, credential-free stdio, explicit root confinement, read-only probe available. Package-license-file omission downgrades the card to partial. |
| 2 | official MCP Git server | 4 | 4 | 4 | 4 | 5 | 3 | 24 | Not selected: safe local read-only operation is feasible, but filesystem server gives a clearer invalid-path permission oracle. |
| 3 | official MCP Everything server | 5 | 4 | 3 | 3 | 5 | 2 | 22 | Rejected: intentionally broad reference surface is less representative of a narrowly permissioned compatibility card. |

The filesystem server exposes write-capable tools, but none were invoked. The allowed root contained one synthetic text file. The npm package declares `SEE LICENSE IN LICENSE` while the installed package contains no LICENSE file; the public repository license explains an MIT→Apache-2.0 transition for code, but packaged attribution remains incomplete.
