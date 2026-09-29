"""Un QCM de français, servi par Flask et corrigé côté serveur."""

import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge


QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"
PUBLIC_FIELDS = ("id", "tense", "before", "verb", "after", "options")


def load_questions(path=QUESTIONS_PATH):
    """Refuser au démarrage un fichier de questions incomplet ou incohérent."""
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

        for field in ("tense", "before", "verb", "after", "explanation"):
            value = question.get(field)
            if not isinstance(value, str) or (field not in ("before", "after") and not value.strip()):
                raise ValueError(f"Question {question_id} : champ « {field} » invalide.")
        if question["tense"] not in ("Imparfait", "Passé simple"):
            raise ValueError(f"Question {question_id} : temps inconnu.")

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


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    app.json.ensure_ascii = False
    questions = load_questions()
    question_ids = {str(question["id"]) for question in questions}

    @app.get("/")
    def index():
        # La solution et les explications ne sont envoyées qu'après soumission.
        public_questions = [
            {field: question[field] for field in PUBLIC_FIELDS}
            for question in questions
        ]
        return render_template("index.html", questions=public_questions)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(RequestEntityTooLarge)
    def payload_too_large(_error):
        return jsonify(error="La requête est trop volumineuse (16 Ko maximum)."), 400

    @app.after_request
    def disable_api_cache(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/submit")
    def submit():
        if not request.is_json:
            return jsonify(error="La requête doit être envoyée au format JSON."), 400
        try:
            payload = request.get_json()
        except (BadRequest, RecursionError):
            return jsonify(error="Le contenu JSON de la requête est invalide."), 400

        if not isinstance(payload, dict) or set(payload) != {"answers"}:
            return jsonify(error="Envoyez un objet JSON contenant uniquement « answers »."), 400
        answers = payload["answers"]
        if not isinstance(answers, dict):
            return jsonify(error="Le champ « answers » doit contenir un objet de réponses."), 400
        if set(answers) != question_ids:
            return jsonify(error="Répondez à toutes les questions, sans identifiant supplémentaire."), 400

        for question in questions:
            selected = answers[str(question["id"])]
            valid_options = {option["id"] for option in question["options"]}
            if not isinstance(selected, str) or selected not in valid_options:
                return jsonify(error=f"Choisissez une réponse valide pour la question {question['id']}."), 400

        results = []
        for question in questions:
            selected = answers[str(question["id"])]
            results.append({
                "id": question["id"],
                "selected": selected,
                "correct_answer": question["answer"],
                "is_correct": selected == question["answer"],
                "explanation": question["explanation"],
            })
        return jsonify(
            score=sum(result["is_correct"] for result in results),
            total=len(questions),
            results=results,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=False,
    )
