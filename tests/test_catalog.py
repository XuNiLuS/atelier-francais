"""Parcours par niveau, correction isolée par quiz et intégrité des contenus."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import app, load_catalog


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def setUp(self):
        self.client = TestClient(app, base_url="http://localhost")
        self.addCleanup(self.client.close)

    def test_home_and_level_pages_expose_the_right_quizzes(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertEqual(len(home.context["quizzes"]), 6)
        self.assertNotIn('id="quiz-data"', home.text)
        for level in ("4e", "3e", "seconde"):
            response = self.client.get(f"/niveaux/{level}")
            self.assertEqual(response.status_code, 200)
            quizzes = response.context["quizzes"]
            self.assertEqual(len(quizzes), 2)
            self.assertTrue(all(quiz["level"] == level for quiz in quizzes))
            for quiz in quizzes:
                self.assertIn(f'/quiz/{quiz["id"]}', response.text)
        self.assertEqual(self.client.get("/niveaux/terminale").status_code, 404)

    def test_all_six_quizzes_have_twenty_valid_original_questions(self):
        sentences = set()
        for quiz in self.catalog.values():
            with self.subTest(quiz=quiz["id"]):
                questions = quiz["questions"]
                self.assertEqual([item["id"] for item in questions], list(range(1, 21)))
                for question in questions:
                    sentence = question["before"] + question["focus"] + question["after"]
                    self.assertNotIn(sentence, sentences)
                    sentences.add(sentence)
                    self.assertEqual(len({choice["label"] for choice in question["options"]}), 4)
                    self.assertTrue(question["prompt"].strip())
                    self.assertTrue(question["explanation"].strip())

    def test_every_quiz_renders_only_public_question_fields(self):
        for quiz_id, quiz in self.catalog.items():
            with self.subTest(quiz=quiz_id):
                response = self.client.get(f"/quiz/{quiz_id}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["current_level"]["id"], quiz["level"])
                self.assertEqual(len(response.context["questions"]), 20)
                for question, public in zip(quiz["questions"], response.context["questions"]):
                    self.assertNotIn("answer", public)
                    self.assertNotIn("explanation", public)
                    self.assertNotIn(question["explanation"], response.text)
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_all_answers_use_the_selected_quiz_and_its_explanation(self):
        for quiz_id, quiz in self.catalog.items():
            for question in quiz["questions"]:
                for choice in "abcd":
                    with self.subTest(quiz=quiz_id, question=question["id"], choice=choice):
                        response = self.client.post(f"/api/quizzes/{quiz_id}/check", json={
                            "question_id": question["id"], "answer": choice,
                        })
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json(), {
                            "id": question["id"], "selected": choice,
                            "correct_answer": question["answer"],
                            "is_correct": choice == question["answer"],
                            "explanation": question["explanation"],
                        })

    def test_full_scores_and_incomplete_submissions_for_every_quiz(self):
        for quiz_id, quiz in self.catalog.items():
            route = f"/api/quizzes/{quiz_id}/submit"
            for correct in (True, False):
                answers = {str(q["id"]): q["answer"] if correct else next(c for c in "abcd" if c != q["answer"]) for q in quiz["questions"]}
                response = self.client.post(route, json={"answers": answers})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["score"], 20 if correct else 0)
                self.assertEqual(response.json()["total"], 20)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            answers.pop("20")
            self.assertEqual(self.client.post(route, json={"answers": answers}).status_code, 400)

    def test_unknown_quizzes_never_fall_back_to_another_quiz_or_a_file(self):
        for quiz_id in ("unknown", "catalog.json", "questions", "3e", "..%2Fcatalog"):
            self.assertEqual(self.client.get(f"/quiz/{quiz_id}").status_code, 404)
            for action, data in (("check", {"question_id": 1, "answer": "a"}), ("submit", {"answers": {}})):
                response = self.client.post(f"/api/quizzes/{quiz_id}/{action}", json=data)
                self.assertEqual(response.status_code, 404)
        for path in ("/data/catalog.json", "/data/quizzes/3e-temps-recit.json"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_new_api_retains_request_limits_validation_and_host_checks(self):
        route = "/api/quizzes/seconde-syntaxe/check"
        for data in ({"question_id": True, "answer": "a"}, {"question_id": 1, "answer": "a", "quiz_id": "4e-temps-recit"}):
            self.assertEqual(self.client.post(route, json=data).status_code, 400)
        large = self.client.post(route, content=b" " * 17000, headers={"Content-Type": "application/json"})
        self.assertEqual(large.status_code, 400)
        self.assertIn("16 Ko", large.json()["error"])
        self.assertEqual(self.client.get("/niveaux/3e", headers={"Host": "attacker.example"}).status_code, 400)
        legacy = self.client.post("/api/check?quiz_id=seconde-syntaxe", json={"question_id": 1, "answer": "a"})
        self.assertEqual(legacy.json()["explanation"], self.catalog["4e-temps-recit"]["questions"][0]["explanation"])

    def test_catalog_rejects_invalid_identifiers_and_levels_at_startup(self):
        definitions = [{key: value for key, value in quiz.items() if key not in ("questions", "count")} for quiz in self.catalog.values()]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            for field, value in (("id", "../questions"), ("level", "unknown"), ("help", []), ("objectives", [""])):
                data = copy.deepcopy(definitions)
                data[0][field] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_catalog(path)

    def test_curriculum_page_explains_the_anticipated_programmes(self):
        response = self.client.get("/programmes")
        self.assertEqual(response.status_code, 200)
        for text in ("2027–2028", "2028–2029", "MENE2602912A", "générale et technologique"):
            self.assertIn(text, response.text)


if __name__ == "__main__":
    unittest.main()
