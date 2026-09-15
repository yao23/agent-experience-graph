# AEG Verified Experience Registry

The Registry is a static, public evidence and reuse surface for recovery paths
that already have objective, public-safe verification. It is not a social
network, marketplace, hosted agent, execution service, or generic knowledge
base. Applying an experience remains BYO-Agent/BYOK and local to the user.

AEG's current design direction is **long working context, sparse external experience**. The Registry therefore serves two distinct consumers: a lightweight routing/index layer that decides whether an experience is worth loading, and a fuller evidence payload that is consulted only after selection. See [`docs/experience-routing.md`](experience-routing.md). This is an incremental design target rather than a claim that every current Registry surface already performs dynamic routing.

## Canonical source and generated surfaces

`experiences/registry.json` is the evolvable public Registry content source. Its schema is
`experiences/verified-experience.schema.json`, and
`scripts/validate_verified_experiences.py` enforces semantic, provenance,
timestamp, URL, redaction, uniqueness, and internal-reference integrity.

`experiences/verified.json` remains the byte-frozen library used by historical
autonomous-lab evidence and is not modified when the public Registry evolves.

`scripts/build_registry.py` safely escapes record content and generates:

- `/experiences/` — human-searchable Registry index;
- `/experiences/<slug>/` — stable human detail page;
- `/experiences/index.json` — machine-readable Registry index; and
- `/experiences/data/<slug>.json` — complete machine-readable Experience.

The generator also creates the Markdown and Agent-ready blocks shown on each
detail page. `python3 scripts/build_registry.py --check` fails when any human or
machine output diverges from the canonical data.

The initial corpus intentionally contains two records. Three other historical
work-queue candidates remain partial and are not promoted to reach an arbitrary
card count.

## Descriptor and payload model

For future dynamic retrieval, each experience should be separable conceptually into two layers.

The **experience descriptor** should be compact enough to rank or inspect without loading the full historical record. It should capture:

- a concise, narrow trigger;
- task/failure signatures or mechanism;
- applicability and exclusions;
- provenance / verification state / confidence;
- known staleness or negative-transfer risk when available.

The **full experience payload** may contain:

- failed approaches and why they failed;
- recovery principle or reusable lesson;
- evidence and verification method;
- constraints and environment/version context;
- validation outcome and measured regressions;
- limitations, stale conditions, and detailed provenance.

Existing records remain valid. Schema evolution for descriptors should remain backward-compatible until controlled experiments demonstrate that particular descriptor fields improve routing quality. The Registry should not make new mandatory fields merely because they sound useful.

The router must be able to abstain. A weak lexical match, broad trigger, or version-incompatible experience should not be forced into an agent's context.

## Measurement adapter

`site.js` exposes privacy-safe semantic events through both a DOM event and an
optional adapter. The default adapter is a no-op, so the site does not claim to
collect analytics and does not add a third-party analytics dependency.

To configure an approved analytics layer before `site.js` loads:

```html
<script>
  window.aegAnalytics = {
    track(name, properties) {
      // Send only the documented privacy-safe fields to an approved destination.
    },
  };
</script>
```

The same events are dispatched as `aeg:analytics` DOM events. Supported names
are:

- `experience_search` — query length, selected category/status, result count;
- `experience_view` — public Experience ID;
- `use_with_agent_copy` — public Experience ID;
- `json_download` — public Experience ID or Registry index;
- `replay_feedback_open` — public Experience ID or Registry index; and
- `experience_submission_open` — Registry context.

Search text is never included. The adapter must not add task text, code,
credentials, personal data, IP-derived identity, fingerprinting, or other
sensitive fields.

Meaningful product signals are non-founder retrieval, Agent-copy or JSON use,
external replay reports, successful reproduction, repeat use, external
Experience contribution, and private-team or paid-pilot interest. Page views,
likes, founder-only use, and compliments are not primary product-market-fit
evidence.

For dynamic-routing experiments, additional evidence should be recorded only when the experiment can measure it honestly: retrieval trigger count, relevant vs irrelevant retrievals, abstentions, harmful steering / negative transfer, and whether retrieval changed the repair path. Do not infer these metrics from a final successful outcome.

## Contributions and replay reports

GitHub Issue Forms capture candidate experiences, successful replays, and
failed/stale/incompatible replays. Every form requires environment and version
context, agent/model/harness context when known, objective verification
evidence, explicit unknowns for missing metrics, publication permission, and a
secret-removal confirmation.

Submissions must not contain credentials, proprietary code, personal data,
customer data, private paths, raw prompts, or other secrets. Submitted code is
never executed automatically.

## Local verification

```bash
python3 scripts/validate_verified_experiences.py
python3 scripts/build_registry.py --check
python3 -m unittest scripts.test_experience_registry scripts.test_site
node scripts/test_registry_client.js
```

## Versioned provenance extension

New archival work can include `provenance.record` v1.0.0 for attributable claims,
prior work, contributor roles, digest-addressed artifacts, external replay
reports and scoped licenses/consent. See [Provenance Record](provenance-record.md)
and the [consumer addendum](../coordination/PROVENANCE_ARCHIVAL.md).
Existing records remain valid; verification states are not automatically
promoted. The entire extension is preserved in exported machine JSON.
