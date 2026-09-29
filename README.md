# L’atelier de français

Des quiz de grammaire pour les **4e, 3e et secondes générales et technologiques**, avec une difficulté progressive. La page d’accueil présente les niveaux et les thèmes. Chaque quiz contient **20 questions**, soit **120 questions** dans cette version.

| Niveau | Quiz disponibles |
| --- | --- |
| 4e | Temps du récit ; classes, fonctions et accords |
| 3e | Temps du récit ; phrase complexe |
| Seconde GT | Temps et effets de récit ; syntaxe et propositions relatives |

Au collège, le contenu anticipe le **nouveau programme officiel publié en mars 2026**, applicable en 4e à la rentrée **2027-2028** et en 3e à la rentrée **2028-2029**. Le programme de seconde est celui de 2019 modifié en 2020. Les sources et les choix pédagogiques sont décrits dans [docs/PROGRAMMES.md](docs/PROGRAMMES.md) et sur la page `/programmes`. Ces premiers quiz couvrent une sélection de notions, pas l’ensemble du programme.

L’élève choisit une réponse puis clique sur **Vérifier ma réponse** : il voit si elle est correcte, la bonne réponse et une explication. La réponse est alors figée pour cet essai. Il peut revenir sur les questions, lire son bilan sur 20 et recommencer. Chaque quiz a ses propres questions, corrections et aides.

Le projet utilise **Python, FastAPI, Jinja2, HTML, CSS et JavaScript**, sans compilation du front-end. Uvicorn sert l’application. Aucun compte ni base de données n’est nécessaire. La progression reste dans la page ouverte : changer de quiz ou recharger la page commence un nouvel essai. Le serveur ne conserve aucun état d’élève et la page ne charge aucune dépendance distante.

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

Le conteneur exécute Uvicorn avec un seul processus et l’utilisateur non root `atelier`. Les fichiers de l’application appartiennent à root et le système de fichiers du conteneur est en lecture seule. Il ne possède aucune capacité Linux supplémentaire et ne peut pas gagner de nouveaux privilèges. Aucun volume n’est nécessaire.

`pip` est mis à jour et utilisé uniquement pendant la construction, puis retiré de l’environnement d’exécution avec ses bibliothèques embarquées. Pour ajouter une dépendance, modifier `requirements.txt` et reconstruire l’image.

Docker Compose limite le conteneur à 256 Mo de mémoire, 1 CPU et 64 processus. Les journaux Docker sont limités à trois fichiers de 10 Mo. Uvicorn limite les connexions/tâches simultanées à 100 et désactive ses journaux d’accès ainsi que la confiance dans les en-têtes de proxy. Son état de santé est vérifié via `/health`. Ces limites sont un point de départ à ajuster selon la classe et l’hébergement.

Après une modification du code ou des questions, relancer `docker compose up --build -d`. Le `Dockerfile` et `.dockerignore` autorisent seulement les fichiers nécessaires à l’application : si vous ajoutez un fichier au projet qui doit être présent dans l’image, mettre à jour cette liste.

### Accès depuis la classe

Par défaut, seul l’ordinateur qui lance Docker peut accéder à l’application. Pour l’ouvrir aux appareils du même réseau, remplacer la ligne des ports dans `compose.yaml` par :

```yaml
      - "0.0.0.0:8000:8000"
```

Ajouter aussi l’adresse IP de l’ordinateur aux hôtes autorisés. Par exemple, pour `192.168.1.25` :

```sh
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.25 docker compose up --build -d
```

Communiquer aux élèves l’adresse `http://192.168.1.25:8000`, en remplaçant l’exemple par l’adresse réelle de l’ordinateur. Les appareils doivent être sur le même réseau et le pare-feu doit autoriser le port 8000. Il n’est pas nécessaire de configurer une redirection de port sur la box. Cet accès HTTP concerne seulement le réseau local ; l’accès public exige HTTPS.

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

`python app.py` lance Uvicorn sur `127.0.0.1:8000`. Les variables d’environnement `HOST` et `PORT` permettent de changer cette adresse et ce port. `ALLOWED_HOSTS` définit les noms d’hôte acceptés, séparés par des virgules ; les valeurs par défaut sont `localhost,127.0.0.1`. Changer `HOST` ne change pas les hôtes autorisés.

## Préparer un hébergement public

Pour une publication gratuite **sans mise en veille**, un export HTML/CSS/JavaScript est disponible. Le projet Python/Docker reste utilisable ; la version exportée corrige les réponses dans le navigateur. La procédure et le déploiement automatique GitHub Pages sont décrits dans [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md).

```sh
python scripts/export_static.py
python -m http.server 8080 --bind 127.0.0.1 --directory dist
```

Le deuxième appel sert uniquement à prévisualiser l’export localement. Publier **le contenu de `dist/`**, jamais le dossier entier du projet. Pour GitHub Pages, le workflow prépare automatiquement le préfixe d’URL du dépôt et n’envoie que cet export. Dans cette version publique, les bonnes réponses et les explications sont incluses dans les pages : les scores sont des entraînements et non des notes authentifiées.

Les conditions ci-dessous concernent un hébergement du **serveur FastAPI** ; l’export statique ne déploie pas de serveur Python.

L’application convient à un entraînement libre : aucun compte, cookie de session, enregistrement de résultat ou donnée personnelle n’est demandé. Un visiteur peut demander les corrections directement à l’API et recommencer ; le score n’est pas une note d’évaluation authentifiée. Le serveur d’hébergement et son proxy peuvent cependant conserver des adresses IP dans leurs journaux : minimiser ces journaux et leur durée de conservation.

L’audit et ses limites sont détaillés dans [SECURITY.md](SECURITY.md). Avant l’ouverture au public :

1. Placer l’application derrière le frontal HTTPS de l’hébergeur ou un reverse proxy avec certificat valide. Garder le port 8000 accessible seulement depuis ce frontal ; ne pas publier directement Uvicorn sur Internet. Aucun hébergement n’est configuré par ce dépôt.
2. Définir les noms de domaine exacts dans `ALLOWED_HOSTS`, sans protocole, chemin ni port. Conserver `127.0.0.1` pour le contrôle de santé. Exemple : `ALLOWED_HOSTS=localhost,127.0.0.1,francais.exemple.fr docker compose up --build -d`. La même variable peut être enregistrée dans un fichier `.env` local non suivi par Git. Le proxy doit transmettre le vrai en-tête `Host` autorisé. Ne pas autoriser `*`.
3. Configurer au frontal une limite de taille des requêtes, un délai maximum de réception des corps et des en-têtes, ainsi qu'une limitation du débit et des connexions. Prévoir que toute une classe peut partager une seule adresse IP publique : dimensionner ces limites à partir d’un essai simultané réel. La limite de 16 Ko de l’application et les limites Docker ne remplacent pas ces protections du frontal ni une protection contre les attaques distribuées.
4. Servir tous les fichiers en HTTPS et activer HSTS au frontal une fois le domaine et le certificat validés. L’application ne fait pas confiance aux en-têtes `X-Forwarded-*`. Si une intégration future nécessite cette confiance, l’accorder uniquement aux adresses des proxies connus, jamais à `*`.
5. Choisir une politique de mises à jour de l’image Python et des dépendances, reconstruire l’image après mise à jour, et vérifier l’application avant de la remettre en service. Le `Dockerfile` fixe le digest de la base auditée : actualiser explicitement ce digest et la version de `pip` lors des mises à jour. Il applique également les mises à jour Debian à la construction ; pour les récupérer même si la couche Docker est en cache, utiliser `docker compose build --pull --no-cache`, puis redémarrer et refaire le scan. `--pull` seul ne remplace pas un digest fixé.

Les interfaces `/docs`, `/redoc` et `/openapi.json` sont désactivées. Les fichiers CSS et JavaScript viennent de l’application elle-même. Une politique CSP limite le chargement des ressources, l’intégration dans une iframe est interdite, et les réponses désactivent la détection automatique des types de fichiers et l’envoi du référent.

## Modifier ou ajouter un quiz

Les questions sont dans `data/quizzes/`, avec un fichier JSON par quiz. Le catalogue `data/catalog.json` définit les titres, les niveaux, les objectifs et les aides. Chaque question contient :

| Champ | Rôle |
| --- | --- |
| `id` | Identifiant entier positif unique dans ce quiz. |
| `label` | Notion affichée et utilisée pour regrouper le bilan (ex. `Imparfait`, `Accords`). |
| `prompt` | Question posée à l’élève. |
| `before` | Texte avant l’élément à analyser. |
| `focus` | Élément mis en évidence : verbe, mot, groupe, proposition ou emplacement à compléter. |
| `after` | Texte après l’élément à analyser. |
| `options` | Quatre choix, chacun avec un `id` (`a`, `b`, `c`, `d`) et un `label`. |
| `answer` | Identifiant de la bonne réponse. |
| `explanation` | Explication justifiée par les indices de la phrase ou une manipulation. |

Conserver les espaces dans `before` et `after`. Les questions et le catalogue sont validés au démarrage. Pour ajouter un quiz, créer `data/quizzes/mon-quiz.json` puis son entrée dans `data/catalog.json` avec le même `id`, un `level` (`4e`, `3e` ou `seconde`), `title`, `description`, `eyebrow`, une liste `objectives` et une liste `help` contenant des objets `title`/`text`. Les identifiants de quiz utilisent seulement lettres minuscules non accentuées, chiffres et tirets.

La liste du catalogue détermine les quiz accessibles. Les chemins de fichiers ne sont jamais construits à partir d’une entrée HTTP. Après modification, redémarrer Python ou reconstruire Docker. Les tests de catalogue décrivent les six séries actuelles : les adapter si le catalogue évolue.

## Routes HTTP

| Route | Rôle |
| --- | --- |
| `GET /` | Accueil : niveaux et catalogue. |
| `GET /niveaux/{level_id}` | Quiz de 4e, 3e ou seconde. |
| `GET /quiz/{quiz_id}` | Questionnaire choisi. |
| `GET /programmes` | Progression, références officielles et dates d’application. |
| `GET /health` | État de santé : `{"status":"ok"}`. |
| `POST /api/quizzes/{quiz_id}/check` | Envoyer `{"question_id":1,"answer":"a"}` pour recevoir la correction et l’explication du quiz choisi. |
| `POST /api/quizzes/{quiz_id}/submit` | Envoyer `{"answers":{"1":"a","2":"b",...}}` pour recevoir le bilan de ce quiz. |

Les routes historiques `/api/check` et `/api/submit` restent compatibles avec le premier quiz de 4e. L’interface utilise les routes identifiant explicitement le quiz. Dans la version FastAPI, les solutions ne sont pas incluses dans les pages initiales. Un identifiant de quiz inconnu renvoie 404.

## Structure

```text
app.py                 Application FastAPI, validation et correction
requirements*.txt      Dépendances Python
data/catalog.json     Catalogue et aides de chaque quiz
data/quizzes/         Six fichiers de questions et de corrections
templates/            Accueil, questionnaire et page des programmes
static/               CSS, JavaScript et icône
tests/                Tests fonctionnels, contenu et protections HTTP
docs/PROGRAMMES.md    Raccord aux programmes et sources officielles
SECURITY.md           Audit de sécurité et limites avant publication
Dockerfile            Image Python et démarrage Uvicorn
compose.yaml          Lancement Docker
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
