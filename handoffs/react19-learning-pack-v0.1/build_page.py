"""Render this pack's small, explicit Markdown subset with the Python stdlib.

No runtime dependency or browser Markdown renderer. Run after editing pack.md.
"""
import hashlib
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACK = ROOT / "docs/react19-migration-pack"


def inline(value):
    value = html.escape(value)
    value = re.sub(r"\[([^\]]+)\]\((https://[^\s)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    return value


def slug(title):
    if title.startswith("R19-"):
        return title[:6].lower()
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def render(markdown):
    output, paragraph, code = [], [], None
    section_open, list_open = False, False
    block_number, active_check = 0, None

    def flush():
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_open
        if list_open:
            output.append("</ul>")
            list_open = False

    for line in markdown.splitlines():
        if code is not None:
            if line == "```":
                block_number += 1
                target = f"copy-block-{block_number}"
                text = "\n".join(code)
                # The copied brief is self-contained. Both parts remain visible
                # in the page and appear identically in the Markdown source.
                if active_check:
                    output.append(f'<button class="button" type="button" data-pack-copy="#{target}" data-shared-rules="#copy-block-1">Copy {active_check} agent brief</button>')
                else:
                    label = "shared agent rules" if block_number == 1 else "receipt template"
                    output.append(f'<button class="button" type="button" data-copy-target="#{target}">Copy {label}</button>')
                output.append(f'<pre id="{target}" tabindex="0"><code>{html.escape(text)}</code></pre>')
                code = None
            else:
                code.append(line)
            continue
        if line == "```text":
            flush()
            close_list()
            code = []
        elif line.startswith("# "):
            output.append("<h1>" + inline(line[2:]) + "</h1>")
        elif line.startswith("## "):
            flush()
            close_list()
            if section_open:
                output.append("</section>")
            title = line[3:]
            active_check = title[:6] if title.startswith("R19-") else None
            output.append(f'<section class="pack-section" id="{slug(title)}"><h2>{inline(title)}</h2>')
            section_open = True
        elif line.startswith("### "):
            flush()
            close_list()
            output.append("<h3>" + inline(line[4:]) + "</h3>")
        elif line.startswith("- "):
            flush()
            if not list_open:
                output.append("<ul>")
                list_open = True
            output.append("<li>" + inline(line[2:]) + "</li>")
        elif not line.strip():
            flush()
            close_list()
        else:
            paragraph.append(line)
    flush()
    close_list()
    if section_open:
        output.append("</section>")
    assert code is None, "Unclosed code block"
    assert block_number == 8, "Expected shared rules, six agent briefs and receipt"
    return "\n".join(output)


def build():
    markdown = (PACK / "pack.md").read_text()
    digest = hashlib.sha256(markdown.encode()).hexdigest()
    content = render(markdown)
    intro_end = content.index('<section class="pack-section"')
    intro, content = content[:intro_end], content[intro_end:]
    nav = "".join(f'<a href="#r19-{i:02}">R19-{i:02}</a>' for i in range(1, 7))
    template = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Six practical React 19 migration acceptance checks for developers and coding agents, with source links, agent briefs and honest result criteria.">
  <meta name="theme-color" content="#121b18">
  <meta name="pack-source-sha256" content="__DIGEST__">
  <title>React 19 Migration Acceptance Pack</title>
  <link rel="icon" href="../../favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../../site.css">
  <script src="../../site.js" defer></script>
  <style>
    .pack-shell { max-width: 1160px; }
    .pack-top { padding: 46px 0 0; }
    .pack-top .kicker { margin-bottom: 12px; }
    .pack-layout { display: grid; grid-template-columns: 185px minmax(0, 1fr); gap: 48px; align-items: start; padding: 36px 0 64px; }
    .pack-order { position: sticky; top: 94px; padding: 18px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
    .pack-order strong, .pack-order a { display: block; }
    .pack-order a { padding: 7px 0; text-underline-offset: 4px; }
    .pack-content { min-width: 0; max-width: 76ch; }
    .pack-content h1 { font-size: clamp(2.6rem, 5vw, 4.6rem); text-wrap: balance; }
    .pack-content > p:first-of-type { font-size: 1.25rem; color: var(--muted); }
    .pack-content p, .pack-content li { overflow-wrap: anywhere; }
    .pack-content h2 { font-size: clamp(1.85rem, 3vw, 2.6rem); line-height: 1.15; }
    .pack-content h3 { margin-top: 28px; line-height: 1.3; }
    .pack-content li { margin-bottom: 10px; }
    .pack-content a { text-underline-offset: 3px; }
    .pack-content pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: 20px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); font-size: .9rem; line-height: 1.6; }
    .pack-content pre, .pack-content pre code { color: var(--ink); }
    .pack-content .button { margin-top: 14px; }
    .pack-section { border-top: 1px solid var(--line); margin-top: 38px; padding-top: 32px; scroll-margin-top: 92px; }
    .pack-section[id^="r19-"] { border-top: 4px solid var(--ink); }
    .pack-status { min-height: 26px; margin: 12px 0 0; color: var(--ink-soft); }
    .pack-header-link { color: #fff; padding: 14px 0; }
    :focus-visible { outline: 3px solid #236a5a; outline-offset: 4px; }
    @media (max-width: 760px) {
      .pack-layout { grid-template-columns: minmax(0, 1fr); gap: 28px; padding-top: 24px; }
      .pack-order { position: static; display: flex; gap: 8px 18px; flex-wrap: wrap; }
      .pack-order strong { flex-basis: 100%; }
      .pack-order a { padding: 5px 0; }
      .pack-top { padding-top: 26px; }
      .pack-header-link { display: none; }
      .pack-content pre { padding: 14px; }
    }
    @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
    @media print { .site-header, .pack-top, .pack-order, button, .site-footer { display: none; } .pack-layout { display: block; } .pack-content { max-width: none; } }
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header"><nav class="nav-shell" aria-label="Primary navigation">
    <a class="brand" href="../../">Agent Experience Graph</a>
    <a class="pack-header-link" href="../../experiences/">Experiences</a>
  </nav></header>
  <main id="main">
  <div class="shell pack-shell pack-top">
    <p class="kicker">AEG / LEARNING PACK 0.1</p>
    <div class="pack-content">__INTRO__</div>
    <div class="actions"><a class="button accent" href="./pack.md" download="react19-migration-acceptance-pack-v0.1.md">Download Markdown</a><a class="button" href="#start-here">Start with applicability ↓</a></div>
    <p>Copy shared rules or a self-contained check brief. If clipboard access is unavailable, select the visible text and copy manually.</p>
    <p class="pack-status" role="status" aria-live="polite" data-copy-status></p>
  </div>
  <div class="shell pack-shell pack-layout">
    <nav class="pack-order" aria-label="Reading order"><strong>Read → check → record</strong><a href="#start-here">Start here</a>__NAV__<a href="#keep-a-local-receipt">Local receipt</a><a href="#share-what-happened">Share what happened</a></nav>
    <article class="pack-content">__CONTENT__</article>
  </div>
  </main>
  <footer class="site-footer"><div class="shell"><p>AEG · Learning pack v0.1 · Source-backed guidance; not independently replayed.</p><a href="#main">Back to top ↑</a></div></footer>
  <script>
    // A copied check includes the shared rules. No network call or telemetry.
    document.querySelectorAll('[data-pack-copy]').forEach((button) => {
      button.addEventListener('click', async () => {
        const rules = document.querySelector(button.dataset.sharedRules);
        const brief = document.querySelector(button.dataset.packCopy);
        const status = document.querySelector('[data-copy-status]');
        try {
          await navigator.clipboard.writeText(rules.textContent + '\\n\\n' + brief.textContent);
          status.textContent = 'Shared rules and selected check instruction copied.';
          const label = button.textContent;
          button.textContent = 'Copied';
          setTimeout(() => { button.textContent = label; }, 2200);
        } catch {
          status.textContent = 'Clipboard access is unavailable. Copy the shared rules in Start here, then the selected visible instruction manually.';
          button.textContent = 'Select and copy manually';
          brief.focus();
        }
      });
    });
  </script>
</body>
</html>
'''
    return template.replace("__DIGEST__", digest).replace("__NAV__", nav).replace("__INTRO__", intro).replace("__CONTENT__", content)


if __name__ == "__main__":
    (PACK / "index.html").write_text(build())
    print("Rendered docs/react19-migration-pack/index.html from pack.md")
