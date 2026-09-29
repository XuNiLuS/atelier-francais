"""Tests du contenu et de la correction, sans serveur ni service externe."""

import copy
import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app, load_questions


class QuizTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.questions = load_questions()
        cls.correct_answers = {
            str(question["id"]): question["answer"] for question in cls.questions
        }

    def setUp(self):
        self.client = app.test_client()

    def test_content_has_twenty_questions_and_both_tenses(self):
        self.assertEqual([question["id"] for question in self.questions], list(range(1, 21)))
        self.assertEqual(
            Counter(question["tense"] for question in self.questions),
            {"Imparfait": 10, "Passé simple": 10},
        )

    def test_home_passes_questions_without_solutions(self):
        with patch("app.render_template", return_value="QCM") as render:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(render.call_args.args, ("index.html",))
        public_questions = render.call_args.kwargs["questions"]
        self.assertEqual(len(public_questions), 20)
        for question in public_questions:
            self.assertNotIn("answer", question)
            self.assertNotIn("explanation", question)
            self.assertIn("verb", question)
            self.assertEqual(len(question["options"]), 4)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_all_correct_answers(self):
        response = self.client.post("/api/submit", json={"answers": self.correct_answers})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
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
        payload = response.get_json()
        self.assertEqual(payload["score"], 0)
        self.assertTrue(all(not result["is_correct"] for result in payload["results"]))

    def test_mixed_answers(self):
        answers = dict(self.correct_answers)
        answers["1"] = next(choice for choice in "abcd" if choice != answers["1"])
        response = self.client.post("/api/submit", json={"answers": answers})
        self.assertEqual(response.get_json()["score"], 19)
        self.assertFalse(response.get_json()["results"][0]["is_correct"])

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
                    "/api/submit", data=json.dumps(payload), content_type="application/json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.get_json()["error"], str)
                self.assertTrue(response.get_json()["error"])

    def test_invalid_json_and_missing_content_type(self):
        for body, content_type in (
            ("", "application/json"),
            ('{"answers":', "application/json"),
            ("[" * 2000, "application/json"),
            (json.dumps({"answers": self.correct_answers}), "text/plain"),
            (json.dumps({"answers": self.correct_answers}), None),
        ):
            with self.subTest(content_type=content_type, body=body[:30]):
                response = self.client.post("/api/submit", data=body, content_type=content_type)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_oversized_body(self):
        response = self.client.post(
            "/api/submit", data='"' + "a" * (17 * 1024) + '"', content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("16 Ko", response.get_json()["error"])

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
