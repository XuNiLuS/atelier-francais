"""Vérifier l’échappement et les protections des fichiers statiques publiés."""

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from quiz_data import (
    ANALYTICS_NETWORK_SOURCES, GOOGLE_TAG_SOURCE, META_CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS, load_analytics_config, load_catalog,
)
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
            analytics = re.search(r'<script type="application/json" id="analytics-config">(.*?)</script>', html, re.S)
            self.assertIsNotNone(analytics)
            self.assertEqual(json.loads(analytics.group(1))['quiz_theme'], attack)

    def test_all_pages_limit_network_to_explicit_analytics_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            export_site(directory)
            for page in Path(directory).rglob('*.html'):
                parser = TagCollector()
                parser.feed(page.read_text(encoding='utf-8'))
                metas = [attrs for tag, attrs in parser.tags if tag == 'meta']
                csp = next(attrs['content'] for attrs in metas if attrs.get('http-equiv') == 'Content-Security-Policy')
                directives = dict(part.strip().split(None, 1) for part in csp.split(';') if part.strip())
                for name in ('default-src', 'base-uri', 'form-action', 'object-src'):
                    self.assertEqual(directives[name], "'none'")
                self.assertEqual(csp, META_CONTENT_SECURITY_POLICY)
                self.assertNotIn('frame-ancestors', directives)
                self.assertEqual(set(directives['script-src'].split()), {"'self'", GOOGLE_TAG_SOURCE})
                self.assertEqual(set(directives['connect-src'].split()), set(ANALYTICS_NETWORK_SOURCES))
                self.assertEqual(set(directives['img-src'].split()), {"'self'", *ANALYTICS_NETWORK_SOURCES})
                self.assertEqual(directives['style-src'], "'self'")
                self.assertNotIn('unsafe-inline', csp)
                self.assertNotIn('unsafe-eval', csp)
                self.assertNotIn('*', csp)
                self.assertTrue(any(attrs.get('name') == 'referrer' and attrs['content'] == 'no-referrer' for attrs in metas))
                for tag, attrs in parser.tags:
                    if tag in ('script', 'link', 'img', 'iframe', 'source'):
                        url = attrs.get('src') or attrs.get('href')
                        if url:
                            self.assertTrue(url.startswith('/static/'), url)
            headers = (Path(directory) / '_headers').read_text(encoding='utf-8')
            for name, value in SECURITY_HEADERS.items():
                self.assertIn(f'{name}: {value}', headers)

    def test_caddy_and_static_headers_use_the_same_csp(self):
        caddy = (Path(__file__).resolve().parents[1] / 'Caddyfile').read_text(encoding='utf-8')
        self.assertIn(f'Content-Security-Policy "{SECURITY_HEADERS["Content-Security-Policy"]}"', caddy)
        self.assertIn("frame-ancestors 'none'", SECURITY_HEADERS['Content-Security-Policy'])

    def test_analytics_config_accepts_an_empty_or_ga4_id(self):
        config = {'measurement_id': '', 'production_origin': 'https://xunilus.github.io', 'base_path': '/atelier-francais'}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            for measurement_id, base_path in (('', '/atelier-francais'), ('G-ABC123', '')):
                expected = {**config, 'measurement_id': measurement_id, 'base_path': base_path}
                path.write_text(json.dumps(expected), encoding='utf-8')
                self.assertEqual(load_analytics_config(path), expected)

    def test_analytics_config_rejects_unsafe_or_ambiguous_values(self):
        valid = {'measurement_id': '', 'production_origin': 'https://xunilus.github.io', 'base_path': '/atelier-francais'}
        invalid = [[], {}, {**valid, 'extra': 'unexpected'}]
        bad_values = {
            'measurement_id': (None, 123, 'UA-123', 'G-', 'g-ABC', 'G-abc', 'G-ABC\n', 'G-ABC?x=1', '</script>'),
            'production_origin': (
                None, 'http://example.org', 'https://example.org/', 'https://example.org/path',
                'https://user@example.org', 'https://example.org:443', 'https://example.org?x=1',
                'https://example.org#fragment', 'https://EXAMPLE.org', 'https://example..org',
                'https://-example.org', 'https://localhost', 'https://127.0.0.1',
                'https://example.org\n', '//example.org',
            ),
            'base_path': (None, '/', '/atelier-francais/', '//example.org', '/a/../b', '/a/./b',
                          '/a//b', '/%2e%2e/private', '/a?x=1', '/a#fragment', '/a\\b', '/a\n'),
        }
        for field, values in bad_values.items():
            invalid.extend({**valid, field: value} for value in values)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            for config in invalid:
                with self.subTest(config=config):
                    path.write_text(json.dumps(config), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        load_analytics_config(path)


if __name__ == '__main__':
    unittest.main()
