# Audit de sécurité — L’atelier des temps

Audit local du 29 septembre 2026, réalisé avant un éventuel hébergement public. Il couvre le code Python et JavaScript, les templates, les dépendances réellement présentes dans l’image Linux ARM64, la configuration Docker et des essais de requêtes hostiles. Aucun service public n’a été déployé ni testé.

**Évolution du catalogue :** la version avec six quiz conserve les protections décrites ici. Ses 40 tests vérifient aussi l’isolation des corrections par quiz, le refus des identifiants inconnus et l’absence d’accès HTTP aux fichiers du catalogue. Les JSON et digests de scan ci-dessous restent ceux de l’image auditée avant cette évolution ; ils ne constituent pas un scan de chaque reconstruction ultérieure. Refaire le scan de l’image retenue pour une publication.

## Conclusion et limites

Les scénarios testés n’ont pas permis de lire les fichiers du serveur, d’exécuter une injection HTML/JavaScript, ni d’obtenir des détails internes dans les réponses. Plusieurs défauts de préparation à Internet ont été corrigés ci-dessous. Cela ne constitue ni une certification ni une garantie d’absence de faille.

**L’ouverture publique reste conditionnée à la configuration du frontal HTTPS et à l’examen des avis résiduels de l’image système.** Les limites du serveur réduisent certains abus ; elles ne protègent pas contre une attaque distribuée ou la saturation du réseau.

## Constats et corrections

| Constat avant l’audit | Portée réelle | Correction appliquée |
| --- | --- | --- |
| Un en-tête `Host` arbitraire est accepté et repris dans les URL absolues CSS/JS. | Empoisonnement de contenu possible avec un proxy/cache mal configuré ; pas d’exploitation directe d’un navigateur démontrée. | Hôtes exacts autorisés via `ALLOWED_HOSTS`, refus des jokers, URLs statiques relatives, redirections automatiques de slash désactivées. |
| Un client peut garder un corps de requête ouvert sans limite de temps. | Risque d’épuisement des connexions/tâches ; la limite de taille seule ne suffit pas. | Lecture limitée à 10 secondes au total et 16 Kio, rejet anticipé des tailles déclarées excessives, concurrence Uvicorn plafonnée à 100. |
| Pas de protections HTTP explicites pour les pages. | Mesures de défense supplémentaires ; aucune injection exploitable constatée dans le rendu existant. | CSP stricte sans `unsafe-inline` ni `unsafe-eval`, refus des iframes, `nosniff`, aucun référent, caméra/micro/géolocalisation interdits. |
| Documentation API interactive publique avec dépendances CDN. | Surface et dépendances navigateur inutiles au QCM, sans secret exposé. | `/docs`, `/redoc`, `/openapi.json` désactivés. |
| Image modifiable, sources détenues par l’utilisateur de service, copie générale du dossier. | Aggravation possible après compromission et risque d’inclure de futurs fichiers privés. | Copie explicite des seuls fichiers nécessaires, sources appartenant à root, service non-root, disque en lecture seule, aucune capability, interdiction de nouveaux privilèges. |
| Pas de quotas de ressources ni de rotation des journaux. | Saturation mémoire/processus/disque en cas d’abus ou de panne. | 256 Mio de RAM, 1 CPU, 64 PID, journaux Docker limités à 3 × 10 Mo ; journaux d’accès Uvicorn désactivés. |
| Avis connus sur l’ancienne image Linux et son installateur `pip`. | Présence signalée par scanners ; les conditions d’exploitation varient selon le paquet et l’architecture. | Base actualisée et fixée par digest, mises à jour Debian, `pip` mis à jour au build puis retiré de l’environnement d’exécution. Voir les résultats de scan conservés. |

Les erreurs internes retournent un message générique. Les détails techniques restent dans les journaux d’erreur accessibles à l’exploitant. Les en-têtes de protection sont aussi ajoutés aux refus d’hôte et aux erreurs de l’application. Les erreurs de transport générées directement par l’hébergeur ou Uvicorn relèvent de leur propre configuration.

## Résultats des scans de dépendances

Image finale ARM64 : `sha256:06cc8ebf9625deee933acf639325fc9cbc22c7007cc4339f253aba17ef730de5`, avec Python 3.12.14 et Debian 13.7. Scan du 29 septembre 2026 à 20:10 UTC ; base d’avis Trivy datée de 19:09 UTC le même jour.

| Mesure | Avant | Après |
| --- | ---: | ---: |
| Distributions Python installées | 17 | 16 |
| Avis Python distincts | 6, tous sur `pip` | 0 |
| Occurrences Debian (paquet × avis) | 256 | 198 |
| Identifiants Debian distincts | 119 | 83 |
| Occurrences Debian critiques | 3 | 0 |
| Occurrences Debian élevées | 57 | 44 |
| Occurrences Debian avec correctif connu | 58 | 0 |

Les 58 occurrences disposant d’un correctif ont été supprimées par les mises à jour. Les **198 occurrences résiduelles correspondent à 83 identifiants distincts**, dont 8 de sévérité élevée, 28 moyenne, 31 faible et 16 inconnue. Elles n’ont pas de version corrigée indiquée dans la base Debian consultée. Plusieurs paquets binaires peuvent partager un même avis ; certains identifiants Debian `TEMP` ne sont pas des CVE. Aucun avis n’a été masqué parce qu’il était sans correctif.

Les huit identifiants de sévérité élevée concernent :

- util-linux : [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) ; opérations de montage et de changement d’espace de noms.
- ACL : [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) ; liens symboliques et permissions.
- ncurses : [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) ; traitement de données de terminal.
- systemd : [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) ; fonctionnalité systemd-homed, avis associé aussi aux bibliothèques issues du paquet source.
- Perl : [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) ; traitement d’archives par Archive::Tar.

Le QCM n’expose pas ces commandes ou traitements. L’exécution non-root, sans capacités et sur disque en lecture seule limite certains scénarios locaux. **Aucune chaîne d’exploitation depuis les routes du QCM n’a été identifiée**, mais le scan ne démontre pas l’inaccessibilité de chaque code vulnérable. Ces avis restent à surveiller et à réexaminer pour l’image réellement publiée.

L’absence d’avis sur les 16 distributions Python installées ne couvre pas intégralement CPython et ses bibliothèques compilées. Des correctifs amont postérieurs à Python 3.12.14 concernent notamment des traitements d’authentification HTTP, d’archives et de XML, qui ne sont pas exposés par le QCM actuel. `pip` n’est plus importable dans l’image finale, mais CPython conserve l’archive inactive `ensurepip/_bundled/pip-25.0.1-py3-none-any.whl` : elle n’est pas une distribution installée et n’entre pas dans ce décompte. Ne pas réinstaller `pip` via `ensurepip` dans le conteneur de production.

Les inventaires et tous les avis détectés, avec versions, sévérités, liens, métadonnées et empreintes des rapports bruts, sont conservés dans [le scan initial](reports/security/dependencies-initial.json), [le scan final](reports/security/dependencies-final.json) et [la comparaison avant/après](reports/security/dependencies-delta.json). Ils sont exclus de l’image applicative.

## Contrôles effectués

- **31 tests automatisés réussis**, dont 15 tests de sécurité : types et champs stricts, corps invalides ou surdimensionnés, en-têtes, hôtes autorisés, erreurs internes, documentation masquée, fichiers sensibles et traversées encodées.
- Injection simulée de `</script><script>…`, attributs `onerror` et `onload` dans les données de questions : HTML échappé, JSON embarqué correctement encodé. Le JavaScript utilise `textContent` et `createTextNode`, sans insertion HTML des réponses.
- La correction reste consultable dans un navigateur sous la CSP, sans erreur JavaScript ni violation CSP observée.
- Une requête HTTP réelle envoyée au ralenti dans Docker reçoit **408 après environ 10 secondes**. Quarante vérifications ciblées des délais sont passées après remplacement d’un middleware qui présentait une annulation intermittente.
- Les refus des chemins `/.env`, `/.git/config`, `/app.py`, `/data/questions.json` et des traversées sous `/static` sont vérifiés. Aucune détection de secret dans les fichiers suivis inspectés ; ce contrôle n’est pas un inventaire de secrets de l’ordinateur ou du futur hébergeur.
- Dans le conteneur : utilisateur non-root, sources détenues par root, écriture refusée par le système de fichiers, capabilities effectives nulles et `NoNewPrivs=1` vérifiés. Pages, API de correction et contrôle de santé fonctionnent.

## Fonctionnement public et données

L’application ne comporte ni compte, ni session, ni téléversement, ni base de données, ni commande système pilotée par une entrée utilisateur. Les réponses sont validées à partir d’identifiants et de quatre choix autorisés. Aucune URL fournie par l’utilisateur n’est chargée par le serveur. Le contrôle de santé contacte seulement son propre serveur HTTP local.

Aucun cookie ni CORS permissif n’est ajouté. Les API n’enregistrent pas de données ; une requête provenant d’un autre site ne peut donc pas modifier une session authentifiée. Si des comptes, résultats persistants, uploads ou fonctions d’administration sont ajoutés, il faudra refaire l’analyse de l’authentification, des autorisations, de CSRF, de la conservation des données et des entrées utilisateur.

**Le score sert à l’entraînement.** Les corrections sont publiques par conception, et un visiteur peut envoyer directement d’autres réponses à l’API ou modifier son navigateur. Le verrouillage du premier choix dans l’interface n’authentifie pas une note d’examen.

Les journaux de l’hébergeur ou de son proxy peuvent contenir les adresses IP et les URL visitées. Leur accès, leur contenu et leur durée de conservation doivent être configurés lors de la mise en ligne. Aucune donnée élève n’a été envoyée à un scanner distant : les analyses d’image ont porté sur une archive locale ; les consultations de vulnérabilités utilisent les noms et versions des paquets.

## Conditions à vérifier chez l’hébergeur

1. HTTPS avec certificat valide et renouvellement, redirection HTTP vers HTTPS, puis HSTS une fois le domaine validé. Ce dépôt ne configure pas de certificat ni de domaine public.
2. Port Uvicorn 8000 joignable uniquement par le frontal. Préserver un `Host` autorisé et configurer le domaine exact dans `ALLOWED_HOSTS`, en conservant `127.0.0.1` pour le contrôle de santé.
3. Limites sur les en-têtes et corps lents, taille des requêtes, connexions et débit au frontal ; protection DDoS de l’hébergeur. Tester avec une classe entière, qui peut partager une seule IP, avant de fixer un quota par IP.
4. Appliquer effectivement les restrictions Docker : un service managé qui utilise uniquement le `Dockerfile` n’applique pas nécessairement `compose.yaml`. Reconfigurer dans ce cas mémoire, CPU, processus, lecture seule, capacités et journaux dans son interface.
5. Examiner les avis système sans correctif, suivre les mises à jour Debian/Python, reconstruire et refaire les scans avant publication et après chaque changement. Une autre architecture d’hébergement, notamment AMD64, doit être scannée séparément.

Uvicorn ignore actuellement les en-têtes `X-Forwarded-*`. Ne pas autoriser globalement leur confiance pour contourner un problème de proxy. Le QCM utilise des chemins relatifs et n’a pas besoin de ces en-têtes pour fonctionner à la racine d’un domaine.

## Refaire les vérifications

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
docker compose build --pull --no-cache
docker compose up -d --wait
```

Le digest de base et la version de `pip` dans `Dockerfile` doivent être actualisés explicitement. Les dépendances transitives peuvent évoluer lors d’une reconstruction : le rapport s’applique à l’image identifiée dans ses métadonnées, pas à toute future image produite par ce dépôt. Les versions fixes et un scanner sans alerte ne dispensent pas de maintenance.

Les scans de référence utilisent **pip-audit 2.10.1** sur l’inventaire exact des distributions de l’image, puis **Trivy 0.74.0** sur une archive `docker save`, sans ignorer les avis sans correctif. Ne pas scanner seulement l’environnement Python de développement : ce n’est pas celui livré par Docker. Conserver la version du scanner, la date de sa base d’avis, l’architecture et le digest de chaque image analysée.

## Références

- [Recommandations OWASP pour les en-têtes HTTP](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html) : CSP, anti-iframe, types MIME et confidentialité du référent.
- [TrustedHostMiddleware de Starlette](https://starlette.dev/middleware/#trustedhostmiddleware) : filtrage du nom d’hôte.
- [Paramètres Uvicorn](https://www.uvicorn.org/settings/) : concurrence, temporisations et confiance dans les proxies. Le délai keep-alive ne remplace pas un délai de réception du corps.
- [pip-audit](https://github.com/pypa/pip-audit) et [Trivy](https://trivy.dev/latest/docs/) : détection d’avis connus, distincte d’une preuve d’exploitation.
- [Suivi de sécurité Debian](https://security-tracker.debian.org/tracker/) et [Python 3.12.14](https://www.python.org/downloads/release/python-31214/) : suivre aussi le système et l’interpréteur, qui ne sont pas entièrement couverts par le scan des distributions Python.
