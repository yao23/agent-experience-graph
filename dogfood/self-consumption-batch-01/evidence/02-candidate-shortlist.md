# Category 02 candidate shortlist

Scoring used the spec's freshness, license, bounded scope, reproducible oracle, and duplicate-work gates. Search was bounded to five candidates; the top three are recorded here.

| Rank | Candidate | Score | Decision |
| --- | --- | ---: | --- |
| 1 | `batonogov/pine` issue #122, historical `actions/checkout` v4→v6 | 8.4/10 | Selected as a non-blind historical replay. MIT; exact three-line migration; frozen parent and upstream fix available; local compatibility/YAML oracle. |
| 2 | `OHWR/ohwr.org` issue #385, Node 24 actions | 6.1/10 | Rejected at freshness gate: current `ab44e35` already uses Node-24-compatible major versions for the relevant official actions, so the issue's stated edge no longer reproduces. |
| 3 | `FlagBrew/local-gpss` issue #19, Node 24 actions | 5.8/10 | Rejected at duplicate-work gate: linked PR #20 is already open and addresses the issue. |

Two additional search results (`netbox-community/netbox#21664` and `neomjs/neo#9600`) were already closed with linked fixes and were much broader than the bounded Pine replay.

The selected project is active and permissively licensed, but the issue is closed. That makes the result useful as reproducible migration evidence, not a fresh contribution opportunity.
