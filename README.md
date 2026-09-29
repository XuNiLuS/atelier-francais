# L’atelier des temps

Une petite application de français pour les élèves de 4e : dans chaque phrase, identifier la valeur du verbe mis en évidence au **passé simple** ou à **l’imparfait**.

Le premier QCM contient **20 questions**, dont 10 à chaque temps. Pour chaque phrase, l’élève choisit une réponse puis clique sur **Vérifier ma réponse** : il voit immédiatement si elle est correcte, la bonne réponse et une explication. La réponse est alors figée pour cet essai, et le bouton **Suivante** permet de continuer. La grille permet de parcourir librement les questions et de relire les corrections déjà obtenues.

Une fois les 20 réponses vérifiées, l’élève peut consulter son score et le bilan détaillé. **Recommencer** remet à zéro les réponses et les corrections pour un nouvel entraînement.

Le projet utilise **Python, FastAPI, Jinja2, HTML, CSS et JavaScript**, sans compilation du front-end. Uvicorn sert l’application. Il ne demande ni compte, ni données personnelles, ni base de données. La progression reste dans la page ouverte ; le serveur ne conserve aucun état d’élève. La page ne charge aucune dépendance distante.

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

Le conteneur exécute Uvicorn avec un seul processus et l’utilisateur non root `atelier`. Son état de santé est vérifié via `/health`. Aucun volume n’est nécessaire. Après une modification du code ou des questions, relancer `docker compose up --build -d`.

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

Sur Windows PowerShell, créer l’environnement avec `py -m venv .venv`, puis l’activer avec `.venv\Scripts\Activate.ps1` avant les deux dernières commandes.

`python app.py` lance Uvicorn sur `127.0.0.1:8000`. Les variables d’environnement `HOST` et `PORT` permettent de changer cette adresse et ce port. Il est aussi possible de lancer directement `uvicorn app:app --host 127.0.0.1 --port 8000`.

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
| `explanation` | Explication présentée après vérification de la réponse et dans le bilan. |

Conserver les espaces nécessaires dans `before` et `after`, des identifiants uniques et une réponse qui correspond à l’une des options. Une bonne question donne assez de contexte pour distinguer la valeur du temps, par exemple une habitude, une description ou une action délimitée.

Les questions sont vérifiées au démarrage et les réponses corrigées côté serveur. Après une modification, redémarrer `python app.py`, ou reconstruire l’image si vous utilisez Docker.

Pour préparer un autre QCM, le plus simple est de partir d’une copie du fichier de questions. Lorsqu’un deuxième thème sera prêt, on pourra ajouter une page de choix et charger le fichier correspondant depuis FastAPI, sans introduire de base de données.

## Routes HTTP

| Route | Rôle |
| --- | --- |
| `GET /` | Page du QCM, rendue avec Jinja2. |
| `GET /health` | État de santé du serveur : `{"status":"ok"}`. |
| `POST /api/check` | Vérification d’une réponse : envoyer `{"question_id":1,"answer":"a"}` pour recevoir la correction et son explication. |
| `POST /api/submit` | Bilan complet : envoyer `{"answers":{"1":"a","2":"b",...}}` avec toutes les réponses pour recevoir le score et les corrections. |

Les deux routes de correction acceptent du JSON. Les bonnes réponses et les explications ne sont pas incluses dans la page initiale ; elles sont envoyées lors de la vérification ou du bilan. Ces routes ne stockent pas les réponses.

## Structure

```text
app.py                 Application FastAPI et routes HTTP
requirements.txt       Dépendances Python pour servir l’application
requirements-dev.txt   Dépendances supplémentaires pour les tests (HTTPX)
data/questions.json    Les 20 questions et leurs corrections
templates/index.html   Page du QCM
static/style.css       Présentation
static/app.js          Interactions dans le navigateur
static/favicon.svg     Icône du site
tests/                 Tests de l’application et du contenu
Dockerfile             Image Python et démarrage Uvicorn
compose.yaml           Lancement Docker
```

## Vérifier

Après avoir activé l’environnement Python, installer les dépendances de développement (qui incluent celles de l’application), puis lancer les tests `unittest` avec le client de test FastAPI :

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Le point de contrôle [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) permet aussi de vérifier que le serveur répond.

## Git

Le dépôt Git est local. Aucun hébergement externe ni dépôt distant n’est nécessaire pour utiliser l’application. Les environnements virtuels, caches et fichiers `.env` sont exclus du suivi.
