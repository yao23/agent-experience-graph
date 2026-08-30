# AEG Verified Experience Registry

The Registry is a static, public evidence and reuse surface for recovery paths
that already have objective, public-safe verification. It is not a social
network, marketplace, hosted agent, execution service, or generic knowledge
base. Applying an experience remains BYO-Agent/BYOK and local to the user.

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
