# Migration Lab evidence and delivery

## Delivery principle

Operator instruction recorded on 2026-10-18: real AEG work should leave timely,
publicly inspectable GitHub evidence. Commit counts and activity are not goals.
For already authorized work, follow: actual work -> necessary verification ->
clear, scoped commit -> authorized push -> remote verification.

Each increment should state the question, reproduction method, observed result,
and limitations. Preserve failures, no improvement, and incomplete work as such.
Preparation does not establish experimental effectiveness. Reuse existing work;
do not rerun costly experiments or create new ones just to publish. If no suitable
unpublished increment exists, report that fact. Review the exact diff and every
outgoing commit for credentials, personal or employer data, and unrelated work;
stage explicit paths only. Publish only within existing scope and budget on the
authorized non-main branch. A blocked push leaves local evidence and a concrete
blocker. This principle grants no additional execution authority and changes no
frozen baseline, paused task, schedule, or publication destination.

## Historical integration preflight, now published

[integration-preflight-20260929.json](integration-preflight-20260929.json) is an
existing local record observed on 2026-09-29, published unchanged in this delivery.
Its SHA-256 is `0debb68bfaf3b765b4786820f18025a3a5393ac9ef57c237ea57e98c4cbebfc3`.
Its `publication` field describes its historical local-only state; this commit
publishes it without rewriting that historical statement.

**Question:** did the local integration preflight stop when no Migration Lab case
was READY, and distinguish configuration, manual preflight, and timed execution?

**Recorded result:** the pinned queue was empty; the preflight recorded
`NO_READY_MIGRATION_CASE` (`NO_READY_TASK`), zero claims and zero executed cases.
It recorded configuration separately from scheduler execution and did not certify
execution isolation or available case budget. This is integration evidence, not
a React 19 migration, fixture calibration, or experience-transfer result.

**Lightweight reproduction:** from the repository root, with Python 3 and Git
available and the historical commit already present, run:

```sh
python3 - <<'PY'
import hashlib
import json
import subprocess
from pathlib import Path

path = Path('coordination/migration-lab-v0-1/evidence/integration-preflight-20260929.json')
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '0debb68bfaf3b765b4786820f18025a3a5393ac9ef57c237ea57e98c4cbebfc3'
report = json.loads(raw)
revision = report['pinned_read_commit']
for name, expected in report['contract_sha256'].items():
    blob = subprocess.check_output(['git', 'show', f'{revision}:{name}'])
    assert hashlib.sha256(blob).hexdigest() == expected, name
queue = json.loads(subprocess.check_output([
    'git', 'show', f'{revision}:coordination/migration-lab-v0-1/queue.json'
]))
assert queue['tasks'] == []
assert report['handoff_stop_reason'] == 'NO_READY_MIGRATION_CASE'
assert report['preflight']['claims_created'] == 0
assert report['preflight']['cases_executed'] == 0
assert report['scheduler_execution']['observed'] is False
assert report['scheduler_execution']['configuration_or_manual_preflight_proves_dispatch'] is False
print('PASS: preserved record, four historical digests, empty queue, and recorded stop semantics')
PY
```

**Publication review on 2026-10-18:** the historical four file digests and empty
queue matched Git objects. The evidence blob and path were absent from the current
dedicated remote branch at `542824ff5b044374dbb1af1514140eded41af4e6`, and no commit
for this path was found in available local refs. The newer React 19 task packet
and fixture preparation handoff were already published. The dedicated workspace
contained no unpublished React 19 fixture implementation or execution result.

**Limits:** these checks verify file integrity and consistency, not the historical
runtime observations independently. Configuration, original-checkout preservation,
and scheduler counters in the JSON remain historical recorded observations, not
current readbacks. At the publication base, `ML-REACT19-001` revision 1 still had
`NEEDS_EVIDENCE` and `dispatch_authorized: false`; that differs from the historical
empty queue. No dependency installation, target build, fixture, oracle, or solver
arm ran for this publication. Aggregate agent-minute consumption and remaining
case/day/week budget are UNKNOWN; this review does not reset or reserve them.
No migration correctness or efficiency improvement is established.
