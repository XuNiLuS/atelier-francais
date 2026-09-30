# Sécurité — L’atelier de Madame Daadoun

Ce document décrit l’architecture **entièrement statique** du site. Python et Jinja2 génèrent les pages avant publication ; le navigateur effectue les corrections et calcule les scores. L’hébergeur sert uniquement les fichiers de `dist/`.

**Les anciens audits FastAPI et les scans de son image Python/Debian ne s’appliquent pas à l’image Caddy actuelle.** Ils sont conservés comme archives ci-dessous. Ce document ne présente aucun nouveau résultat de scan Caddy et ne constitue pas une certification d’absence de faille.

## Périmètre et données

Le site ne possède ni API de correction, ni compte élève, ni session applicative côté serveur, ni téléversement, ni base de données. La réponse d’un élève reste dans la mémoire de la page et ne déclenche aucun envoi de réponse au serveur ou à Google Analytics. Recharger la page recommence l’essai ; les réponses et les scores ne sont pas enregistrés par l’application.

Les questions, les bonnes réponses et les explications sont publiques par conception. Le verrouillage d’un choix dans l’interface ne protège pas une note contre la modification du navigateur. **Le site convient à l’entraînement, pas à une évaluation authentifiée.**

Les quiz fonctionnent sans ressource distante. Une mesure d’audience Google Analytics 4 est facultative : le script distant et les requêtes de mesure sont bloqués tant que le visiteur n’a pas accepté. L’hébergement et son éventuel frontal peuvent conserver des adresses IP, des URL et des informations de navigateur dans leurs journaux, indépendamment de ce choix. Leurs règles de collecte et de conservation doivent être examinées pour le service choisi.

## Mesure d’audience facultative

`static/analytics.js` exige à la fois un accord valide, un identifiant GA4 valide, l’origine exacte `https://xunilus.github.io` et le chemin `/atelier-francais` ou un de ses sous-chemins. Les prévisualisations locales, HTTP, les autres hôtes et les projets voisins ne chargent pas la balise, même après un clic sur Accepter. Le code n’envoie aucun signal de consentement à Google avant l’accord et ne conserve pas d’événements à transmettre rétroactivement.

Le choix, accord ou refus, est stocké dans `localStorage` sous une clé propre au chemin du projet, pendant 180 jours au maximum. Une simple visite ne prolonge pas ce délai. Si ce stockage est inaccessible, le choix vaut pour la page ouverte seulement. Les cookies GA4 sont configurés avec le préfixe `atelier`, sans attribut `Domain` (hôte seulement), au chemin `/atelier-francais/`, avec `SameSite=Lax;Secure`, une durée de 180 jours et sans renouvellement automatique à chaque visite. Ces réglages limitent le périmètre des cookies ; ils ne constituent pas une isolation de sécurité entre applications partageant la même origine.

Le bouton **Mes choix de statistiques** permet de retirer l’accord. Le code désactive alors la mesure, supprime les cookies `atelier_ga` du projet, vide sa file locale et recharge la page si la balise avait été chargée. Un retrait dans un autre onglet ou l’expiration du choix déclenche aussi l’arrêt. Cette action n’efface pas les données déjà reçues par Google ; le rechargement efface l’essai en cours comme tout autre rechargement de la page.

Le site envoie explicitement `page_view`, `quiz_start` et `quiz_complete`. Les événements de quiz contiennent seulement `education_level`, `quiz_id` et `quiz_theme`, issus du catalogue. Les vues de page ajoutent le niveau lorsqu’il existe et, sur les pages de quiz, l’identifiant et le thème. Les réponses, corrections consultées et notes ne sont pas transmises comme données d’événements. Les URL envoyées par le code excluent les paramètres et fragments ; le référent est vide. Le titre transmis est construit à partir du nom du site, du niveau et du thème disponibles dans le catalogue, sans lire le titre du document ni les réponses. Les événements automatiques GA4 de visite, de session et d’engagement restent possibles après accord, même lorsque les mesures améliorées sont désactivées. Google reçoit aussi des informations techniques et des identifiants de navigateur : **la collecte n’est pas totalement anonyme**.

Les mesures améliorées du flux ont été désactivées dans l’interface GA4 ; Google Signals et la personnalisation publicitaire sont désactivés dans le code. L’ajout de cette balise introduit une dépendance à du JavaScript distant, dont les évolutions et le comportement réel doivent être surveillés. Le [guide Analytics](docs/ANALYTICS.md) précise les identifiants, la lecture des rapports et les contrôles à reproduire. La page publique `/confidentialite/` présente ces informations aux visiteurs. Ces réglages techniques ne constituent pas une certification de conformité juridique ou CNIL.

## Construction et rendu

`quiz_data.py` vérifie la structure du catalogue et des questions avant la génération. Les fichiers de contenu et les modèles sont des sources de confiance maintenues dans le dépôt : ils ne sont pas fournis par les visiteurs.

Jinja2 échappe le texte HTML et sérialise les données embarquées avec son filtre JSON. Le JavaScript crée les éléments de réponse avec des insertions textuelles, sans interpréter les libellés comme du HTML. La CSP autorise les scripts du site et la seule URL de chargement `https://www.googletagmanager.com/gtag/js`, sans `unsafe-inline` ni `unsafe-eval`. Les styles restent locaux ; les connexions et images de mesure sont limitées aux hôtes Google explicitement listés dans la configuration. Cette autorisation CSP ne vaut pas consentement : le script local contrôle le chargement et les envois. Ces protections doivent être conservées lors de l’ajout de questions ou de fonctionnalités.

L’exporteur copie les pages et ressources explicitement prévues. Il ne publie ni code Python, ni historique Git, ni rapports d’audit, ni fichier local `.env`. Publier **le contenu de `dist/` seulement**. Les corrigés font néanmoins partie des pages générées : leur présence ne doit pas être confondue avec une fuite de secrets.

La chaîne de construction reste à maintenir : dépendances Python de génération, image de construction, actions du workflow et comptes ayant accès au dépôt. Une modification malveillante de ces éléments pourrait produire un site altéré même sans serveur applicatif.

## Protections selon le mode de service

| Mode | Protections et limites |
| --- | --- |
| Docker avec Caddy | Le serveur applique sa configuration d’en-têtes HTTP. La configuration Compose restreint le conteneur. Le port livré est HTTP local, sans certificat public. |
| Cloudflare Pages | Le fichier `_headers` généré définit les protections HTTP pour les fichiers statiques. Vérifier leur présence après déploiement. |
| GitHub Pages | La CSP et la politique de référent présentes dans le HTML restent utilisables. Le fichier `_headers` n’est pas appliqué par GitHub Pages. Les protections nécessitant un en-tête HTTP personnalisé ne sont donc pas garanties par ce dépôt sur cet hébergeur. |
| `python -m http.server` | Prévisualisation locale uniquement. Ce serveur n’applique pas `_headers` et n’est pas prévu pour une mise en production. |

En particulier, **`frame-ancestors` ne fonctionne pas dans une CSP définie par balise meta**. L’interdiction d’affichage en iframe exige un véritable en-tête HTTP et ne doit pas être annoncée comme assurée sur GitHub Pages. Une CSP meta ne remplace pas non plus les en-têtes `X-Content-Type-Options`, `Permissions-Policy` ou HSTS. Voir la [spécification CSP](https://w3c.github.io/webappsec-csp/#directive-frame-ancestors) et les [en-têtes Cloudflare Pages](https://developers.cloudflare.com/pages/configuration/headers/).

## Conteneur Caddy

La construction Docker comporte deux étapes : Python fabrique `dist/`, puis l’image officielle Caddy reçoit seulement le site généré et sa configuration. L’environnement Python de génération et les sources du dépôt ne sont pas présents dans l’image de service.

Les restrictions prévues sont :

- utilisateur non root `10001:10001`, fichiers du site en lecture seule et absence de capacités Linux (la capacité réseau portée par le binaire Caddy est retirée à la construction) ;
- `/data` en mémoire temporaire, limité à 16 Mio, sans exécution ni suid, pour la maintenance interne de Caddy ; aucune donnée élève et aucun stockage persistant ;
- interdiction de nouveaux privilèges, administration Caddy désactivée et pas de sauvegarde automatique de sa configuration ;
- aucune journalisation d’accès configurée ; les journaux de fonctionnement restent visibles par l’exploitant ;
- limites Compose de 256 Mio de RAM, 1 CPU et 64 processus ; rotation des journaux Docker à 3 × 10 Mo ;
- liaison à `127.0.0.1:8000` sur la machine hôte et contrôle de santé par `GET /`.

Un hébergeur qui utilise uniquement le `Dockerfile` n’applique pas nécessairement les réglages de `compose.yaml`. Les restrictions doivent alors être reproduites et vérifiées dans sa configuration. Les quotas ne remplacent pas une protection contre la saturation du réseau.

## Avant une ouverture publique

Pour un hébergement statique managé, publier uniquement l’export, activer HTTPS et vérifier le comportement réel du site et de ses en-têtes sur l’adresse fournie. Le [guide de déploiement](docs/DEPLOIEMENT.md) détaille les deux solutions documentées.

Pour une machine virtuelle publique, la configuration locale ne suffit pas. Il faut définir le domaine, un frontal HTTPS et le renouvellement du certificat, le pare-feu et l’accès au port 8000 depuis ce frontal seulement. Configurer aussi les limites de connexions et de débit, la protection contre les abus et la politique de journaux. Une classe peut partager une seule adresse IP : tester l’accès simultané avant de fixer un quota par IP. Aucun frontal public ni certificat n’est configuré ici.

Maintenir l’OS hôte, Docker, Caddy et les outils de génération. Reconstruire après les mises à jour, tester l’image produite et analyser **cette image précise**, avec son architecture, son identifiant et une base d’avis à jour. Si une base Docker est fixée par digest, `--pull` ne remplace pas ce digest : il faut également actualiser la référence dans le `Dockerfile`.

Si des comptes, des résultats persistants, une interface d’administration ou des téléversements sont ajoutés, réexaminer l’authentification, les autorisations, les entrées, la conservation des données et les protections CSRF avant publication.

## Vérification de la migration statique

Le 29 septembre 2026 : 14 tests automatisés réussis sur les contenus, les exports et l’échappement HTML/JSON. Construction Docker et état de santé vérifiés ; l’image finale ne contient pas Python ni les sources des quiz. Les en-têtes HTTP sont présents sur les pages, ressources et erreurs 404 testées. Les chemins de sources, données JSON et ancienne API sont refusés. Un parcours de 20 réponses dans le navigateur donne le score attendu et ses 20 corrections, sans erreur JavaScript ou CSP observée. Ces contrôles fonctionnels ne sont pas un scan de vulnérabilités.

## Vérifications à reproduire

Pour l’intégration Analytics, le 30 septembre 2026 : **19 tests Python et 17 tests JavaScript réussis**. Les trois dimensions personnalisées ont été enregistrées dans GA4. Ces contrôles précèdent la publication de cette intégration ; ils ne constituent pas une preuve de réception d’événements en production.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/analytics.test.cjs
python scripts/export_static.py
docker compose build --pull --no-cache
docker compose up -d --wait
docker compose ps
```

Les tests JavaScript nécessitent Node.js 22 et n’installent aucun paquet npm ; ils s’exécutent sans requête réseau. Ils vérifient notamment l’absence de mesure sans accord et hors production, l’expiration, le retrait, le périmètre des cookies et les données admises dans les événements. Le workflow GitHub Pages les exécute avant la publication. Ces tests simulés ne prouvent pas la réception d’événements par Google.

Compléter ces contrôles par un essai dans le navigateur : navigation entre niveaux, corrections correctes et incorrectes, bilan et nouvel essai, puis refus, accord et retrait de la mesure. Examiner les requêtes réelles, les réponses HTTP du service choisi, la non-publication de `/.git/config`, `/.env` et des sources, ainsi que les restrictions effectives du conteneur. Le [guide Analytics](docs/ANALYTICS.md) décrit la vérification séparée dans GA4.

Un inventaire des dépendances de construction ne suffit pas à analyser l’image finale Caddy. Inversement, l’analyse du conteneur ne couvre pas les outils et comptes qui construisent le site, ni les serveurs de GitHub ou de Cloudflare. Pour tout nouveau scan, conserver l’image exacte, l’architecture, la date, la version du scanner et celle de sa base d’avis. Ne pas ignorer les avis dépourvus de correctif.

## Archives de l’ancien audit FastAPI

L’audit du 29 septembre 2026 concernait l’ancienne application Python/FastAPI et une image Linux ARM64 identifiée dans les rapports. Les anciens nombres de tests, inventaires, résultats de vulnérabilités et vérifications de délais décrivent cette version historique uniquement. Ils ne prouvent ni la présence ni l’absence de vulnérabilités dans le site statique, Caddy ou une future reconstruction.

Les pièces sont conservées sans modification :

- [Inventaire et scan initiaux](reports/security/dependencies-initial.json).
- [Inventaire et scan finaux de l’ancienne image](reports/security/dependencies-final.json).
- [Comparaison avant/après de cet audit](reports/security/dependencies-delta.json).

Ces rapports ne sont pas inclus dans `dist/` ni dans l’image servant le site. Aucun rapport de scan Caddy n’est joint à cette migration.
