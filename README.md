# L’atelier des temps

Une petite application de français pour les élèves de 4e : dans chaque phrase, identifier la valeur du verbe mis en évidence au **passé simple** ou à **l’imparfait**.

Le premier QCM contient **20 questions**, dont 10 à chaque temps. Les élèves avancent une question à la fois, reviennent librement sur leurs réponses, puis consultent leur score ainsi que la correction expliquée. Ils peuvent recommencer pour s’entraîner.

Le projet utilise **Python, Flask, HTML, CSS et JavaScript**, sans compilation du front-end. Il ne demande ni compte, ni données personnelles, ni base de données. La page ne charge aucune dépendance distante.

## Démarrer avec Docker

Installer Docker avec la commande `docker compose` disponible, puis lancer depuis le dossier du projet :

```sh
docker compose up --build
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Pour arrêter, utiliser `Ctrl+C`, puis `docker compose down` pour supprimer le conteneur.

Pour laisser tourner l’application en arrière-plan :

```sh
docker compose up --build -d
docker compose logs -f
```

Le conteneur exécute Gunicorn avec un utilisateur non root. Son état de santé est vérifié via `/health`. Aucun volume n’est nécessaire. Après une modification du code ou des questions, relancer `docker compose up --build -d`.

### Accès depuis la classe

Par défaut, seul l’ordinateur qui lance Docker peut accéder à l’application. Pour l’ouvrir aux appareils du même réseau, remplacer la ligne des ports dans `compose.yaml` par :

```yaml
      - "0.0.0.0:8000:8000"
```

Relancer Docker Compose, puis communiquer aux élèves l’adresse `http://ADRESSE_IP_DE_L_ORDINATEUR:8000`. Les appareils doivent être sur le même réseau et le pare-feu doit autoriser le port 8000. Il n’est pas nécessaire de configurer une redirection de port sur la box.

## Démarrer avec Python

Utiliser Python 3.10 ou plus récent ; l’image Docker utilise Python 3.12. Depuis le dossier du projet, sur macOS ou Linux :

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Arrêter le serveur avec `Ctrl+C`.

Sur Windows PowerShell, créer l’environnement avec `py -m venv .venv`, puis l’activer avec `.venv\Scripts\Activate.ps1` avant les deux dernières commandes. Le serveur lancé par `python app.py` est destiné au développement local ; Docker fournit le lancement avec Gunicorn.

## Modifier les questions

Les questions se trouvent dans `data/questions.json`. Chaque entrée contient :

| Champ | Rôle |
| --- | --- |
| `id` | Identifiant entier positif unique de la question. |
| `tense` | Temps étudié : `Imparfait` ou `Passé simple` (respecter la casse et les accents). |
| `before` | Début de la phrase avant le verbe. |
| `verb` | Verbe à mettre en évidence. |
| `after` | Fin de la phrase après le verbe. |
| `options` | Quatre choix, chacun avec un `id` (`a`, `b`, `c`, `d`) et un `label`. |
| `answer` | Identifiant du bon choix. |
| `explanation` | Explication présentée dans la correction. |

Conserver les espaces nécessaires dans `before` et `after`, des identifiants uniques et une réponse qui correspond à l’une des options. Une bonne question donne assez de contexte pour distinguer la valeur du temps, par exemple une habitude, une description ou une action délimitée.

Les questions sont vérifiées au démarrage et les réponses corrigées côté serveur. Après une modification, redémarrer `python app.py`, ou reconstruire l’image si vous utilisez Docker.

Pour préparer un autre QCM, le plus simple est de partir d’une copie du fichier de questions. Lorsqu’un deuxième thème sera prêt, on pourra ajouter une page de choix et charger le fichier correspondant depuis Flask, sans introduire de base de données.

## Structure

```text
app.py                 Application Flask et routes HTTP
requirements.txt       Dépendances Python
data/questions.json    Les 20 questions et leurs corrections
templates/index.html   Page du QCM
static/style.css       Présentation
static/app.js          Interactions dans le navigateur
static/favicon.svg     Icône du site
tests/                 Tests de l’application et du contenu
Dockerfile             Image Python et démarrage Gunicorn
compose.yaml           Lancement Docker
```

## Vérifier

Après avoir installé les dépendances et activé l’environnement Python :

```sh
python -m unittest discover -s tests -v
```

Le point de contrôle [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) permet aussi de vérifier que le serveur répond.

## Git

Le dépôt Git est local. Aucun hébergement externe ni dépôt distant n’est nécessaire pour utiliser l’application. Les environnements virtuels, caches et fichiers `.env` sont exclus du suivi.
