"""Un QCM de français, servi par FastAPI et corrigé côté serveur."""

import json
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, StrictInt
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn


BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "data" / "questions.json"
PUBLIC_FIELDS = ("id", "tense", "before", "verb", "after", "options")
MAX_BODY_SIZE = 16 * 1024
Answer = Literal["a", "b", "c", "d"]


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question_id: StrictInt
    answer: Answer


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answers: dict[str, Answer]


class AnswerResult(BaseModel):
    id: int
    selected: Answer
    correct_answer: Answer
    is_correct: bool
    explanation: str


class QuizResult(BaseModel):
    score: int
    total: int
    results: list[AnswerResult]


class LimitedJSONRequest(Request):
    """Limiter le flux avant que FastAPI lise et valide le contenu JSON."""

    async def body(self):
        if not hasattr(self, "_body"):
            body = bytearray()
            async for chunk in self.stream():
                if len(body) + len(chunk) > MAX_BODY_SIZE:
                    raise HTTPException(
                        400, "La requête est trop volumineuse (16 Ko maximum)."
                    )
                body.extend(chunk)
            self._body = bytes(body)
        return self._body


class JSONRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def route_handler(request: Request):
            if request.url.path.startswith("/api/"):
                content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type != "application/json" and not (
                    content_type.startswith("application/") and content_type.endswith("+json")
                ):
                    raise HTTPException(400, "La requête doit être envoyée au format JSON.")
                request = LimitedJSONRequest(request.scope, request.receive)
            return await original_handler(request)

        return route_handler


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


def answer_result(question, selected):
    return AnswerResult(
        id=question["id"],
        selected=selected,
        correct_answer=question["answer"],
        is_correct=selected == question["answer"],
        explanation=question["explanation"],
    )


def create_app():
    app = FastAPI(title="L’atelier des temps", version="2.0.0")
    app.router.route_class = JSONRoute
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    questions = load_questions()
    questions_by_id = {question["id"]: question for question in questions}
    question_ids = {str(question["id"]) for question in questions}

    @app.middleware("http")
    async def disable_api_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_payload(request: Request, error: RequestValidationError):
        if any(item["type"] == "json_invalid" for item in error.errors()):
            message = "Le contenu JSON de la requête est invalide."
        elif request.url.path == "/api/check":
            message = "Envoyez uniquement « question_id » (un entier) et « answer » (a, b, c ou d)."
        else:
            message = "Envoyez uniquement « answers », un objet associant chaque question à a, b, c ou d."
        return JSONResponse({"error": message}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException):
        messages = {
            "There was an error parsing the body": "Le contenu JSON de la requête est invalide.",
            "Not Found": "Cette ressource est introuvable.",
            "Method Not Allowed": "Cette méthode n’est pas autorisée.",
        }
        message = messages.get(error.detail, error.detail)
        return JSONResponse({"error": message}, status_code=error.status_code, headers=error.headers)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index(request: Request):
        # La solution et les explications ne sont envoyées qu'après une réponse.
        public_questions = [
            {field: question[field] for field in PUBLIC_FIELDS}
            for question in questions
        ]
        return templates.TemplateResponse(
            request=request, name="index.html", context={"questions": public_questions}
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/check", response_model=AnswerResult)
    def check(payload: CheckRequest):
        question = questions_by_id.get(payload.question_id)
        if question is None:
            raise HTTPException(400, "Choisissez un identifiant de question valide.")
        return answer_result(question, payload.answer)

    @app.post("/api/submit", response_model=QuizResult)
    def submit(payload: SubmitRequest):
        if set(payload.answers) != question_ids:
            raise HTTPException(400, "Répondez à toutes les questions, sans identifiant supplémentaire.")
        results = [
            answer_result(question, payload.answers[str(question["id"])])
            for question in questions
        ]
        return QuizResult(
            score=sum(result.is_correct for result in results),
            total=len(questions),
            results=results,
        )

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
