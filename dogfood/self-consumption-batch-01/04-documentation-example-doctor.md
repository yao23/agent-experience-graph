# 04 — Documentation example doctor

## Operating contract

- **Project category:** execute and repair one README/tutorial/sample-code path.
- **Independent external value:** make a documented first-use path runnable with declared dependencies.
- **AEG consumption/production:** retrieve version/API/example repair evidence; produce an executable documentation contract with output proof.
- **Selection criteria:** permissive active project; example is small, local, credential-free, and explicitly documented; deterministic command/output; ≤2 doc/example files.
- **Exclusions/safety:** examples requiring accounts, tokens, paid APIs, cloud deployment, large downloads, subjective prose-only edits, copyright-heavy content.
- **Bounded pilot:** one example from setup through expected output; five candidates/three scored; 30 minutes/20 commands.

## Procedure

1. **Freeze:** record doc URL/path, commit/version, exact commands, expected output, dependencies, license, scope and oracle; hash manifest.
2. **Retrieve:** query verified AEG library for example, outdated import, path, command and version drift; record scores/evidence/threshold/capsule.
3. **Execute:** follow instructions literally in `/tmp`; capture first deterministic failure; change the smallest doc/sample line or dependency declaration; avoid changing product behavior unless example proves a product defect.
4. **Verify:** clean-environment rerun, exit code, expected output/assertion, syntax/lint/build for example, link/path validation, diff audit.
5. **Record:** exact runnable sequence, failure/recovery, output hash, files, manifest hash, metrics, retrieval effect, limitations and version assumptions.

## Outcomes and metrics

- **Success:** frozen example fails before and runs as documented after repair.
- **Partial:** a concrete defect is repaired but clean-environment or broader docs validation is incomplete.
- **Blocked:** credentials/service/large artifact required or documented result is subjective.
- **Failure:** repair does not make the literal example work.
- **Metrics:** setup commands, execution time, output hash, files/lines, tests, tokens/cost, retrieval score/capsule.
- **Stopping conditions:** >20 commands/30 minutes, hidden service requirement, large downloads, scope outside one example.
- **External approval later:** doc PR/comment, publish example/artifact, trigger docs build, candidate promotion.

## Next-pilot recommendation template

`Example path / literal failing command / expected output / version boundary / minimal edit / residual requirement / approval.`
