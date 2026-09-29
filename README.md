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

L’application convient à un entraînement libre : aucun compte, cookie de session, enregistrement de résultat ou donnée personnelle n’est demandé. Un visiteur peut demander les corrections directement à l’API et recommencer ; le score n’est pas une note d’évaluation authentifiée. Le serveur d’hébergement et son proxy peuvent cependant conserver des adresses IP dans leurs journaux : minimiser ces journaux et leur durée de conservation.

L’audit et ses limites sont détaillés dans [SECURITY.md](SECURITY.md). Avant l’ouverture au public :

1. Placer l’application derrière le frontal HTTPS de l’hébergeur ou un reverse proxy avec certificat valide. Garder le port 8000 accessible seulement depuis ce frontal ; ne pas publier directement Uvicorn sur Internet. Aucun hébergement n’est configuré par ce dépôt.
2. Définir les noms de domaine exacts dans `ALLOWED_HOSTS`, sans protocole, chemin ni port. Conserver `127.0.0.1` pour le contrôle de santé. Exemple : `ALLOWED_HOSTS=localhost,127.0.0.1,francais.exemple.fr docker compose up --build -d`. La même variable peut être enregistrée dans un fichier `.env` local non suivi par Git. Le proxy doit transmettre le vrai en-tête `Host` autorisé. Ne pas autoriser `*`.
3. Configurer au frontal une limite de taille des requêtes, un délai maximum de réception des corps et des en-têtes, ainsi qu'une limitation du débit et des connexions. Prévoir que toute une classe peut partager une seule adresse IP publique : dimensionner ces limites à partir d’un essai simultané réel. La limite de 16 Ko de l’application et les limites Docker ne remplacent pas ces protections du frontal ni une protection contre les attaques distribuées.
4. Servir tous les fichiers en HTTPS et activer HSTS au frontal une fois le domaine et le certificat validés. L’application ne fait pas confiance aux en-têtes `X-Forwarded-*`. Si une intégration future nécessite cette confiance, l’accorder uniquement aux adresses des proxies connus, jamais à `*`.
5. Choisir une politique de mises à jour de l’image Python et des dépendances, reconstruire l’image après mise à jour, et vérifier l’application avant de la remettre en service. Le `Dockerfile` fixe le digest de la base auditée : actualiser explicitement ce digest et la version de `pip` lors des mises à jour. Il applique également les mises à jour Debian à la construction ; pour les récupérer même si la couche Docker est en cache, utiliser `docker compose build --pull --no-cache`, puis redémarrer et refaire le scan. `--pull` seul ne remplace pas un digest fixé.

Les interfaces `/docs`, `/redoc` et `/openapi.json` sont désactivées. Les fichiers CSS et JavaScript viennent de l’application elle-même. Une politique CSP limite le chargement des ressources, l’intégration dans une iframe est interdite, et les réponses désactivent la détection automatique des types de fichiers et l’envoi du référent.

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
