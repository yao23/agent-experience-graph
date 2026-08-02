# Source and license

- Upstream repository: https://github.com/cool-RR/PySnooper
- Buggy commit: `6e3d797be3fa0a746fb5b1b7c7fea78eb926c208`
- Fixed commit: `15555ed760000b049aff8fecc79d29339c1224c3`
- Upstream file: `pysnooper/pysnooper.py`
- License: MIT
- Dataset cross-reference: BugsInPy, project `PySnooper`, bug `3`

The fixture keeps only the small path-writer behavior needed to reproduce the
upstream defect. The golden patch is deliberately not included in either agent
workspace. Both experiment arms receive the same issue, code, and test.
