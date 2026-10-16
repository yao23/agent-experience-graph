"""Small content/asset checks using the existing Python standard library."""
import hashlib
import html.parser
import pathlib
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_page import PACK, ROOT, build


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.copy_targets, self.assets = [], [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if "data-copy-target" in attrs:
            self.copy_targets.append(attrs["data-copy-target"])
        if "data-pack-copy" in attrs:
            self.copy_targets.extend([attrs["data-pack-copy"], attrs["data-shared-rules"]])
        if tag in ("link", "script"):
            self.assets.append(attrs.get("href", attrs.get("src", "")))


markdown = (PACK / "pack.md").read_text()
page_text = (PACK / "index.html").read_text()
assert page_text == build(), "Generated page differs from Markdown: run build_page.py"
assert hashlib.sha256(markdown.encode()).hexdigest() in page_text
ids = [f"R19-{i:02}" for i in range(1, 7)]
sections = re.findall(r"^## (R19-\d\d) · (.*?)(?=^## |\Z)", markdown, re.M | re.S)
assert [identifier for identifier, _ in sections] == ids
for identifier, content in sections:
    for field in ["When it applies", "What to check", "Agent instruction", "Decide the result", "Sources, versions, and limits"]:
        assert "### " + field in content, (identifier, field)
    for value in ["PASS", "FAIL", "NOT_APPLICABLE", "NOT_CHECKED", "2026-10-14", "source-backed guidance; not independently replayed", "https://"]:
        assert value in content, (identifier, value)
parser = Page()
parser.feed(page_text)
assert len(parser.ids) == len(set(parser.ids)), "Duplicate HTML IDs"
for target in parser.copy_targets:
    assert target[1:] in parser.ids
for link in parser.links + parser.assets:
    parsed = urlsplit(link)
    if parsed.scheme:
        assert parsed.scheme == "https"
        continue
    if parsed.path:
        target = PACK / parsed.path
        if target.is_dir():
            target /= "index.html"
        assert target.is_file(), link
    elif parsed.fragment:
        assert parsed.fragment in parser.ids, link
feedback = [link for link in parser.links if "/issues/new" in link]
assert feedback == ["https://github.com/yao23/agent-experience-graph/issues/new?template=learning-pack-feedback.yml"]
assert len(re.findall(r"data-pack-copy=", page_text)) == 6
assert len(re.findall(r"```text", markdown)) == 8
print("PASS: exact generated-page parity, six IDs/fields/statuses, dates/evidence labels, copy targets, relative paths/fragments, single feedback URL")
