# Category 06 candidate shortlist

| Rank | Candidate | Score | Decision |
| --- | --- | ---: | --- |
| 1 | USGS FDSN earthquake GeoJSON, fixed 2025-01-01 UTC window | 9.0/10 | Selected. Public domain, credential-free, 100-record/72 KB bound, explicit schema, reproducible type and metadata quality hazards. |
| 2 | USGS real-time earthquake feed | 7.0/10 | Rejected for this pilot because continuous revision weakens repeat-run determinism. |
| 3 | NOAA public weather observations | 5.8/10 | Rejected because station selection and missing-value semantics would expand the contract beyond one small quality assertion. |

No raw event row is stored in the AEG repository. The fixed historical window remains revisable upstream, so source response digests are frozen and deterministic claims apply to those downloaded bytes, not to all future responses from the URL.
