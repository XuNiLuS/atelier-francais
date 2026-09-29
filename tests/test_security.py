"""Vérifier l’échappement et les protections des fichiers statiques publiés."""

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from quiz_data import load_catalog, SECURITY_HEADERS
from scripts.export_static import export_site


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class StaticSecurityTests(unittest.TestCase):
    def test_injected_content_is_text_in_html_and_embedded_json(self):
        catalog = copy.deepcopy(load_catalog())
        attack = '</script><script id="xss-probe">alert("injection")</script>'
        quiz = catalog['4e-temps-recit']
        quiz['title'] = attack
        quiz['questions'][0]['before'] = attack
        quiz['questions'][0]['focus'] = '<img src=x onerror="alert(1)">'
        quiz['questions'][0]['options'][0]['label'] = '<svg onload="alert(2)">'
        quiz['questions'][0]['explanation'] = attack
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.export_static.load_catalog', return_value=catalog):
                export_site(directory)
            for page in Path(directory).rglob('*.html'):
                html = page.read_text(encoding='utf-8')
                self.assertNotIn(attack, html)
                parser = TagCollector()
                parser.feed(html)
                for tag, attrs in parser.tags:
                    self.assertNotEqual(attrs.get('id'), 'xss-probe')
                    self.assertFalse(any(name.lower().startswith('on') for name in attrs))
            html = (Path(directory) / 'quiz/4e-temps-recit/index.html').read_text(encoding='utf-8')
            match = re.search(r'<script type="application/json" id="quiz-data">(.*?)</script>', html, re.S)
            question = json.loads(match.group(1))['questions'][0]
            self.assertEqual(question['before'], attack)
            self.assertEqual(question['explanation'], attack)

    def test_all_pages_limit_resources_and_block_network_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            export_site(directory)
            for page in Path(directory).rglob('*.html'):
                parser = TagCollector()
                parser.feed(page.read_text(encoding='utf-8'))
                metas = [attrs for tag, attrs in parser.tags if tag == 'meta']
                csp = next(attrs['content'] for attrs in metas if attrs.get('http-equiv') == 'Content-Security-Policy')
                directives = dict(part.strip().split(None, 1) for part in csp.split(';') if part.strip())
                for name in ('default-src', 'connect-src', 'base-uri', 'form-action', 'object-src'):
                    self.assertEqual(directives[name], "'none'")
                self.assertNotIn('unsafe-inline', csp)
                self.assertNotIn('unsafe-eval', csp)
                self.assertTrue(any(attrs.get('name') == 'referrer' and attrs['content'] == 'no-referrer' for attrs in metas))
                for tag, attrs in parser.tags:
                    if tag in ('script', 'link'):
                        url = attrs.get('src') or attrs.get('href')
                        if url:
                            self.assertTrue(url.startswith('/static/'), url)
            headers = (Path(directory) / '_headers').read_text(encoding='utf-8')
            for name, value in SECURITY_HEADERS.items():
                self.assertIn(f'{name}: {value}', headers)


if __name__ == '__main__':
    unittest.main()
