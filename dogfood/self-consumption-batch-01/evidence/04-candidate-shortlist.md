# Category 04 candidate shortlist

| Rank | Candidate | Score | Decision |
| --- | --- | ---: | --- |
| 1 | Pendulum PR #920, fluent-helper example state leak | 8.7/10 | Selected for non-blind local validation. MIT, one docs file, five credential-free outputs, current main still reproduces; existing PR prevents duplicate contribution. |
| 2 | FastAPI historical “First Steps” example correction | 6.0/10 | Rejected as old and already released; less useful than a currently reproducible example. |
| 3 | OpenAPI Generator asyncio README issue #763 | 4.7/10 | Rejected as generator-wide, credential/API-oriented, and outside the one-example bound. |

PR #920's proposed patch also contained trailing whitespace in its explanatory comment. The local replay retained the semantic fix but shortened that line so `git diff --check` passed. No upstream comment or competing patch was created.
