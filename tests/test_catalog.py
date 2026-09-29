"""Intégrité des contenus et validation des fichiers, sans serveur HTTP."""

import copy
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest

from quiz_data import DEFAULT_QUIZ, LEVELS, load_catalog, load_questions


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.definitions = [
            {key: value for key, value in quiz.items() if key not in ("questions", "count")}
            for quiz in cls.catalog.values()
        ]

    def test_catalog_has_six_quizzes_and_one_hundred_twenty_questions(self):
        self.assertEqual(len(self.catalog), 6)
        self.assertEqual(sum(quiz["count"] for quiz in self.catalog.values()), 120)
        self.assertIn(DEFAULT_QUIZ, self.catalog)
        self.assertEqual({level["id"] for level in LEVELS}, {"4e", "3e", "seconde"})
        self.assertEqual(
            Counter(quiz["level"] for quiz in self.catalog.values()),
            {"4e": 2, "3e": 2, "seconde": 2},
        )
        for quiz_id, quiz in self.catalog.items():
            with self.subTest(quiz=quiz_id):
                self.assertEqual(quiz["id"], quiz_id)
                self.assertTrue(quiz_id.startswith(quiz["level"] + "-"))
                self.assertEqual(quiz["count"], len(quiz["questions"]))

    def test_each_quiz_has_twenty_original_explained_questions(self):
        sentences = set()
        for quiz_id, quiz in self.catalog.items():
            with self.subTest(quiz=quiz_id):
                questions = quiz["questions"]
                self.assertEqual([item["id"] for item in questions], list(range(1, 21)))
                self.assertEqual(Counter(q["answer"] for q in questions), dict.fromkeys("abcd", 5))
                for question in questions:
                    sentence = question["before"] + question["focus"] + question["after"]
                    self.assertNotIn(sentence, sentences)
                    sentences.add(sentence)
                    self.assertEqual({choice["id"] for choice in question["options"]}, set("abcd"))
                    self.assertEqual(len({choice["label"] for choice in question["options"]}), 4)
                    self.assertTrue(question["prompt"].strip())
                    self.assertTrue(question["explanation"].strip())

    def test_reference_quiz_keeps_both_narrative_tenses(self):
        questions = load_questions()
        self.assertEqual(questions, self.catalog[DEFAULT_QUIZ]["questions"])
        self.assertEqual(
            Counter(question["label"] for question in questions),
            {"Imparfait": 10, "Passé simple": 10},
        )

    def assert_rejected(self, datasets, loader):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for label, dataset in datasets:
                with self.subTest(dataset=label):
                    path.write_text(json.dumps(dataset), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        loader(path)

    def test_catalog_rejects_invalid_structure_and_metadata(self):
        invalid = [("empty", []), ("object", {}), ("non-object item", ["quiz"])]
        for field, value in (
            ("id", "../questions"), ("id", "quiz/secret"), ("id", ""),
            ("id", 3), ("level", "unknown"), ("level", None),
            ("title", ""), ("description", None), ("eyebrow", " "),
            ("help", []), ("help", ["texte"]), ("help", [{"title": "Titre"}]),
            ("objectives", [""]), ("objectives", "Objectif"),
        ):
            data = copy.deepcopy(self.definitions)
            data[0][field] = value
            invalid.append((f"{field}={value!r}", data))
        self.assert_rejected(invalid, load_catalog)

    def test_catalog_rejects_duplicate_identifiers_and_missing_reference_quiz(self):
        duplicate = copy.deepcopy(self.definitions)
        duplicate.append(copy.deepcopy(duplicate[0]))
        without_reference = [item for item in self.definitions if item["id"] != DEFAULT_QUIZ]
        self.assert_rejected([
            ("duplicate id", duplicate), ("missing reference", without_reference),
        ], load_catalog)

    def test_question_loader_rejects_invalid_content_and_choices(self):
        questions = self.catalog[DEFAULT_QUIZ]["questions"]
        invalid = [("empty", []), ("object", {}), ("non-object item", ["question"])]
        duplicate = copy.deepcopy(questions)
        duplicate[1]["id"] = duplicate[0]["id"]
        invalid.append(("duplicate id", duplicate))
        for field, value in (
            ("id", True), ("id", 0), ("id", -1), ("id", "1"),
            ("label", ""), ("prompt", ""), ("focus", " "),
            ("before", None), ("after", 3), ("explanation", ""),
            ("answer", "e"), ("answer", True),
            ("options", [{"id": "a", "label": "Même option"}] * 4),
            ("options", []), ("options", None),
        ):
            data = copy.deepcopy(questions)
            data[0][field] = value
            invalid.append((f"{field}={value!r}", data))
        self.assert_rejected(invalid, load_questions)


if __name__ == "__main__":
    unittest.main()
