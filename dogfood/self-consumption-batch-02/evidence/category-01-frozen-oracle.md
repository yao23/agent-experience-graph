# Category 01 frozen oracle

Frozen at 2026-08-07T16:15:42Z before AEG retrieval, diagnosis, or repair-oriented source inspection. SHA-256: `7c33b75bba6eade9e6981cda8d0232717072481a3078a82c3887d6266138b815`.

```python
import io

import click


class TerminalBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


output = TerminalBuffer()
with click.progressbar(
    range(20), file=output, show_pos=True, update_min_steps=7
) as items:
    for _ in items:
        pass

rendered = output.getvalue()
if "20/20" not in rendered:
    raise AssertionError(
        "completed progress bar did not render its final position; "
        f"captured={rendered!r}"
    )
```

Command (with the external checkout and oracle path substituted locally):

```text
PYTHONPATH=src python3.11 aeg-batch02-click-3571-oracle.py
```

Observed pre-fix result at Click `00e592cea702e0b2caa0dee42489fdb1c22cd845`: exit 1. The sanitized captured rendering progressed through 0/20, 7/20, and 14/20, then finalized at 14/20 rather than 20/20.
