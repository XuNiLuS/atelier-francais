"""Vérifications de sécurité locales, sans serveur public ni service externe."""

import asyncio
import copy
from html.parser import HTMLParser
import json
import os
import re
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as quiz_app


EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cross-origin-resource-policy": "same-origin",
}
EXPECTED_CSP = {
    "default-src": "'none'",
    "script-src": "'self'",
    "style-src": "'self'",
    "img-src": "'self'",
    "connect-src": "'self'",
    "base-uri": "'none'",
    "form-action": "'none'",
    "frame-ancestors": "'none'",
    "object-src": "'none'",
}


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SecurityAssertions:
    def assert_security_headers(self, headers):
        for key, expected in EXPECTED_HEADERS.items():
            self.assertEqual(headers.get(key), expected, key)
        csp = headers.get("content-security-policy", "")
        directives = dict(
            directive.strip().split(None, 1)
            for directive in csp.split(";") if directive.strip()
        )
        for key, expected in EXPECTED_CSP.items():
            self.assertEqual(directives.get(key), expected, key)
        self.assertNotIn("'unsafe-inline'", csp)
        self.assertNotIn("'unsafe-eval'", csp)


class SecurityTests(SecurityAssertions, unittest.TestCase):
    def setUp(self):
        self.app = quiz_app.create_app(allowed_hosts=["localhost", "127.0.0.1"])
        self.client = TestClient(
            self.app, base_url="http://localhost", raise_server_exceptions=False
        )
        self.addCleanup(self.client.close)

    def test_security_headers_cover_pages_assets_health_and_errors(self):
        for path, status in (
            ("/", 200), ("/health", 200), ("/static/app.js", 200),
            ("/static/style.css", 200), ("/does-not-exist", 404),
            ("/api/check", 405),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status)
                self.assert_security_headers(response.headers)

    def test_security_headers_cover_api_success_validation_and_size_limit(self):
        for content, status in (
            ('{"question_id":1,"answer":"a"}', 200),
            ('{"question_id":true,"answer":"a"}', 400),
            ('{"question_id":', 400),
            (" " * (quiz_app.MAX_BODY_SIZE + 1), 400),
        ):
            with self.subTest(status=status, size=len(content)):
                response = self.client.post(
                    "/api/check", content=content,
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers.get("Cache-Control"), "no-store")
                self.assert_security_headers(response.headers)

    def test_unknown_hosts_cannot_poison_pages_or_redirects(self):
        for host in ("attacker.example", "localhost.attacker.example", "www.localhost"):
            for path in ("/", "/api/check/"):
                with self.subTest(host=host, path=path):
                    response = self.client.get(
                        path, headers={"Host": host}, follow_redirects=False
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertNotIn("location", response.headers)
                    self.assertNotIn(host, response.text)
                    self.assert_security_headers(response.headers)

    def test_local_hosts_work_with_ports(self):
        for host in ("localhost", "localhost:8000", "127.0.0.1:8000"):
            with self.subTest(host=host):
                self.assertEqual(
                    self.client.get("/", headers={"Host": host}).status_code, 200
                )

    def test_public_host_can_be_configured_from_environment(self):
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "quiz.example.org, localhost"}):
            configured_app = quiz_app.create_app()
        with TestClient(configured_app, base_url="https://quiz.example.org") as client:
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/", headers={"Host": "localhost"}).status_code, 200)
            self.assertEqual(client.get("/", headers={"Host": "attacker.example"}).status_code, 400)

    def test_static_resources_use_relative_urls_and_ignore_forwarded_host(self):
        response = self.client.get("/", headers={
            "X-Forwarded-Host": "attacker.example",
            "X-Forwarded-Proto": "https",
        })
        parser = TagCollector()
        parser.feed(response.text)
        asset_urls = [
            attrs.get("src") if tag == "script" else attrs.get("href")
            for tag, attrs in parser.tags
            if tag == "link" or (tag == "script" and "src" in attrs)
        ]
        self.assertEqual(set(asset_urls), {
            "/static/favicon.svg", "/static/style.css", "/static/app.js",
        })
        self.assertNotIn("attacker.example", response.text)

    def test_interactive_documentation_is_not_public(self):
        for path in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("cdn.jsdelivr", response.text)

    def test_source_secrets_and_static_traversal_are_not_served(self):
        for path in (
            "/.git/config", "/.env", "/app.py", "/requirements.txt",
            "/data/questions.json", "/templates/index.html",
            "/static/%2e%2e/app.py", "/static/..%2fapp.py",
            "/static/%2e%2e%2fdata%2fquestions.json", "/static/%2fetc/passwd",
            "/static/%00",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("Traceback", response.text)
                self.assertNotIn(str(quiz_app.BASE_DIR), response.text)

    def test_html_and_json_question_data_cannot_create_executable_tags(self):
        questions = copy.deepcopy(quiz_app.load_questions())
        attack = '</script><script id="xss-probe">alert("injection")</script>'
        questions[0]["before"] = attack
        questions[0]["verb"] = '<img src=x onerror="alert(1)">'
        questions[0]["options"][0]["label"] = '<svg onload="alert(2)">'
        with patch.object(quiz_app, "load_questions", return_value=questions):
            injected_app = quiz_app.create_app(allowed_hosts=["localhost"])
        with TestClient(injected_app, base_url="http://localhost") as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(attack, response.text)
        parser = TagCollector()
        parser.feed(response.text)
        for tag, attrs in parser.tags:
            self.assertNotEqual(attrs.get("id"), "xss-probe")
            self.assertNotIn("onerror", attrs)
            self.assertNotIn("onload", attrs)
        embedded = re.search(
            r'<script type="application/json" id="quiz-data">(.*?)</script>',
            response.text, re.DOTALL,
        )
        self.assertIsNotNone(embedded)
        decoded = json.loads(embedded.group(1))
        self.assertEqual(decoded[0]["before"], attack)
        self.assertEqual(decoded[0]["verb"], questions[0]["verb"])

    def test_unexpected_errors_do_not_leak_details(self):
        private_detail = "private-database-password /home/teacher/secret.py"
        with self.assertLogs("app", level="ERROR"):
            with patch.object(quiz_app, "answer_result", side_effect=RuntimeError(private_detail)):
                response = self.client.post(
                    "/api/check", json={"question_id": 1, "answer": "a"}
                )
        self.assertEqual(response.status_code, 500)
        self.assertIsInstance(response.json().get("error"), str)
        for private_text in (private_detail, "RuntimeError", "Traceback"):
            self.assertNotIn(private_text, response.text)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assert_security_headers(response.headers)

    def test_requests_do_not_create_sessions_or_allow_cross_origin_reads(self):
        response = self.client.post(
            "/api/check", json={"question_id": 1, "answer": "a"},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn("access-control-allow-origin", response.headers)
        preflight = self.client.options("/api/check", headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(preflight.status_code, 405)
        self.assertNotIn("access-control-allow-origin", preflight.headers)


class RequestStreamTests(SecurityAssertions, unittest.IsolatedAsyncioTestCase):
    async def call_asgi(self, receive, extra_headers=()):
        application = quiz_app.create_app(allowed_hosts=["localhost"])
        events = []

        async def send(event):
            events.append(event)

        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1", "method": "POST", "scheme": "http",
            "path": "/api/check", "raw_path": b"/api/check", "query_string": b"",
            "headers": [
                (b"host", b"localhost"), (b"content-type", b"application/json"),
                *extra_headers,
            ],
            "client": ("127.0.0.1", 12345), "server": ("localhost", 8000),
        }
        await asyncio.wait_for(application(scope, receive, send), timeout=2)
        start = next(event for event in events if event["type"] == "http.response.start")
        headers = {key.decode(): value.decode() for key, value in start["headers"]}
        body = b"".join(
            event.get("body", b"") for event in events if event["type"] == "http.response.body"
        )
        self.assert_security_headers(headers)
        self.assertEqual(headers.get("cache-control"), "no-store")
        return start["status"], json.loads(body)

    async def test_oversized_declared_body_is_rejected_without_reading_it(self):
        reads = 0

        async def receive():
            nonlocal reads
            reads += 1
            await asyncio.Event().wait()

        status, body = await self.call_asgi(
            receive, [(b"content-length", str(quiz_app.MAX_BODY_SIZE + 1).encode())]
        )
        self.assertEqual(status, 400)
        self.assertIn("16 Ko", body["error"])
        self.assertEqual(reads, 0)

    async def test_chunked_body_limit_stops_before_consuming_all_chunks(self):
        chunks = [b"a" * 8000, b"b" * 8000, b"c" * 385, b"unread"]
        reads = 0

        async def receive():
            nonlocal reads
            chunk = chunks[reads]
            reads += 1
            return {"type": "http.request", "body": chunk, "more_body": reads < len(chunks)}

        status, body = await self.call_asgi(receive)
        self.assertEqual(status, 400)
        self.assertIn("16 Ko", body["error"])
        self.assertEqual(reads, 3)

    async def test_stalled_body_returns_timeout(self):
        reads = 0

        async def receive():
            nonlocal reads
            reads += 1
            if reads == 1:
                return {"type": "http.request", "body": b"{", "more_body": True}
            await asyncio.Event().wait()

        with patch.object(quiz_app, "REQUEST_BODY_TIMEOUT", 0.05):
            status, body = await self.call_asgi(receive)
        self.assertEqual(status, 408)
        self.assertIsInstance(body.get("error"), str)
        self.assertGreaterEqual(reads, 2)

    async def test_continuous_slow_chunks_cannot_extend_total_deadline(self):
        reads = 0

        async def receive():
            nonlocal reads
            await asyncio.sleep(0.01)
            reads += 1
            return {"type": "http.request", "body": b" ", "more_body": True}

        with patch.object(quiz_app, "REQUEST_BODY_TIMEOUT", 0.05):
            status, body = await self.call_asgi(receive)
        self.assertEqual(status, 408)
        self.assertIsInstance(body.get("error"), str)
        self.assertGreaterEqual(reads, 1)
        self.assertLess(reads, 50)


if __name__ == "__main__":
    unittest.main()
