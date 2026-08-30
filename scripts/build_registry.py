#!/usr/bin/env python3
"""Generate the human and machine Registry surfaces from verified.json."""

import argparse
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "experiences" / "verified.json"
OUTPUT = ROOT / "experiences"
REPOSITORY = "https://github.com/yao23/agent-experience-graph"
SUBMIT_URL = f"{REPOSITORY}/issues/new?template=candidate-experience.yml"
REPLAY_SUCCESS_URL = f"{REPOSITORY}/issues/new?template=experience-replay-success.yml"
REPLAY_FAILURE_URL = f"{REPOSITORY}/issues/new?template=experience-replay-failure.yml"


def esc(value):
    return html.escape(str(value), quote=True)


def list_html(items, css_class="clean-list"):
    return f'<ul class="{css_class}">' + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def nav(prefix, current="experiences"):
    experiences_current = ' aria-current="page"' if current == "experiences" else ""
    return f"""
    <header class="site-header">
      <div class="nav-shell">
        <a class="brand" href="{prefix}" aria-label="Agent Experience Graph home"
          ><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span
          ><span>Agent Experience Graph</span></a
        ><button class="nav-toggle" type="button" aria-label="Open navigation"
          aria-expanded="false" aria-controls="site-nav" data-nav-toggle>☰</button>
        <nav class="site-nav" id="site-nav" aria-label="Primary navigation" data-site-nav>
          <a href="{prefix}">Product</a
          ><a href="{prefix}experiences/"{experiences_current}>Experiences</a
          ><a href="{prefix}pitch/">Pitch</a
          ><a href="{prefix}docs/install-vscode-extension.html">Install</a
          ><a class="nav-github" href="{REPOSITORY}">GitHub ↗</a>
        </nav>
      </div>
    </header>"""


def footer(prefix):
    return f"""
    <footer class="site-footer">
      <div class="shell footer-grid">
        <span>AEG · Evidence before reuse</span>
        <nav class="footer-links" aria-label="Footer navigation">
          <a href="{prefix}">Product</a><a href="{prefix}experiences/">Experiences</a
          ><a href="{SUBMIT_URL}" data-aeg-event="experience_submission_open">Contribute ↗</a>
        </nav>
      </div>
    </footer>"""


def page_head(title, description, prefix):
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(description)}" />
    <meta name="theme-color" content="#121b18" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{esc(title)}" />
    <meta name="twitter:description" content="{esc(description)}" />
    <title>{esc(title)}</title>
    <link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="{prefix}site.css?v=registry-mvp-2" />
    <script src="{prefix}site.js?v=registry-mvp-2" defer></script>
  </head>"""


def render_status(status):
    return status.replace("_", " ")


def build_search_blob(record):
    values = [
        record["title"],
        record["summary"],
        record["category"],
        record["verification_status"],
        *record["problem"]["symptoms"],
        *record["problem"]["error_signatures"],
        *record["recovery_steps"],
        *record["reuse"]["retrievalTags"],
    ]
    return " ".join(values).lower()


def render_index(records):
    categories = sorted({record["category"] for record in records})
    statuses = sorted({record["verification_status"] for record in records})
    cards = []
    for record in records:
        errors = record["problem"]["error_signatures"]
        error_line = errors[0] if errors else "No stable public-safe error signature recorded"
        cards.append(
            f"""
            <article class="experience-card" data-experience-card
              data-experience-id="{esc(record['id'])}"
              data-category="{esc(record['category'])}"
              data-status="{esc(record['verification_status'])}"
              data-search="{esc(build_search_blob(record))}">
              <div class="experience-card-meta">
                <span class="verification-badge status-{record['verification_status'].lower()}">
                  {esc(render_status(record['verification_status']))}
                </span>
                <span class="tag">{esc(record['category'])}</span>
              </div>
              <h2><a href="./{esc(record['slug'])}/" data-aeg-event="experience_view">{esc(record['title'])}</a></h2>
              <p>{esc(record['summary'])}</p>
              <dl class="card-facts">
                <div><dt>Error signal</dt><dd>{esc(error_line)}</dd></div>
                <div><dt>Last verified</dt><dd><time datetime="{esc(record['last_verified_at'])}">{esc(record['last_verified_at'][:10])}</time></dd></div>
              </dl>
              <div class="experience-card-footer">
                <span class="mono">{esc(record['id'])}</span>
                <a class="text-link" href="./{esc(record['slug'])}/" data-aeg-event="experience_view">Inspect evidence →</a>
              </div>
            </article>"""
        )

    category_options = "".join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in categories)
    status_options = "".join(
        f'<option value="{esc(value)}">{esc(render_status(value))}</option>' for value in statuses
    )
    last_updated = max(record["last_verified_at"] for record in records)[:10]
    return f"""{page_head('Verified Experience Registry — Agent Experience Graph', 'Search evidence-backed recovery paths, inspect their limits, and copy agent-ready guidance.', '../')}
  <body data-registry-index>
    <a class="skip-link" href="#main">Skip to content</a>
{nav('../')}
    <main id="main">
      <section class="registry-hero">
        <div class="shell registry-hero-grid">
          <div>
            <p class="kicker">AEG Verified Experience Registry</p>
            <h1>Search proven recovery paths before your agent repeats the same failure.</h1>
            <p class="lede">Inspect objective evidence, applicability limits, failed paths, and reusable instructions before applying a prior recovery.</p>
          </div>
          <aside class="registry-stat-panel" aria-label="Registry summary">
            <div><strong>{len(records)}</strong><span>published experiences</span></div>
            <div><strong>{len(categories)}</strong><span>failure categories</span></div>
            <div><strong>{esc(last_updated)}</strong><span>latest verification</span></div>
          </aside>
        </div>
      </section>
      <section class="registry-workspace" aria-labelledby="registry-results-heading">
        <div class="shell">
          <form class="registry-controls" role="search" aria-label="Search and filter verified experiences" data-registry-controls>
            <div class="search-field">
              <label for="experience-search">Search the evidence</label>
              <input id="experience-search" type="search" autocomplete="off"
                placeholder="Try an error, symptom, or recovery…" data-experience-search />
              <span class="field-hint">Titles, symptoms, exact errors, categories, and recovery steps</span>
            </div>
            <div class="filter-field">
              <label for="category-filter">Category</label>
              <select id="category-filter" data-category-filter>
                <option value="">All categories</option>{category_options}
              </select>
            </div>
            <div class="filter-field">
              <label for="status-filter">Verification</label>
              <select id="status-filter" data-status-filter>
                <option value="">All states</option>{status_options}
              </select>
            </div>
            <button class="button registry-reset" type="button" data-registry-reset>Reset</button>
          </form>
          <div class="registry-results-head">
            <div>
              <p class="kicker">Public evidence</p>
              <h2 id="registry-results-heading">Recovery paths</h2>
            </div>
            <p class="result-count" aria-live="polite"><strong data-result-count>{len(records)}</strong> <span data-result-label>experiences</span></p>
          </div>
          <p class="registry-empty-hint" data-empty-query-state>Showing the complete public Registry. Every record carries its limitations and objective evidence.</p>
          <div class="experience-grid" data-experience-grid>{''.join(cards)}</div>
          <section class="no-results" data-no-results hidden aria-live="polite">
            <span class="mono">NO MATCHING EXPERIENCE</span>
            <h2>No recovery path matches those filters.</h2>
            <p>Clear the filters, try the exact error text, or submit a sanitized candidate for review.</p>
            <div class="actions">
              <button class="button primary" type="button" data-registry-reset>Clear search</button>
              <a class="button" href="{SUBMIT_URL}" data-aeg-event="experience_submission_open">Submit a candidate ↗</a>
            </div>
          </section>
          <section class="registry-contribute">
            <div>
              <p class="kicker">Improve the evidence</p>
              <h2>Replay one path—or contribute another.</h2>
              <p>GitHub submissions are reviewed and sanitized. Never include credentials, proprietary code, personal data, customer data, or other secrets. Submitted code is not executed automatically.</p>
            </div>
            <div class="registry-contribute-actions">
              <a class="button accent" href="{SUBMIT_URL}" data-aeg-event="experience_submission_open">Submit an experience ↗</a>
              <a class="button" href="{REPLAY_SUCCESS_URL}" data-aeg-event="replay_feedback_open">Report a successful replay ↗</a>
              <a class="button" href="{REPLAY_FAILURE_URL}" data-aeg-event="replay_feedback_open">Report failure or staleness ↗</a>
              <a class="text-link" href="./index.json" data-aeg-event="json_download">Open Registry JSON →</a>
            </div>
          </section>
        </div>
      </section>
    </main>
{footer('../')}
  </body>
</html>
"""


def markdown_for(record):
    def bullets(items):
        return "\n".join(f"- {item}" for item in items)

    errors = record["problem"]["error_signatures"] or ["Unknown: no stable public-safe error signature was recorded."]
    attempts = "\n".join(
        f"{index}. **{item['approach']}**\n   - Observed: {item['observed_result']}\n   - Why it failed: {item['why_failed']}"
        for index, item in enumerate(record["failed_attempts"], 1)
    )
    steps = "\n".join(f"{index}. {step}" for index, step in enumerate(record["recovery_steps"], 1))
    metrics = "\n".join(
        f"- {name.replace('_', ' ').title()}: "
        + (str(metric["value"]) if metric["value"] is not None else "Unknown")
        + f" {metric['unit']} — {metric['note']}"
        for name, metric in record["registry_metrics"].items()
    )
    return f"""# {record['title']}

- Experience ID: `{record['id']}`
- Verification: `{record['verification_status']}`
- Category: {record['category']}
- Last verified: {record['last_verified_at']}

{record['summary']}

## Symptoms

{bullets(record['problem']['symptoms'])}

## Exact error signatures

{bullets(errors)}

## Apply when

{bullets(record['applicability']['applies_when'])}

## Do not apply when

{bullets(record['applicability']['exclusions'])}

## Known limitations

{bullets(record['limitations'])}

## Environment and agent context

- Language: {record['context']['environment_fingerprint']['language']}
- Runtime: {record['context']['environment_fingerprint']['runtime']}
- Operating system: {record['context']['environment_fingerprint']['operating_system']}
- Dependencies: {', '.join(record['context']['environment_fingerprint']['dependencies'])}
- Agent: {record['context']['agent_context']['agent']}
- Model: {record['context']['agent_context']['model']}
- Harness: {record['context']['agent_context']['harness']}
- Reasoning context: {record['context']['agent_context']['reasoning']}

## Failed approaches

{attempts}

## Verified recovery

{steps}

## Verification

{record['verification_method']['summary']}

{bullets(record['verification_method']['checks'])}

## Metrics

{metrics}

## Agent-ready instructions

{record['agent_ready_instructions']}

## Provenance

- Source: {record['context']['repository']}
- Revision: `{record['context']['source_revision']['commit_sha']}`
- License: {record['license']}
"""


def format_metric(metric):
    if metric["value"] is None:
        return "Unknown"
    value = metric["value"]
    return f"{value:+}" if value != 0 else "0"


def render_detail(record):
    prefix = "../../"
    errors = record["problem"]["error_signatures"]
    errors_html = list_html(errors) if errors else '<p class="unknown-value">Unknown — no stable public-safe signature was recorded.</p>'
    environment = record["context"]["environment_fingerprint"]
    agent = record["context"]["agent_context"]
    dependency_items = "".join(f"<li>{esc(item)}</li>" for item in environment["dependencies"])
    attempts = "".join(
        f"""<article class="attempt-card"><span class="attempt-index">FAILED PATH {index:02d}</span>
        <h3>{esc(item['approach'])}</h3><p><strong>Observed:</strong> {esc(item['observed_result'])}</p>
        <p><strong>Why it failed:</strong> {esc(item['why_failed'])}</p></article>"""
        for index, item in enumerate(record["failed_attempts"], 1)
    )
    steps = "".join(
        f'<li><span>{index:02d}</span><p>{esc(step)}</p></li>'
        for index, step in enumerate(record["recovery_steps"], 1)
    )
    metrics = "".join(
        f"""<article class="registry-metric"><span>{esc(name.replace('_', ' '))}</span>
        <strong>{esc(format_metric(metric))}</strong><small>{esc(metric['unit'])}</small>
        <p>{esc(metric['note'])}</p></article>"""
        for name, metric in record["registry_metrics"].items()
    )
    evidence = "".join(
        f'<li><a href="{prefix}{esc(path)}">{esc(path)}</a></li>' for path in record["verification_method"]["evidence_refs"]
    )
    markdown = markdown_for(record)
    json_text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    return f"""{page_head(record['title'] + ' — AEG Verified Experience', record['summary'], prefix)}
  <body data-experience-detail data-experience-id="{esc(record['id'])}">
    <a class="skip-link" href="#main">Skip to content</a>
{nav(prefix)}
    <main id="main">
      <article>
        <header class="experience-hero">
          <div class="shell">
            <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Experiences</a><span aria-hidden="true">/</span><span>{esc(record['id'])}</span></nav>
            <div class="experience-card-meta">
              <span class="verification-badge status-{record['verification_status'].lower()}">{esc(render_status(record['verification_status']))}</span>
              <span class="tag">{esc(record['category'])}</span>
            </div>
            <h1>{esc(record['title'])}</h1>
            <p class="lede">{esc(record['summary'])}</p>
            <div class="experience-primary-actions">
              <button class="button accent" type="button" data-copy-target="#agent-instructions" data-copy-event="use_with_agent_copy">Use with Agent</button>
              <a class="button" href="../data/{esc(record['slug'])}.json" download data-aeg-event="json_download">Download JSON ↓</a>
              <a class="button" href="{REPLAY_SUCCESS_URL}" data-aeg-event="replay_feedback_open">Report replay ↗</a>
            </div>
            <p class="copy-status" aria-live="polite" data-copy-status></p>
          </div>
        </header>

        <section class="detail-section">
          <div class="shell detail-layout">
            <div class="detail-main">
              <section aria-labelledby="problem-heading">
                <p class="kicker">Problem</p><h2 id="problem-heading">Symptoms and error signature</h2>
                {list_html(record['problem']['symptoms'])}
                <div class="signature-block"><h3>Exact public-safe error</h3>{errors_html}</div>
              </section>
              <section aria-labelledby="applicability-heading">
                <p class="kicker">Applicability</p><h2 id="applicability-heading">Check the boundary before reuse</h2>
                <div class="boundary-grid"><div><h3>Apply when</h3>{list_html(record['applicability']['applies_when'])}</div>
                <div class="boundary-warning"><h3>Do not apply when</h3>{list_html(record['applicability']['exclusions'])}</div>
                <div class="boundary-limitations"><h3>Known limitations</h3>{list_html(record['limitations'])}</div></div>
              </section>
              <section aria-labelledby="failed-heading">
                <p class="kicker">Failed approaches</p><h2 id="failed-heading">What did not work—and why</h2>
                <div class="attempt-grid">{attempts}</div>
              </section>
              <section aria-labelledby="recovery-heading">
                <p class="kicker">Verified recovery</p><h2 id="recovery-heading">Recovery steps</h2>
                <ol class="recovery-list">{steps}</ol>
              </section>
              <section aria-labelledby="verification-heading">
                <p class="kicker">Verification</p><h2 id="verification-heading">Method and objective evidence</h2>
                <p class="section-intro">{esc(record['verification_method']['summary'])}</p>
                {list_html(record['verification_method']['checks'])}
                <details class="evidence-details"><summary>Evidence references</summary><ul>{evidence}</ul></details>
              </section>
              <section aria-labelledby="metrics-heading">
                <p class="kicker">Observed metrics</p><h2 id="metrics-heading">Measured values and explicit unknowns</h2>
                <div class="registry-metric-grid">{metrics}</div>
              </section>
            </div>
            <aside class="detail-sidebar" aria-label="Experience context">
              <div class="sticky-evidence-card">
                <span class="mono">{esc(record['id'])}</span>
                <dl class="context-list">
                  <div><dt>Status</dt><dd>{esc(render_status(record['verification_status']))}</dd></div>
                  <div><dt>Last verified</dt><dd><time datetime="{esc(record['last_verified_at'])}">{esc(record['last_verified_at'][:10])}</time></dd></div>
                  <div><dt>Language</dt><dd>{esc(environment['language'])}</dd></div>
                  <div><dt>Runtime</dt><dd>{esc(environment['runtime'])}</dd></div>
                  <div><dt>OS</dt><dd>{esc(environment['operating_system'])}</dd></div>
                  <div><dt>Dependencies</dt><dd><ul class="context-dependencies">{dependency_items}</ul></dd></div>
                  <div><dt>Agent</dt><dd>{esc(agent['agent'])}</dd></div>
                  <div><dt>Model</dt><dd>{esc(agent['model'])}</dd></div>
                  <div><dt>Harness</dt><dd>{esc(agent['harness'])}</dd></div>
                  <div><dt>Reasoning</dt><dd>{esc(agent['reasoning'])}</dd></div>
                  <div><dt>Source version</dt><dd>{esc(record['context']['source_revision']['version'])}</dd></div>
                  <div><dt>License</dt><dd>{esc(record['license'])}</dd></div>
                </dl>
                <a class="text-link" href="{esc(record['context']['repository'])}">Open public source ↗</a>
                <p class="revision">Revision <code>{esc(record['context']['source_revision']['commit_sha'])}</code></p>
              </div>
            </aside>
          </div>
        </section>

        <section class="consumption-section" aria-labelledby="consumption-heading">
          <div class="shell">
            <p class="kicker">Agent consumption</p><h2 id="consumption-heading">Copy the evidence in the format you need</h2>
            <p class="section-intro">The page, Markdown, and JSON are generated from the same canonical record. Applying an experience remains a local, BYO-Agent decision.</p>
            <div class="format-tabs" data-tabs>
              <div class="tab-list" role="tablist" aria-label="Experience formats">
                <button type="button" role="tab" aria-selected="true" aria-controls="agent-panel" id="agent-tab" data-tab-target="#agent-panel">Agent instructions</button>
                <button type="button" role="tab" aria-selected="false" aria-controls="markdown-panel" id="markdown-tab" data-tab-target="#markdown-panel" tabindex="-1">Markdown</button>
                <button type="button" role="tab" aria-selected="false" aria-controls="json-panel" id="json-tab" data-tab-target="#json-panel" tabindex="-1">JSON</button>
              </div>
              <section role="tabpanel" id="agent-panel" aria-labelledby="agent-tab" data-tab-panel>
                <div class="code-toolbar"><span>AGENT-READY INSTRUCTIONS</span><button type="button" data-copy-target="#agent-instructions" data-copy-event="use_with_agent_copy">Copy instructions</button></div>
                <pre id="agent-instructions" tabindex="0"><code>{esc(record['agent_ready_instructions'])}</code></pre>
              </section>
              <section role="tabpanel" id="markdown-panel" aria-labelledby="markdown-tab" data-tab-panel hidden>
                <div class="code-toolbar"><span>MARKDOWN</span><button type="button" data-copy-target="#experience-markdown">Copy Markdown</button></div>
                <pre id="experience-markdown" tabindex="0"><code>{esc(markdown)}</code></pre>
              </section>
              <section role="tabpanel" id="json-panel" aria-labelledby="json-tab" data-tab-panel hidden>
                <div class="code-toolbar"><span>MACHINE-READABLE JSON</span><div><button type="button" data-copy-target="#experience-json">Copy JSON</button><a href="../data/{esc(record['slug'])}.json" download data-aeg-event="json_download">Download</a></div></div>
                <pre id="experience-json" tabindex="0"><code>{esc(json_text)}</code></pre>
              </section>
            </div>
          </div>
        </section>
      </article>
    </main>
{footer(prefix)}
  </body>
</html>
"""


def registry_index(records):
    return {
        "schema_version": "1.0.0",
        "last_updated_at": max(record["last_verified_at"] for record in records),
        "experience_count": len(records),
        "experiences": [
            {
                "schema_version": record["schema_version"],
                "id": record["id"],
                "slug": record["slug"],
                "title": record["title"],
                "summary": record["summary"],
                "category": record["category"],
                "verification_status": record["verification_status"],
                "source_version": record["provenance"]["sourceVersion"],
                "last_verified_at": record["last_verified_at"],
                "detail_url": f"/experiences/{record['slug']}/",
                "json_url": f"/experiences/data/{record['slug']}.json",
            }
            for record in records
        ],
    }


def expected_outputs(records):
    outputs = {
        OUTPUT / "index.html": render_index(records),
        OUTPUT / "index.json": json.dumps(registry_index(records), indent=2, ensure_ascii=False) + "\n",
    }
    for record in records:
        outputs[OUTPUT / record["slug"] / "index.html"] = render_detail(record)
        outputs[OUTPUT / "data" / f"{record['slug']}.json"] = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when generated output differs")
    args = parser.parse_args()
    records = json.loads(LIBRARY.read_text(encoding="utf-8"))
    outputs = expected_outputs(records)
    stale = []
    for path, expected in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if stale:
        raise SystemExit("stale Registry output: " + ", ".join(stale))
    action = "checked" if args.check else "generated"
    print(json.dumps({"status": "passed", "action": action, "experience_count": len(records), "output_count": len(outputs)}))


if __name__ == "__main__":
    main()
