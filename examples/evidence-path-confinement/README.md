# Evidence-path symlink confinement

A repository-relative evidence path can look safe lexically while a file or directory symlink redirects it outside the repository. The baseline validator rejected absolute paths and explicit `..` components, then called `is_file()`. Because that check follows symlinks, an outside target could be accepted as evidence.

This package replays that known regression against the actual production validator source from the pinned baseline and published fix. It is a retrospective technical case: the solution is already known and was published through [PR #30](https://github.com/yao23/agent-experience-graph/pull/30).

## When the case applies

Use this case when code accepts repository-relative file references, symlinks may appear in any path component, outside targets must be rejected, and internal symlinks must remain usable.

It does not apply as proof of general filesystem sandboxing, operating-system authorization, protection against concurrent malicious replacement, or correctness on an operating system where the replay has not run. It is not fresh discovery, a transfer experiment, external adoption evidence, or product-market-fit evidence.

## Run the replay

From a checkout containing the pinned Git history, run:

```bash
python3 examples/evidence-path-confinement/replay.py --json
```

Prerequisites are Python 3, Git, both pinned commits in local history, and local symbolic-link support. The replay uses only the Python standard library. It does not install dependencies or access the network.

The driver verifies the expected commit, tree, Git blob, and SHA-256 identities before use. It exports each pinned production validator into a disposable directory, imports the source verbatim, and calls its `validate_repository_reference` function with inert task-owned fixtures. It never reads a real secret or an unrelated host file.

Exit codes are:

- `0`: `PASS`; every essential before/after observation matched.
- `1`: `FAIL`; the replay ran but behavior differed from the committed matrix.
- `2`: `BLOCKED`; source history, source identity, Git, validator loading, or symlink support was unavailable.

`PASS` is not inferred from a successful process alone. It requires all 13 cases to run against both validators, the baseline to accept all four escape cases, the fixed source to reject them, all legitimate in-root cases to remain accepted, every other invalid case to be rejected, and the temporary directory to be removed.

The JSON keeps `committed_expectations` separate from `observed_replay`. Inspect `status`, `reason_codes`, `source_identity`, `prerequisites`, `summary`, and the per-case decisions. No host-local fixture path is emitted.

## Expected behavior

| Case | Baseline | Fixed |
| --- | --- | --- |
| Ordinary in-root file | accepted | accepted |
| In-root symlink | accepted | accepted |
| Multi-hop in-root symlink | accepted | accepted |
| Direct outside symlink | accepted | rejected |
| Multi-hop outside symlink | accepted | rejected |
| Symlinked-directory escape | accepted | rejected |
| Prefix-collision escape | accepted | rejected |
| Dangling symlink | rejected | rejected |
| Symlink loop | rejected | rejected |
| Missing path | rejected | rejected |
| Absolute path | rejected | rejected |
| Lexical parent traversal | rejected | rejected |
| Directory instead of file | rejected | rejected |

Internal symlinks remain allowed because the fixed validator evaluates their final resolved target. If that target is a regular file beneath the resolved repository root, the reference satisfies the same containment rule as an ordinary file.

Strict resolution makes every path component concrete and fails closed for missing targets, dangling links, and link loops. Component-level containment with `relative_to()` then checks path ancestry rather than comparing string prefixes, so a sibling such as `repository-collision` cannot be mistaken for a descendant of `repository`.

## Limitations

Validation and later file use are separate operations. An attacker able to replace path components concurrently could create a time-of-check/time-of-use race; this replay does not claim to close it. It also does not cover mount changes, network filesystem semantics, every path representation, or platforms that have not run the case. Results are limited to the pinned validator sources and the filesystem used for the invocation.

This package is not a Capture Candidate or Registry Experience. Running it does not authorize publication, make it recommendation-eligible, or change public confidence.
