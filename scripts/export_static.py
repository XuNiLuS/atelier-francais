"""Générer le site public sans serveur, avec les mêmes templates et questions.

Exemple : python scripts/export_static.py --base-path /atelier-francais
Seul dist/ est à publier ; Python et les fichiers du dépôt ne sont pas servis.
"""

import argparse
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
from quiz_data import BASE_DIR, LEVELS, SECURITY_HEADERS, load_catalog  # noqa: E402


def export_site(output=PROJECT_DIR / "dist", base_path=""):
    base_path = base_path.rstrip("/")
    if not re.fullmatch(r"(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*", base_path):
        raise ValueError("Le préfixe doit être vide ou un chemin comme /atelier-francais.")
    output = Path(output).absolute()
    marker = output / ".atelier-static-export"
    if output.is_symlink():
        raise ValueError("Le dossier de sortie ne doit pas être un lien symbolique.")
    if output.exists():
        if not output.is_dir() or (any(output.iterdir()) and not marker.is_file()):
            raise ValueError("Choisissez un dossier vide ou un ancien export de cet outil.")

    catalog = load_catalog()
    quiz_navigation = {
        level["id"]: [
            {"id": quiz["id"], "title": quiz["title"]}
            for quiz in catalog.values() if quiz["level"] == level["id"]
        ]
        for level in LEVELS
    }
    environment = Environment(
        loader=FileSystemLoader(BASE_DIR / "templates"),
        autoescape=select_autoescape(["html"]),
    )

    def asset_url(_name, path):
        return SimpleNamespace(path=f"{base_path}/static/{path}")

    def render(name, **context):
        return environment.get_template(name).render(
            levels=LEVELS, site_root=base_path, quiz_navigation=quiz_navigation,
            url_for=asset_url, **context,
        )

    # Tout rendre avant de remplacer un export précédent.
    pages = {"index.html": render("home.html", current_level=None, quizzes=list(catalog.values()))}
    pages["programmes/index.html"] = render("programmes.html", current_level=None)
    for level in LEVELS:
        pages[f'niveaux/{level["id"]}/index.html'] = render(
            "home.html", current_level=level,
            quizzes=[quiz for quiz in catalog.values() if quiz["level"] == level["id"]],
        )
    for quiz_id, quiz in catalog.items():
        pages[f"quiz/{quiz_id}/index.html"] = render(
            "index.html", current_level=next(level for level in LEVELS if level["id"] == quiz["level"]),
            quiz=quiz, questions=quiz["questions"],
        )
    # Une vraie page 404 évite le repli vers un faux questionnaire sur certains hébergeurs.
    pages["404.html"] = environment.from_string(
        '{% extends "base.html" %}{% block title %}Page introuvable{% endblock %}'
        '{% block content %}<main class="page" id="main-content"><h1>Page introuvable</h1>'
        '<p><a href="{{ site_root }}/">Revenir aux quiz</a></p></main>{% endblock %}'
    ).render(levels=LEVELS, current_level=None, site_root=base_path,
             quiz_navigation=quiz_navigation, url_for=asset_url)

    if marker.is_file():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    marker.write_text("Export généré par scripts/export_static.py\n", encoding="utf-8")
    for path, html in pages.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html + "\n", encoding="utf-8")
    (output / "static").mkdir()
    for name in ("app.js", "navigation.js", "style.css", "favicon.svg"):
        shutil.copyfile(BASE_DIR / "static" / name, output / "static" / name)
    (output / ".nojekyll").touch()
    # Appliqué par Cloudflare Pages ; GitHub Pages utilise la CSP meta des pages.
    (output / "_headers").write_text(
        "/*\n" + "".join(f"  {name}: {value}\n" for name, value in SECURITY_HEADERS.items()),
        encoding="utf-8",
    )
    return {"directory": str(output), "pages": len(pages), "quizzes": len(catalog), "base_path": base_path}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "dist")
    parser.add_argument("--base-path", default="")
    args = parser.parse_args()
    print(export_site(args.output, args.base_path))
