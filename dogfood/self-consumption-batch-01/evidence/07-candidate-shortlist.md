# Category 07 candidate shortlist

| Rank | Candidate | Reproducibility | Verifiability | Repeatability | External usefulness | License/data | Bounded cost | Total | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Verified-evidence file resolution | 5 | 5 | 4 | 5 | 5 | 5 | 29 | Selected. Real semantic false positive, deterministic one-record reproduction, two-file fix, no promoted-data or release overlap. |
| 2 | Portable `SKILL.md` 0.1.3 vs extension 0.1.5 version audit | 3 | 3 | 3 | 3 | 5 | 4 | 21 | Rejected: version semantics may intentionally differ and any correction risks release/version overlap explicitly excluded by the spec. |
| 3 | README local-link integrity | 5 | 5 | 3 | 2 | 5 | 5 | 25 | Rejected because all three repository-relative README links already resolve; no defect reproduced. |

The existing extension test already checks equality between the bundled and source verified library, so package-copy drift was not duplicated as a fourth implementation. The selected check runs automatically for the canonical `experiences/verified.json`; arbitrary candidate libraries retain semantic validation without requiring their evidence to live in this repository.
