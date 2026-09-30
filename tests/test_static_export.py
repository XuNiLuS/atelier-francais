"""Contrôler le site exporté, ses liens et son contenu public sans serveur Python."""

import json
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit

from scripts.export_static import export_site
from quiz_data import load_catalog


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src"):
                self.urls.append(value)


class StaticExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "site"

    def test_export_at_root_and_repository_path_has_no_broken_internal_links(self):
        for prefix in ("", "/atelier-francais"):
            result = export_site(self.output, prefix)
            self.assertEqual(result["quizzes"], len(load_catalog()))
            self.assertEqual(result["pages"], len(load_catalog()) + 6)
            for page in self.output.rglob("*.html"):
                parser = Links()
                parser.feed(page.read_text())
                for url in parser.urls:
                    if url.startswith("#") or urlsplit(url).scheme:
                        continue
                    with self.subTest(page=page, url=url):
                        self.assertTrue(url.startswith(prefix + "/"))
                        relative = urlsplit(url).path[len(prefix):].lstrip("/")
                        target = self.output / relative
                        if target.is_dir():
                            target /= "index.html"
                        self.assertTrue(target.is_file(), target)

    def test_public_bundle_contains_only_generated_pages_and_public_assets(self):
        export_site(self.output)
        self.assertFalse((self.output / "quiz_data.py").exists())
        self.assertFalse((self.output / "data").exists())
        self.assertFalse((self.output / ".git").exists())
        self.assertFalse((self.output / "reports").exists())
        self.assertEqual({p.name for p in (self.output / "static").iterdir()}, {"app.js", "navigation.js", "style.css", "favicon.svg"})

    def test_each_static_quiz_contains_its_own_twenty_explained_corrections(self):
        export_site(self.output)
        for page in (self.output / "quiz").glob("*/index.html"):
            html = page.read_text()
            match = re.search(r'<script type="application/json" id="quiz-data">(.*?)</script>', html, re.S)
            quiz = json.loads(match.group(1))
            self.assertEqual(quiz["id"], page.parent.name)
            self.assertEqual(len(quiz["questions"]), 20)
            for question in quiz["questions"]:
                self.assertIn(question["answer"], "abcd")
                self.assertTrue(question["explanation"].strip())
            self.assertIn('http-equiv="Content-Security-Policy"', html)
            self.assertNotIn("unsafe-inline", html)

    def test_reexport_removes_obsolete_generated_pages(self):
        export_site(self.output)
        obsolete = self.output / "obsolete.html"
        obsolete.write_text("Ancien quiz")
        export_site(self.output)
        self.assertFalse(obsolete.exists())
        self.assertTrue((self.output / "index.html").exists())

    def test_export_does_not_overwrite_an_unrelated_directory(self):
        self.output.mkdir()
        document = self.output / "important.txt"
        document.write_text("À conserver")
        with self.assertRaises(ValueError):
            export_site(self.output)
        self.assertEqual(document.read_text(), "À conserver")

    def test_export_rejects_unsafe_url_prefixes(self):
        for prefix in ("https://example.org", "//example.org", "/../private", '/quiz" onload="evil'):
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    export_site(self.output, prefix)


if __name__ == "__main__":
    unittest.main()
