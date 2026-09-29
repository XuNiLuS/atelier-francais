"""Tests du contenu et de la correction, sans serveur ni service externe."""

import copy
import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import app, load_questions


class QuizTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = load_questions()
        cls.correct_answers = {
            str(question["id"]): question["answer"] for question in cls.questions
        }

    def setUp(self):
        self.client = TestClient(app, base_url="http://localhost")
        self.addCleanup(self.client.close)

    def test_content_has_twenty_questions_and_both_tenses(self):
        self.assertEqual([question["id"] for question in self.questions], list(range(1, 21)))
        self.assertEqual(
            Counter(question["tense"] for question in self.questions),
            {"Imparfait": 10, "Passé simple": 10},
        )

    def test_home_renders_questions_without_solutions(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertEqual(response.template.name, "index.html")
        self.assertIn("L’atelier des temps", response.text)
        public_questions = response.context["questions"]
        self.assertEqual(len(public_questions), 20)
        for question, original in zip(public_questions, self.questions):
            self.assertNotIn("answer", question)
            self.assertNotIn("explanation", question)
            self.assertNotIn(original["explanation"], response.text)
            self.assertIn("verb", question)
            self.assertEqual(len(question["options"]), 4)
        for name in ("app.js", "style.css", "favicon.svg"):
            self.assertIn(f"/static/{name}", response.text)

    def test_static_assets_are_served(self):
        for name, content_type in (
            ("app.js", "javascript"),
            ("style.css", "text/css"),
            ("favicon.svg", "image/svg+xml"),
        ):
            with self.subTest(asset=name):
                response = self.client.get(f"/static/{name}")
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.headers["Content-Type"])
                self.assertTrue(response.content)

    def test_api_schema_describes_request_models(self):
        schema = app.openapi()
        for route in ("/api/check", "/api/submit"):
            self.assertIn("requestBody", schema["paths"][route]["post"])

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_all_correct_answers(self):
        response = self.client.post("/api/submit", json={"answers": self.correct_answers})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["score"], 20)
        self.assertEqual(payload["total"], 20)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual([result["id"] for result in payload["results"]], list(range(1, 21)))
        for result, question in zip(payload["results"], self.questions):
            self.assertTrue(result["is_correct"])
            self.assertEqual(result["selected"], question["answer"])
            self.assertEqual(result["correct_answer"], question["answer"])
            self.assertEqual(result["explanation"], question["explanation"])

    def test_all_incorrect_answers(self):
        answers = {
            str(question["id"]): next(
                option["id"] for option in question["options"]
                if option["id"] != question["answer"]
            )
            for question in self.questions
        }
        response = self.client.post("/api/submit", json={"answers": answers})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["score"], 0)
        self.assertTrue(all(not result["is_correct"] for result in payload["results"]))

    def test_mixed_answers(self):
        answers = dict(self.correct_answers)
        answers["1"] = next(choice for choice in "abcd" if choice != answers["1"])
        response = self.client.post("/api/submit", json={"answers": answers})
        self.assertEqual(response.json()["score"], 19)
        self.assertFalse(response.json()["results"][0]["is_correct"])

    def test_invalid_payloads_return_clear_json_errors(self):
        missing_answer = dict(self.correct_answers)
        missing_answer.pop("1")
        invalid_payloads = [
            None,
            [],
            "texte",
            {},
            {"answers": []},
            {"answers": None},
            {"answers": missing_answer},
            {"answers": {**self.correct_answers, "21": "a"}},
            {"answers": {**self.correct_answers, "01": "a"}},
            {"answers": self.correct_answers, "score": 20},
        ]
        for invalid_answer in ("e", "A", "", 1, True, None, [], {}):
            invalid_payloads.append({"answers": {**self.correct_answers, "1": invalid_answer}})
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/submit", content=json.dumps(payload), headers={"Content-Type": "application/json"}
                )
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.json()["error"], str)
                self.assertTrue(response.json()["error"])

    def assert_api_error(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json()["error"], str)
        self.assertTrue(response.json()["error"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_each_question_can_be_checked_correctly_and_incorrectly(self):
        for question in self.questions:
            for selected in "abcd":
                with self.subTest(question=question["id"], selected=selected):
                    response = self.client.post(
                        "/api/check", json={"question_id": question["id"], "answer": selected}
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {
                        "id": question["id"],
                        "selected": selected,
                        "correct_answer": question["answer"],
                        "is_correct": selected == question["answer"],
                        "explanation": question["explanation"],
                    })
                    self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_check_requests_are_independent_and_do_not_change_final_score(self):
        question = self.questions[0]
        correct = question["answer"]
        incorrect = next(choice for choice in "abcd" if choice != correct)
        payload = {"question_id": question["id"], "answer": incorrect}
        first = self.client.post("/api/check", json=payload).json()
        correct_result = self.client.post(
            "/api/check", json={"question_id": question["id"], "answer": correct}
        ).json()
        repeated = self.client.post("/api/check", json=payload).json()
        self.assertEqual(first, repeated)
        self.assertFalse(first["is_correct"])
        self.assertTrue(correct_result["is_correct"])
        response = self.client.post("/api/submit", json={"answers": self.correct_answers})
        self.assertEqual(response.json()["score"], 20)

    def test_check_rejects_invalid_payloads_and_non_integer_identifiers(self):
        invalid_payloads = [None, [], "texte", {}, {"answer": "a"}, {"question_id": 1}]
        invalid_payloads.append({"question_id": 1, "answer": "a", "score": 1})
        for question_id in (True, False, 1.0, "1", "01", None, [], {}, -1, 0, 21):
            invalid_payloads.append({"question_id": question_id, "answer": "a"})
        for answer in ("e", "A", "", 1, True, None, [], {}):
            invalid_payloads.append({"question_id": 1, "answer": answer})
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/check", content=json.dumps(payload), headers={"Content-Type": "application/json"}
                )
                self.assert_api_error(response)

    def test_invalid_json_and_missing_content_type(self):
        for route in ("/api/check", "/api/submit"):
            for body, content_type in (
                ("", "application/json"),
                ('{"answers":', "application/json"),
                ("[" * 2000, "application/json"),
                (b"\xff", "application/json"),
                (json.dumps({"answers": self.correct_answers}), "text/plain"),
                (json.dumps({"answers": self.correct_answers}), None),
            ):
                with self.subTest(route=route, content_type=content_type, body=body[:30]):
                    headers = {"Content-Type": content_type} if content_type else {}
                    response = self.client.post(route, content=body, headers=headers)
                    self.assert_api_error(response)

    def test_oversized_body_with_and_without_content_length(self):
        body = b'"' + b"a" * (17 * 1024) + b'"'
        for route in ("/api/check", "/api/submit"):
            for chunked in (False, True):
                with self.subTest(route=route, chunked=chunked):
                    content = iter([body[:8000], body[8000:]]) if chunked else body
                    response = self.client.post(
                        route, content=content, headers={"Content-Type": "application/json"}
                    )
                    self.assert_api_error(response)
                    self.assertIn("16 Ko", response.json()["error"])
                    if chunked:
                        self.assertNotIn("Content-Length", response.request.headers)

    def test_body_at_size_limit_and_json_content_type_parameters_are_accepted(self):
        payload = json.dumps({"question_id": 1, "answer": "a"})
        body = payload + " " * (16 * 1024 - len(payload))
        response = self.client.post(
            "/api/check", content=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 1)

    def test_invalid_question_file_fails_at_loading(self):
        invalid_datasets = [[], {}, ["question"]]
        duplicate_id = copy.deepcopy(self.questions)
        duplicate_id[1]["id"] = duplicate_id[0]["id"]
        invalid_datasets.append(duplicate_id)
        for field, value in (
            ("id", True),
            ("tense", "futur"),
            ("verb", ""),
            ("explanation", ""),
            ("answer", "e"),
            ("options", [{"id": "a", "label": "Même option"}] * 4),
        ):
            dataset = copy.deepcopy(self.questions)
            dataset[0][field] = value
            invalid_datasets.append(dataset)
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "questions.json"
            for index, dataset in enumerate(invalid_datasets):
                with self.subTest(dataset=index):
                    path.write_text(json.dumps(dataset), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_questions(path)


if __name__ == "__main__":
    unittest.main()
