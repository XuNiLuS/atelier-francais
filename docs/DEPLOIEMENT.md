# Publication gratuite sans serveur à réveiller

Le site peut être exporté en HTML, CSS et JavaScript. Les six quiz gardent leurs corrections immédiates, explications et scores ; le navigateur effectue la correction. Aucun serveur Python n’est nécessaire en ligne. FastAPI et Docker restent utilisables en local avec les mêmes contenus et templates.

## Essayer l’export

```sh
python -m pip install -r requirements.txt
python scripts/export_static.py
python -m http.server 8080 --bind 127.0.0.1 --directory dist
```

Ouvrir http://127.0.0.1:8080. Pour un site publié sous un chemin comme `/atelier-francais`, passer `--base-path /atelier-francais` à l’exporteur. Le workflow GitHub calcule ce chemin automatiquement.

Publier **uniquement le dossier `dist/`**. Il contient 12 pages, les trois ressources statiques et les fichiers de configuration d’hébergement. Le code Python, l’historique Git, les rapports et les fichiers locaux ne sont pas copiés dans cet export. Ne pas modifier les fichiers générés : modifier les sources, puis régénérer l’export. L’outil refuse d’écraser un dossier non vide qui n’est pas un de ses anciens exports.

## GitHub Pages : utiliser le compte GitHub existant

GitHub Pages sert directement les fichiers statiques, sans mise en veille d’une application. Avec GitHub Free, le dépôt source doit être **public**. Cela rend son code et son historique consultables, en plus du site : choisir explicitement cette visibilité avant de créer ou de publier le dépôt. Le plan gratuit reste soumis aux limites de GitHub Pages et ne constitue pas une garantie de disponibilité.

Le fichier [.github/workflows/pages.yml](../.github/workflows/pages.yml) est prêt : il teste le projet, génère le site et le publie après chaque push sur `main`. Aucun jeton personnel n’est nécessaire dans les secrets du projet ; le workflow utilise les permissions temporaires de GitHub Actions.

Première mise en ligne, après choix de la visibilité :

1. Créer le dépôt GitHub, par exemple `atelier-francais`, puis y pousser le dépôt local.
2. Dans **Settings → Pages → Build and deployment**, sélectionner **GitHub Actions**.
3. Depuis **Actions**, lancer le workflow **Publier les quiz sur GitHub Pages**, ou pousser un nouveau commit sur `main`.
4. Attendre la réussite du déploiement et ouvrir l’adresse affichée par GitHub, sans la deviner à partir du nom du compte.
5. Vérifier HTTPS, les trois niveaux, une correction, un bilan complet et les liens de navigation.

Les publications suivantes sont automatiques à chaque push sur `main`. Un commit qui reste seulement sur l’ordinateur ne publie rien. La préparation locale du workflow ne crée aucun dépôt distant et ne met pas encore le site en ligne.

## Alternative : Cloudflare Pages, avec code privé

Pour conserver un dépôt GitHub privé avec un hébergement statique gratuit, Cloudflare Pages est une autre possibilité ; elle nécessite un compte Cloudflare. Autoriser seulement le dépôt concerné dans l’intégration GitHub.

- Framework : aucun.
- Commande de construction : `pip install -r requirements.txt && python scripts/export_static.py`.
- Dossier de sortie : `dist`.
- Domaine fourni : une adresse `pages.dev`, affichée après la création du projet.
- Aucun Worker, aucune Function ni base de données ne sont nécessaires.

Les fichiers statiques ne demandent aucun réveil de serveur. L’offre gratuite comporte notamment un quota de constructions ; vérifier les conditions affichées avant l’activation. Le fichier `_headers` généré est pris en charge par Cloudflare Pages.

## Sécurité et limites de cette version

Les réponses et explications sont présentes dans les fichiers publics. C’est adapté à l’entraînement ; le score ne constitue pas une note d’examen authentifiée. Aucun compte élève, cookie ni stockage de résultats n’est ajouté. L’hébergeur peut enregistrer les adresses IP dans ses journaux.

L’export conserve l’échappement HTML/JSON et les insertions de texte sûres. Une CSP et une politique de référent sont définies dans les pages. GitHub Pages n’applique pas notre fichier `_headers` : les protections qui exigent de véritables en-têtes HTTP, notamment l’interdiction d’affichage en iframe, ne doivent pas être supposées actives sur cet hébergeur. Cloudflare Pages peut appliquer les en-têtes fournis.

Aucun conteneur Docker ni API de correction ne tourne sur l’hébergement statique. Les vérifications système décrites dans [SECURITY.md](../SECURITY.md) concernent la variante FastAPI/Docker et son image identifiée, pas les serveurs de GitHub ou Cloudflare. Si des comptes ou des résultats persistants sont ajoutés, revoir l’architecture et la sécurité avant publication.

## Références officielles

- [GitHub Pages et plans compatibles](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Workflow GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Limites GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Limites Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/)
- [Fichiers statiques Cloudflare Pages](https://developers.cloudflare.com/pages/functions/routing/)
- [En-têtes Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/headers/)
