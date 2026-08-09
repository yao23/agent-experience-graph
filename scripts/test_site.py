import html.parser
import pathlib
import unittest
from urllib.parse import urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = (
    ROOT / "index.html",
    ROOT / "pitch" / "index.html",
    ROOT / "docs" / "install-vscode-extension.html",
    ROOT / "docs" / "60-second-demo.html",
)


class PageParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.h1_count = 0
        self.stylesheets = []
        self.scripts = []
        self.has_main = False
        self.has_nav = False
        self.has_footer = False
        self.has_skip_link = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.h1_count += 1
        elif tag == "main":
            self.has_main = True
        elif tag == "nav" and attrs.get("aria-label") == "Primary navigation":
            self.has_nav = True
        elif tag == "footer":
            self.has_footer = True
        elif tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if attrs.get("class") == "skip-link":
                self.has_skip_link = True
        elif tag == "link" and attrs.get("rel") == "stylesheet":
            self.stylesheets.append(attrs.get("href"))
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])


def resolve_local(page, href):
    parsed = urlsplit(href)
    if parsed.scheme or href.startswith(("mailto:", "#")):
        return None
    target = (page.parent / parsed.path).resolve()
    if parsed.path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target


class SiteSmokeTest(unittest.TestCase):
    def parse(self, page):
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        return parser

    def test_pages_share_structure_and_assets(self):
        for page in PAGES:
            with self.subTest(page=page.relative_to(ROOT)):
                parsed = self.parse(page)
                self.assertEqual(parsed.h1_count, 1)
                self.assertTrue(parsed.has_main)
                self.assertTrue(parsed.has_nav)
                self.assertTrue(parsed.has_footer)
                self.assertTrue(parsed.has_skip_link)
                self.assertEqual(len(parsed.stylesheets), 1)
                self.assertTrue(parsed.stylesheets[0].endswith("site.css"))
                self.assertEqual(len(parsed.scripts), 1)
                self.assertTrue(parsed.scripts[0].endswith("site.js"))

    def test_internal_links_and_fragments_resolve(self):
        for page in PAGES:
            parsed = self.parse(page)
            for href in parsed.links:
                with self.subTest(page=page.relative_to(ROOT), href=href):
                    if href.startswith("#"):
                        self.assertIn(href[1:], parsed.ids)
                        continue
                    target = resolve_local(page, href)
                    if target is not None:
                        self.assertTrue(target.is_file(), f"missing {target}")

    def test_shared_assets_exist(self):
        self.assertTrue((ROOT / "site.css").is_file())
        self.assertTrue((ROOT / "site.js").is_file())
        self.assertTrue((ROOT / "favicon.svg").is_file())

    def test_design_partnership_contacts_use_reviewed_destination(self):
        destination = (
            "mailto:realcybermatrix@gmail.com?subject=AEG%20Design%20Partnership"
        )
        expected_counts = {
            ROOT / "index.html": 2,
            ROOT / "pitch" / "index.html": 2,
        }
        for page, expected_count in expected_counts.items():
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertEqual(self.parse(page).links.count(destination), expected_count)

    def test_fragment_targets_clear_sticky_header(self):
        css = (ROOT / "site.css").read_text(encoding="utf-8")
        self.assertIn("scroll-margin-top: 84px", css)


if __name__ == "__main__":
    unittest.main()
