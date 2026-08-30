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
    ROOT / "experiences" / "index.html",
    *sorted((ROOT / "experiences").glob("*/index.html")),
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
                self.assertTrue(urlsplit(parsed.stylesheets[0]).path.endswith("site.css"))
                self.assertEqual(len(parsed.scripts), 1)
                self.assertTrue(urlsplit(parsed.scripts[0]).path.endswith("site.js"))

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
        homepage = ROOT / "index.html"
        pitch = ROOT / "pitch" / "index.html"
        expected_destinations = {
            homepage: (
                "mailto:realcybermatrix@gmail.com?subject=AEG%20Design%20Partnership"
            ),
            pitch: (
                "mailto:realcybermatrix@gmail.com?subject="
                "AEG%20Design%20Partner%20Experiment"
            ),
        }
        for page, destination in expected_destinations.items():
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertEqual(self.parse(page).links.count(destination), 2)

    def test_pitch_preserves_required_evidence_and_thesis_boundaries(self):
        pitch_html = (ROOT / "pitch" / "index.html").read_text(encoding="utf-8")
        pitch_copy = " ".join(pitch_html.split())
        required_copy = (
            "Verified experience for the",
            "AEG helps agents repeatedly improve through verified execution",
            "Median assisted runs used one fewer completed command.",
            "Five pairs; all ten arms passed objective verification",
            "No success gain; median latency regressed 18,235 ms",
            "From Superintelligence to Distributed Intelligence",
            "learning locally and sharing selectively",
            "Verified situated experience",
            "THESIS, NOT YET PRODUCT EVIDENCE",
            "CONTEXT / RAG",
            "Unlike generic memory, AEG keeps provenance and a verified outcome attached",
            "Capture, validation, and retrieval are shipped. Benefit remains bounded.",
            "public and license-compatible, explicitly authorized, or synthetic",
            "Any retained evidence will be sanitized.",
            "Under the merged Stage A approval record",
            "outreach is authorized for up to three voluntary seed participants",
            "public recruitment budget currently records 0 invitations and 0 enrolled participants",
            "Task execution and AEG-assisted testing remain unauthorized.",
            "Bring one reproducible task",
            "Not a generic marketplace or agent orchestrator",
            "No LangSmith replacement claim",
        )
        for copy in required_copy:
            with self.subTest(copy=copy):
                self.assertIn(copy, pitch_copy)

        distributed = pitch_html.index('id="distributed-intelligence"')
        evidence = pitch_html.index('id="evidence"')
        self.assertLess(distributed, evidence)

    def test_pitch_avoids_unsupported_public_claims(self):
        pitch = (ROOT / "pitch" / "index.html").read_text(encoding="utf-8").lower()
        unsupported_copy = (
            "billions of users",
            "proven cross-project",
            "proven customer demand",
            "product-market fit exists",
            "replaces langsmith",
            "global reputation score",
            "retrieval benefit is proven",
            "we have design partners",
            "active design partner",
            "customer adoption exists",
        )
        for copy in unsupported_copy:
            with self.subTest(copy=copy):
                self.assertNotIn(copy, pitch)

    def test_mobile_evidence_rows_expose_claim_boundaries(self):
        pitch = (ROOT / "pitch" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "site.css").read_text(encoding="utf-8")
        self.assertEqual(pitch.count('data-label="Claim"'), 5)
        self.assertEqual(pitch.count('data-label="Repository evidence"'), 5)
        self.assertEqual(pitch.count('data-label="Boundary"'), 5)
        self.assertIn(".evidence-table td::before", css)
        self.assertIn("content: attr(data-label)", css)
        self.assertIn(".evidence-table tbody", css)

    def test_fragment_targets_clear_sticky_header(self):
        css = (ROOT / "site.css").read_text(encoding="utf-8")
        self.assertIn("scroll-margin-top: 84px", css)

    def test_primary_navigation_exposes_registry(self):
        for page in PAGES:
            with self.subTest(page=page.relative_to(ROOT)):
                links = self.parse(page).links
                self.assertTrue(
                    any("experiences/" in link for link in links),
                    f"Registry missing from {page}",
                )


if __name__ == "__main__":
    unittest.main()
