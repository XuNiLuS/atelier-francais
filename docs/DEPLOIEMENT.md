# Publier le site statique

Le site produit des fichiers HTML, CSS et JavaScript. Les six quiz conservent leurs corrections immédiates, explications et scores ; le navigateur effectue tout le calcul. Python et Jinja2 interviennent seulement pendant la construction. Il n’y a aucune API ni application Python à démarrer chez l’hébergeur.

## Préparer et essayer les fichiers

Depuis le dossier du projet, dans un environnement Python activé :

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/export_static.py
python -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000). Si Docker utilise ce port, l’arrêter avant la prévisualisation. Pour un site publié sous un chemin comme `/atelier-francais`, passer `--base-path /atelier-francais` à l’exporteur ; le workflow GitHub prépare ce chemin automatiquement.

Publier **uniquement le contenu du dossier `dist/`**. Il contient les pages, les ressources statiques et les fichiers de configuration d’hébergement. Les sources Python, l’historique Git, les rapports et les fichiers privés ne sont pas copiés. Modifier les sources puis reconstruire, sans éditer les fichiers générés. L’exporteur refuse d’écraser un dossier non vide qui n’est pas un de ses anciens exports.

## GitHub Pages

GitHub Pages sert les fichiers statiques sans mise en veille d’une application. Avec GitHub Free, le dépôt source doit être **public** : son code et son historique deviennent consultables. Choisir cette visibilité avant de créer ou publier le dépôt. Voir les [plans compatibles avec Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

Le workflow [.github/workflows/pages.yml](../.github/workflows/pages.yml) teste le projet, construit le site et publie `dist/` après chaque push sur `main`. Il utilise les permissions temporaires de GitHub Actions, sans jeton personnel à placer dans les secrets.

Après choix de la visibilité :

1. Créer le dépôt GitHub, puis y pousser le dépôt local.
2. Dans **Settings → Pages → Build and deployment**, sélectionner **GitHub Actions**.
3. Lancer **Publier les quiz sur GitHub Pages** depuis **Actions**, ou pousser un nouveau commit sur `main`.
4. Attendre la réussite et ouvrir l’adresse affichée par GitHub.
5. Vérifier HTTPS, les trois niveaux, une correction et un bilan complet.

Les commits conservés seulement sur l’ordinateur ne publient rien. La présence du workflow ne crée pas de dépôt distant. Les publications suivantes suivent les push sur `main`. Le service reste soumis aux [limites de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## Cloudflare Pages : conserver un dépôt privé

Cloudflare Pages permet de connecter le dépôt GitHub tout en conservant son code privé. Le site généré et ses corrigés restent publics. Un compte Cloudflare est nécessaire ; limiter l’autorisation GitHub au dépôt concerné.

Utiliser les réglages suivants :

| Réglage | Valeur |
| --- | --- |
| Framework | Aucun |
| Branche de production | `main` |
| Commande de construction | `python -m pip install -r requirements.txt && python -m unittest discover -s tests -v && python scripts/export_static.py` |
| Dossier de sortie | `dist` |

Aucun Worker, aucune Function et aucune base de données ne sont nécessaires. Après construction, ouvrir l’adresse `pages.dev` affichée par le service et vérifier le parcours élève. Les fichiers statiques ne nécessitent pas de réveiller une application ; l’offre gratuite conserve des quotas, notamment de construction. Consulter les [limites actuelles](https://developers.cloudflare.com/pages/platform/limits/) avant l’activation et les règles de l’[intégration GitHub](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/).

Le fichier `_headers` généré est destiné à cette plateforme. Vérifier les protections réellement renvoyées après publication ; les [règles d’en-têtes Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/headers/) concernent les réponses statiques.

## Docker et machine publique

Docker reste disponible pour travailler localement ou servir le site sur une machine choisie :

```sh
docker compose up --build -d
```

Une étape Python construit les fichiers ; l’image finale Caddy les sert sur le port 8000. La configuration fournie écoute en HTTP et expose le port seulement sur `127.0.0.1`. Elle n’installe pas de certificat public et ne constitue pas une configuration complète de machine virtuelle sur Internet.

Pour ce type d’hébergement, il faudra configurer séparément le domaine, un frontal HTTPS avec renouvellement du certificat, le pare-feu, la limitation des abus et les mises à jour de la machine et du conteneur. Le port 8000 doit rester accessible seulement au frontal. Le serveur Python `http.server` est réservé à la prévisualisation locale.

## Sécurité et limites

Les réponses et explications figurent dans les pages publiques : le score sert à l’entraînement et peut être modifié dans le navigateur. Aucun compte élève, cookie ni stockage de résultats n’est ajouté. L’hébergeur peut conserver les adresses IP dans ses journaux, même si le dépôt source est privé.

Les pages conservent l’échappement HTML/JSON, les insertions de texte et la CSP. **GitHub Pages n’applique pas `_headers`** : les protections nécessitant des en-têtes personnalisés, notamment l’interdiction d’affichage en iframe, ne doivent pas être supposées actives. Une CSP en balise meta ne peut pas imposer `frame-ancestors`. Cloudflare Pages utilise le fichier `_headers` pour les fichiers statiques ; Caddy utilise sa propre configuration HTTP.

Les anciens scans Python/FastAPI ne décrivent ni l’image Caddy actuelle ni les serveurs des hébergeurs. Consulter [SECURITY.md](../SECURITY.md) pour les protections actuelles, les vérifications à reproduire et les liens vers ces archives. Toute future fonction de comptes ou d’enregistrement des résultats demandera une nouvelle analyse.

## Références officielles

- [Fonctionnement et plans GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
- [Workflows de déploiement GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
- [Intégration GitHub de Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/).
- [En-têtes Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/headers/).
- [Limites Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/).
- [Portée et limites du serveur Python `http.server`](https://docs.python.org/3/library/http.server.html).
