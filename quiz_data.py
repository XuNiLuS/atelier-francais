"""Catalogue et validation des quiz, sans serveur ni dépendance externe."""


import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


DEFAULT_QUIZ = "4e-temps-recit"


QUESTIONS_PATH = BASE_DIR / "data" / "quizzes" / f"{DEFAULT_QUIZ}.json"


LEVELS = (
    {"id": "4e", "name": "4e", "stage": "Collège", "description": "Explorer les temps, les accords, la phrase complexe et les paroles rapportées."},
    {"id": "3e", "name": "3e", "stage": "Collège", "description": "Maîtriser le conditionnel, le subjonctif et les accords ; interpréter les paroles rapportées."},
    {"id": "seconde", "name": "Seconde", "stage": "Lycée général et technologique", "description": "Analyser les temps, la modalisation et la syntaxe ; justifier les accords et les choix d’écriture."},
)


SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
        "connect-src 'none'; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def load_questions(path=QUESTIONS_PATH):
    """Refuser un fichier de questions incomplet ou incohérent avant la génération."""
    with Path(path).open(encoding="utf-8") as source:
        questions = json.load(source)

    if not isinstance(questions, list) or not questions:
        raise ValueError("Le QCM doit contenir une liste non vide de questions.")

    seen_ids = set()
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Chaque question doit être un objet JSON.")
        question_id = question.get("id")
        if type(question_id) is not int or question_id < 1 or question_id in seen_ids:
            raise ValueError("Chaque question doit avoir un identifiant entier positif unique.")
        seen_ids.add(question_id)

        for field in ("label", "prompt", "before", "focus", "after", "explanation"):
            value = question.get(field)
            if not isinstance(value, str) or (field not in ("before", "after") and not value.strip()):
                raise ValueError(f"Question {question_id} : champ « {field} » invalide.")
        options = question.get("options")
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"Question {question_id} : quatre choix sont nécessaires.")
        option_ids = []
        for option in options:
            if (
                not isinstance(option, dict)
                or not isinstance(option.get("id"), str)
                or not isinstance(option.get("label"), str)
                or not option["label"].strip()
            ):
                raise ValueError(f"Question {question_id} : choix invalide.")
            option_ids.append(option["id"])
        if set(option_ids) != {"a", "b", "c", "d"}:
            raise ValueError(f"Question {question_id} : les choix doivent être a, b, c et d.")
        if not isinstance(question.get("answer"), str) or question["answer"] not in option_ids:
            raise ValueError(f"Question {question_id} : réponse correcte invalide.")

    return questions


def load_catalog(path=BASE_DIR / "data" / "catalog.json"):
    """Valider le catalogue local et charger uniquement ses fichiers de quiz autorisés."""
    with Path(path).open(encoding="utf-8") as source:
        definitions = json.load(source)
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("Le catalogue doit contenir des quiz.")
    catalog = {}
    for definition in definitions:
        if not isinstance(definition, dict):
            raise ValueError("Chaque quiz du catalogue doit être un objet.")
        quiz_id = definition.get("id")
        if not isinstance(quiz_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", quiz_id) or quiz_id in catalog:
            raise ValueError("Chaque quiz doit avoir un identifiant unique sans chemin.")
        if definition.get("level") not in {level["id"] for level in LEVELS}:
            raise ValueError(f"Quiz {quiz_id} : niveau inconnu.")
        for field in ("title", "description", "eyebrow"):
            if not isinstance(definition.get(field), str) or not definition[field].strip():
                raise ValueError(f"Quiz {quiz_id} : champ {field} invalide.")
        objectives = definition.get("objectives")
        if not isinstance(objectives, list) or not objectives or any(not isinstance(item, str) or not item.strip() for item in objectives):
            raise ValueError(f"Quiz {quiz_id} : objectifs invalides.")
        help_items = definition.get("help")
        if not isinstance(help_items, list) or not help_items or any(
            not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key].strip() for key in ("title", "text"))
            for item in help_items
        ):
            raise ValueError(f"Quiz {quiz_id} : aide invalide.")
        questions = load_questions(BASE_DIR / "data" / "quizzes" / f"{quiz_id}.json")
        catalog[quiz_id] = {**definition, "questions": questions, "count": len(questions)}
    if DEFAULT_QUIZ not in catalog:
        raise ValueError("Le quiz de référence de 4e est absent du catalogue.")
    return catalog
