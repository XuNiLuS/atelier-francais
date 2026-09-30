# Consulter les statistiques du site

Les statistiques servent à repérer les pages et les quiz utilisés pour préparer les prochains contenus. Elles concernent seulement les visiteurs qui acceptent la mesure et dont le navigateur laisse passer Google Analytics. Les exercices restent utilisables après un refus.

## Ouvrir Google Analytics

Utiliser [Google Analytics — L’atelier de Madame Daadoun](https://analytics.google.com/analytics/web/#/a410298672p556853738/) avec le compte Google autorisé.

| Élément | Identifiant |
| --- | --- |
| Compte Analytics | `410298672` |
| Propriété GA4 | `556853738` |
| Flux Web | `15892076312` |
| Identifiant de mesure | `G-S61F6F97C5` |
| Origine autorisée | `https://xunilus.github.io` |
| Chemin du site | `/atelier-francais` |

La création du compte, de la propriété et du flux a été vérifiée dans l’interface GA4 le 30 septembre 2026. Les **mesures améliorées du flux sont désactivées** et les trois dimensions personnalisées décrites ci-dessous sont enregistrées. Après publication, GA4 a bien affiché une occurrence de chacun des événements `page_view`, `quiz_start` et `quiz_complete` issus du parcours de test de 4e.

L’identifiant de mesure est public et figure dans `data/analytics.json`, puis dans les pages générées. Il ne donne pas accès aux rapports. Aucun mot de passe ni jeton d’administration Google n’est nécessaire dans le dépôt.

## Ce qui est compté

| Événement envoyé par le site | Déclenchement | Informations ajoutées par le site |
| --- | --- | --- |
| `page_view` | Une fois par page chargée, lorsque l’accord est valide ou vient d’être donné. | Adresse sans paramètres ni fragment, référent vide, niveau lorsqu’il existe ; identifiant et thème sur les pages de quiz. |
| `quiz_start` | Première réponse vérifiée dans un essai, correcte ou incorrecte. | Niveau, identifiant et thème du quiz. |
| `quiz_complete` | Les 20 réponses de l’essai ont été vérifiées. | Niveau, identifiant et thème du quiz. |

Chaque événement de quiz est envoyé au maximum une fois par essai. Cliquer sur Recommencer ouvre un nouvel essai ; visiter une page de quiz sans vérifier de réponse ne déclenche pas `quiz_start`. Les événements survenus sans accord ne sont pas rattrapés si le visiteur accepte plus tard.

Ces nombres représentent des **essais**, pas un nombre d’élèves. Un même élève peut recommencer, plusieurs élèves peuvent partager un navigateur, et les refus ou bloqueurs ne sont pas comptés. Le rapport entre les fins et les débuts ne mesure pas la réussite scolaire ; il peut aussi être affecté par les changements de consentement et la période choisie. Aucune réponse ni note n’est envoyée.

Le titre de page transmis est construit depuis le catalogue : « Thème · niveau · L’atelier de Madame Daadoun » sur un quiz, « Quiz de niveau · L’atelier de Madame Daadoun » sur une page de niveau, et le nom du site sur les autres pages. Il ne vient pas du titre lu dans le navigateur. Les **chemins de page** permettent de distinguer toutes les pages, y compris celles qui partagent ce dernier titre. Le niveau et le thème décrivent le contenu ouvert, sans déduire le niveau personnel de son visiteur.

GA4 peut également collecter automatiquement des événements tels que `first_visit`, `session_start` et `user_engagement` après accord. Désactiver les mesures améliorées ne supprime pas ces événements de base. Le service reçoit des informations techniques liées au navigateur et à la connexion et utilise des identifiants en cookies ; il ne s’agit pas d’une collecte totalement anonyme. Voir les [événements automatiques GA4](https://support.google.com/analytics/answer/9234069?hl=fr) et la [collecte de données](https://support.google.com/analytics/answer/11593727?hl=fr).

## Lire les résultats

Dans **Rapports**, commencer par la vue **Temps réel** pour contrôler une visite de test consentie. Les autres rapports ne sont pas instantanés : leur [traitement peut prendre 24 à 48 heures](https://support.google.com/analytics/answer/11198161?hl=fr). L’absence de résultat immédiat ne prouve donc ni une panne ni un bon fonctionnement.

Choisir **Aperçu en temps réel** pour voir l’ensemble des visites. **Instantané d’utilisateur** montre l’activité d’un visiteur sélectionné au hasard : il ne représente pas forcément votre propre navigation. Si cette vue est ouverte, cliquer sur **Quitter l’instantané** pour revenir au rapport global.

Pour les visites, utiliser le rapport **Pages et écrans**, avec une dimension de chemin de page, et comparer les vues :

- `/atelier-francais/` correspond à l’accueil ;
- `/atelier-francais/niveaux/4e/`, `/3e/` ou `/seconde/` correspondent aux pages de niveau ;
- `/atelier-francais/quiz/{quiz_id}/` correspond à un quiz.

Pour les essais commencés et terminés, utiliser le rapport **Événements** et les noms `quiz_start` et `quiz_complete`. Pour croiser les résultats par niveau ou thème, utiliser **Explorer** avec le nombre d’événements, filtrer ces deux noms et ajouter les dimensions ci-dessous. Pour comparer les vues par niveau ou quiz, effectuer la même analyse en filtrant `page_view`. Les intitulés et l’emplacement exact des rapports peuvent varier selon l’organisation de la propriété.

### Dimensions des quiz

Dans **Administration → Affichage des données → Définitions personnalisées**, les trois dimensions suivantes ont été enregistrées avec une portée **Événement** ; leurs noms ont été vérifiés dans l’interface :

| Libellé de la dimension | Paramètre exact | Exemples |
| --- | --- | --- |
| Niveau scolaire | `education_level` | `4e`, `3e`, `seconde` |
| Identifiant du quiz | `quiz_id` | `4e-temps-recit` |
| Thème du quiz | `quiz_theme` | `Les temps du récit` |

Le code transmet les trois paramètres sur `quiz_start`, `quiz_complete` et les vues de page de quiz. Les vues de page de niveau portent seulement `education_level` ; l’accueil et les autres pages générales ne portent aucune de ces dimensions. Une valeur absente sur ces dernières pages est donc normale. La déclaration des dimensions permet de les sélectionner dans les rapports et explorations après le traitement des nouvelles données. Voir les [dimensions personnalisées GA4](https://support.google.com/analytics/answer/14240153?hl=fr).

## Accord, stockage et retrait

Sans choix ou après un refus, le site ne charge pas `gtag.js`, n’envoie pas de requête à Google Analytics et ne met aucun événement en attente. La mesure exige un accord encore valide, un identifiant de mesure valide, l’origine HTTPS exacte et un chemin appartenant au projet. Elle reste désactivée en local, sur une copie du site, sur un autre hôte ou dans un projet voisin, même après un clic sur Accepter.

L’accord ou le refus est enregistré dans `localStorage` sous `atelier.analytics-consent.v1:/atelier-francais`, avec sa date. Il reste valable au maximum **180 jours**, sans prolongation lors d’une simple visite. Si le stockage est bloqué, le choix ne vaut que pour la page ouverte.

Après accord, le code configure les cookies de mesure avec les réglages suivants :

| Réglage | Valeur |
| --- | --- |
| Préfixe | `atelier` : notamment `atelier_ga` et `atelier_ga_S61F6F97C5`. |
| Hôte | `xunilus.github.io` seulement, sans attribut `Domain` (`cookie_domain: 'none'`). |
| Chemin | `/atelier-francais/`. |
| Durée configurée | 180 jours, soit 15 552 000 secondes ; le navigateur peut les supprimer plus tôt. |
| Renouvellement | `cookie_update: false`, sans report de l’expiration à chaque visite. |
| Attributs | `SameSite=Lax;Secure`. |

Le bouton **Mes choix de statistiques**, en bas de chaque page, permet de changer d’avis. En cas de retrait, le code désactive la balise, supprime les cookies Analytics propres à ce projet et recharge la page si la balise avait démarré. Cela efface aussi l’essai en cours, comme tout rechargement. L’expiration du choix et son retrait dans un autre onglet interrompent également la mesure. Le retrait n’efface pas les données déjà reçues par Google. La durée de 180 jours concerne le navigateur. Dans GA4, la conservation des données d’événements et des données utilisateur est réglée sur **2 mois**, avec la réinitialisation de la durée sur nouvelle activité **désactivée**. Ces réglages ont été enregistrés dans l’interface le 30 septembre 2026. Ils ne s’appliquent pas aux rapports agrégés standards, dont la conservation n’est pas limitée à deux mois par ce paramètre.

Google Signals et la personnalisation publicitaire sont désactivés par le code ; les réglages de consentement publicitaire restent refusés. Les [paramètres de configuration GA4](https://developers.google.com/analytics/devguides/collection/ga4/reference/config) décrivent les champs employés. La page publique [Confidentialité](https://xunilus.github.io/atelier-francais/confidentialite/) explique le fonctionnement aux visiteurs. Ces choix techniques ne valent pas certification juridique ou CNIL.

## Vérifier avant et après publication

Le 30 septembre 2026, **19 tests Python et 23 tests JavaScript ont réussi**, y compris les contrôles ajoutés pour le chargement et les changements de page. Le [déploiement initial GitHub Pages](https://github.com/XuNiLuS/atelier-francais/actions/runs/36763018436) a réussi. Sur le site public, un parcours de 20 réponses du quiz « Les temps du récit » a produit une page vue, un début et une fin de quiz, tous visibles dans **Aperçu en temps réel**. La valeur `education_level = 4e` a été consultée dans le détail de l’événement reçu. Ces premières occurrences sont des tests, pas des visites d’élèves.

Le navigateur a également confirmé l’absence de script Google avant accord, après refus et après retrait (avec rechargement). Aucune erreur JavaScript ou CSP n’a été observée sur ce parcours. Le positionnement des boutons a été vérifié en largeur mobile de 375 pixels. La configuration des cookies est couverte par les tests simulés ; les attributs des cookies réels n’ont pas été inspectés dans les outils de stockage du navigateur. Les rapports différés et les autres navigateurs n’ont pas encore été vérifiés.

Les vérifications automatisées s’exécutent depuis le dossier du projet :

```sh
python -m unittest discover -s tests -v
node --test tests/analytics.test.cjs
python scripts/export_static.py --base-path /atelier-francais
```

Les tests JavaScript utilisent Node.js 22, sans installation npm ni appel réseau. Le workflow GitHub Pages les exécute avant la publication. Ils couvrent l’absence de mesure sans accord ou hors production, l’accord, le refus, l’expiration, le retrait, le stockage bloqué, les URL nettoyées et le contenu limité des événements. Ils simulent le navigateur ; ils ne prouvent pas l’exécution de la balise Google ni la réception côté GA4.

Sur le site publié, contrôler séparément le comportement réel dans les outils réseau du navigateur :

1. Dans un contexte de navigation sans choix enregistré, ouvrir une page : aucune requête vers Google Analytics ou Google Tag Manager ne doit partir. Refuser et naviguer doit conserver ce résultat.
2. Accepter depuis **Mes choix de statistiques** : vérifier le chargement de la balise, la vue de page, son contexte de niveau ou de quiz et les cookies au bon hôte et au bon chemin.
3. Vérifier une première réponse, puis les 20 réponses : contrôler `quiz_start` et `quiz_complete`, leurs trois paramètres de catalogue et l’absence de réponses ou de notes.
4. Retirer l’accord : vérifier le rechargement, l’arrêt des requêtes suivantes et la suppression des cookies du projet. Vérifier aussi que le quiz fonctionne toujours.
5. Refaire un accord en prévisualisation locale : aucun chargement de balise ni événement ne doit partir.
6. Contrôler ensuite les événements dans **Temps réel** et, après traitement, dans les rapports. Une requête réseau ou un test local réussi ne remplace pas cette observation dans GA4.

Si rien n’apparaît, vérifier l’adresse de production, l’accord, l’identifiant de mesure, les bloqueurs, les erreurs CSP et la bonne propriété Analytics. Ne pas réactiver les mesures améliorées pour tenter de corriger un problème de réception : elles ajouteraient d’autres événements que ceux prévus ici.

Le panneau **Mes choix de statistiques** distingue désormais l’accord enregistré, le chargement en cours, la balise chargée et une erreur de chargement. Au-delà de 20 secondes sans résultat, il signale une attente longue, sans conclure à une panne. En cas d’erreur ou d’attente longue, **Réessayer** recharge la page et réinitialise l’essai en cours ; le choix de consentement mémorisé reste inchangé. « Balise chargée » confirme le chargement du script, pas la réception des données par Google : cette dernière se vérifie dans **Aperçu en temps réel**.

Pour désactiver la mesure pour tous les visiteurs, remplacer `measurement_id` par une chaîne vide dans `data/analytics.json`, puis reconstruire et publier. Un changement d’hôte ou de chemin demande aussi de revoir le garde-fou dans le code, les tests, les cookies et la documentation ; modifier seulement l’identifiant GA4 ne suffit pas.
