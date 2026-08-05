# Source and license

- Upstream repository: https://github.com/fastapi/fastapi
- Buggy commit: `7cea84b74ca3106a7f861b774e9d215e5228728f`
- Fixed commit: `75a07f24bf01a31225ee687f3e2b3fc1981b67ab`
- Upstream issue/PR: https://github.com/fastapi/fastapi/pull/889
- Upstream files: `fastapi/utils.py`, `tests/test_filter_pydantic_sub_model.py`
- License: MIT
- Dataset cross-reference: BugsInPy, project `fastapi`, bug `5`

The dependency-free fixture preserves the upstream failure mechanism: a response
model clone reuses a nested field, allowing a subclass instance to retain an
undeclared sensitive field. Names and surrounding implementation are adapted so
the experiment can run without installing historical FastAPI/Pydantic versions.
The golden patch is not included in either agent workspace.
