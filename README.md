# L’atelier de Madame Daadoun

**Site public : [xunilus.github.io/atelier-francais](https://xunilus.github.io/atelier-francais/)** · [Dépôt GitHub](https://github.com/XuNiLuS/atelier-francais)

Des quiz de grammaire pour les **4e, 3e et secondes générales et technologiques**, avec une difficulté progressive. La page d’accueil présente les niveaux et les thèmes. Chaque quiz contient **20 questions**, soit **320 questions réparties en 16 quiz** dans cette version.

| Niveau | Quiz disponibles |
| --- | --- |
| 4e | Temps du récit ; conjugaison du passé simple ; classes, fonctions et accords ; phrase complexe ; paroles rapportées ; temps composés et voix passive |
| 3e | Conditionnel et hypothèses ; subjonctif ; paroles rapportées ; accords complexes ; phrase complexe |
| Seconde GT | Temps, aspect et concordance ; modes et modalisation ; accords ; phrase complexe ; syntaxe et propositions relatives |

Au collège, le contenu anticipe le **nouveau programme officiel publié en mars 2026**, applicable en 4e à la rentrée **2027-2028** et en 3e à la rentrée **2028-2029**. Le programme de seconde est celui de 2019 modifié en 2020. Les sources et les choix pédagogiques sont décrits dans [docs/PROGRAMMES.md](docs/PROGRAMMES.md) et sur la page `/programmes/`. Ces premiers quiz couvrent une sélection de notions, pas l’ensemble du programme.

L’élève choisit une réponse puis clique sur **Vérifier ma réponse** : il voit si elle est correcte, la bonne réponse et une explication. La réponse est alors figée pour cet essai. Il peut revenir sur les questions, lire son bilan sur 20 et recommencer. Chaque quiz a ses propres questions, corrections et aides.

Le site est entièrement **statique : HTML, CSS et JavaScript**. Python valide les données et Jinja2 génère les pages avant publication. La correction et le score sont calculés dans le navigateur, sans API. Aucun compte, cookie, base de données ni dépendance distante n’est nécessaire. La progression reste dans la page ouverte : changer de quiz ou recharger la page commence un nouvel essai.

## Démarrer avec Docker

Depuis le dossier du projet, avec Docker et Docker Compose installés :

```sh
docker compose up --build
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Arrêter avec `Ctrl+C`, puis `docker compose down` pour supprimer le conteneur. Pour le laisser tourner en arrière-plan :

```sh
docker compose up --build -d
docker compose logs -f
```

La construction utilise Python pour générer le site. L’image finale contient **Caddy et les fichiers publiables**, sans serveur Python. Caddy sert le site sur le port 8000 ; son contrôle de santé consulte la page d’accueil `/`.

Le conteneur s’exécute avec l’utilisateur non root `10001:10001`, un système de fichiers en lecture seule, aucune capacité Linux et l’interdiction d’acquérir de nouveaux privilèges. L’administration Caddy et la sauvegarde automatique de sa configuration sont désactivées. Aucun journal d’accès n’est configuré. Les quiz ne nécessitent aucun volume de données persistant. Un espace temporaire en mémoire de 16 Mio est réservé à la maintenance interne de Caddy dans `/data` ; les pages restent en lecture seule. Docker Compose fixe 256 Mio de mémoire, 1 CPU, 64 processus et une rotation des journaux de fonctionnement de 3 × 10 Mo.

Après une modification, reconstruire avec `docker compose up --build -d`. Le `Dockerfile` et `.dockerignore` limitent les fichiers utilisés et publiés ; adapter leurs listes si la structure du projet évolue.

### Accès depuis la classe

Par défaut, le port n’est accessible que sur l’ordinateur qui lance Docker. Pour les appareils du même réseau, remplacer la ligne des ports dans `compose.yaml` par :

```yaml
      - "0.0.0.0:8000:8000"
```

Recréer le conteneur, puis communiquer aux élèves `http://192.168.1.25:8000`, en remplaçant cette adresse par l’IP réelle de l’ordinateur. Le pare-feu doit autoriser ce port depuis le réseau local. Aucune redirection de port sur la box n’est nécessaire. Cette configuration HTTP concerne le réseau local ; la publication sur Internet nécessite HTTPS.

## Construire et prévisualiser avec Python

Utiliser Python 3.10 ou plus récent. Sur macOS ou Linux :

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/export_static.py
python -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000), puis arrêter avec `Ctrl+C`. Si Docker utilise déjà le port 8000, l’arrêter avant de lancer cette prévisualisation.

Sur Windows PowerShell, créer l’environnement avec `py -m venv .venv`, puis l’activer avec `.venv\Scripts\Activate.ps1` avant les commandes d’installation et de construction.

Jinja2 est la seule dépendance Python déclarée ; la validation des questions utilise la bibliothèque standard. Après chaque modification des sources, relancer `python scripts/export_static.py`. Ne pas modifier directement `dist/`, qui sera régénéré. Le serveur `http.server` sert uniquement à la prévisualisation locale ; il n’est [pas recommandé pour la production](https://docs.python.org/3/library/http.server.html).

## Publier le site

Publier **uniquement le contenu de `dist/`**, jamais le dossier entier du projet. Le [guide de déploiement](docs/DEPLOIEMENT.md) explique GitHub Pages et Cloudflare Pages : ces hébergeurs servent les fichiers statiques sans démarrer une application Python à chaque visite.

```sh
python scripts/export_static.py
```

Pour une URL sous un chemin comme `/atelier-francais`, construire avec `python scripts/export_static.py --base-path /atelier-francais`. Le workflow GitHub Pages calcule ce préfixe automatiquement.

Les corrections figurent dans les fichiers publics et peuvent être consultées dans le navigateur. **Les scores servent à l’entraînement**, pas à une évaluation authentifiée. L’hébergeur peut enregistrer les adresses IP dans ses journaux. Les protections, leurs limites et le statut des anciens audits sont décrits dans [SECURITY.md](SECURITY.md).

Le conteneur Caddy livré ici écoute en HTTP pour l’usage local ou derrière un frontal. Sur une machine publique, prévoir séparément le domaine, HTTPS et son renouvellement, le pare-feu, les protections contre les abus et les mises à jour. Ce dépôt ne configure ni machine publique ni certificat.

## Modifier ou ajouter un quiz

Les questions se trouvent dans `data/quizzes/`, avec un fichier JSON par quiz. Le catalogue `data/catalog.json` définit les titres, les niveaux, les objectifs et les aides. Chaque question contient :

| Champ | Rôle |
| --- | --- |
| `id` | Identifiant entier positif unique dans ce quiz. |
| `label` | Notion affichée et utilisée pour regrouper le bilan. |
| `prompt` | Question posée à l’élève. |
| `before` | Texte avant l’élément à analyser. |
| `focus` | Élément mis en évidence : verbe, mot, groupe, proposition ou emplacement à compléter. |
| `after` | Texte après l’élément à analyser. |
| `options` | Quatre choix, chacun avec un `id` (`a`, `b`, `c`, `d`) et un `label`. |
| `answer` | Identifiant de la bonne réponse. |
| `explanation` | Explication justifiée par les indices ou une manipulation. |

Conserver les espaces dans `before` et `after`. Les questions et le catalogue sont validés **à la construction** par `quiz_data.py`. Pour ajouter un quiz, créer `data/quizzes/mon-quiz.json` puis son entrée dans `data/catalog.json` avec le même `id`, un `level` (`4e`, `3e` ou `seconde`), `title`, `description`, `eyebrow`, une liste `objectives` et une liste `help` contenant des objets `title`/`text`. Les identifiants utilisent uniquement des lettres minuscules non accentuées, des chiffres et des tirets.

La liste du catalogue détermine les quiz générés. Après modification, reconstruire le site avec Python ou Docker. Les tests vérifient les 16 séries actuelles, leurs 320 corrections et leurs liens : adapter les effectifs attendus si le catalogue évolue.

## Pages générées

| Chemin | Contenu |
| --- | --- |
| `/` | Accueil : niveaux et catalogue. |
| `/niveaux/{level_id}/` | Quiz de 4e, 3e ou seconde. |
| `/quiz/{quiz_id}/` | Questionnaire choisi et corrections dans le navigateur. |
| `/programmes/` | Progression, références officielles et dates d’application. |
| `/404.html` | Page d’erreur pour l’hébergeur. |

Il n’y a aucune route API ni point de santé JSON. Le contrôle de santé Docker vérifie simplement que la page d’accueil répond.

## Structure

```text
quiz_data.py              Chargement et validation du catalogue avec la bibliothèque standard
scripts/export_static.py  Génération HTML avec Jinja2
requirements.txt          Dépendance de construction Python
data/catalog.json         Catalogue et aides
data/quizzes/             Seize fichiers de questions et corrections
templates/                Modèles HTML
static/                   CSS, JavaScript et icône
dist/                     Site généré, seul dossier à publier
tests/                    Tests unittest de données et de génération
docs/PROGRAMMES.md        Raccord aux programmes officiels
docs/DEPLOIEMENT.md       Publication du site statique
SECURITY.md                Sécurité actuelle et archives de l’audit précédent
Dockerfile                Construction Python, puis service statique Caddy
Caddyfile                 Service HTTP local et en-têtes de protection
compose.yaml              Lancement et restrictions Docker
```

## Vérifier

Après activation de l’environnement Python :

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/export_static.py
```

Ouvrir ensuite le site pour vérifier la navigation, une réponse correcte, une réponse incorrecte, le bilan et le redémarrage d’un quiz. Pour Docker, consulter l’état avec `docker compose ps`.

## Git

Le dépôt public est [XuNiLuS/atelier-francais](https://github.com/XuNiLuS/atelier-francais). La branche `main` est reliée à `origin/main` ; un `git push` déclenche les tests et la publication GitHub Pages. Les environnements virtuels, caches, exports générés et fichiers `.env` sont exclus du suivi. L’utilisation locale reste indépendante de GitHub.
