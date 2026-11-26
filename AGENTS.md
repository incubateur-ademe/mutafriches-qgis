# Mutafriches QGIS - Instructions pour les agents

## Description du projet

Extension QGIS de Mutafriches : qualifier un site composé d'une ou plusieurs parcelles
cadastrales, puis consulter son potentiel de mutabilité pour sept usages et l'indice de
fiabilité associé, directement dans QGIS.

**Phase actuelle : analyse réelle sur l'API de production, seule API interrogée (ADR-0003, ADR-0006).**
L'utilisateur se présente, envoie un inventaire au **standard CNIG Friches**, et reçoit deux
couches attributaires (mutabilité, qualification), une carte symbolisée par usage et un tableau
de bord territorial dans le panneau. En mode réel, chaque site est enrichi puis évalué par l'API
(`POST /enrichissement`, `POST /evaluation/calculer`), site par site, avec le domaine de la
structure déclarée à l'accueil (ADR-0005). Ni démonstration, ni choix d'environnement, ni mode
développeur : une autre API ne se désigne que par variable d'environnement, pour les tests et
les captures de l'équipe. Suite prévue : `docs/plan-implementation-reelle.md`. Le parcours site à
site (ADR-0001) reste dans le code, hors panneau.

Projet Beta.gouv / incubateur ADEME. Application web et API :
`../mutafriches` (dépôt voisin, NestJS + React). Ses contrats (`packages/shared-types`) sont la
référence des valeurs, libellés et formes de réponse reproduits ici.

## Stack technique

- **QGIS 3.44** (seule version testée : 3.44.14, macOS arm64), PyQGIS, **Qt 5.15 / PyQt 5.15**
- **Python 3.12** embarqué par QGIS (aucune dépendance tierce)
- **Outillage de développement** : `uv`, Ruff, mypy (hors du Python de QGIS)
- **Interface Qt native** (widgets + QSS), inspirée du DSFR : pas de QtWebEngine (cf. Gotchas)
- **Outillage hors plugin** : Python 3 (générateur de terrain), TypeScript via le `tsx` de
  Mutafriches (gel des réponses simulées)

## Structure

```
mutafriches/                 # Le plugin (nom du dossier = identifiant du plugin)
├── __init__.py              # classFactory
├── metadata.txt
├── plugin.py                # Action de barre d'outils, dock, cycle de vie
├── core/                    # Sans dépendance à l'interface
│   ├── referentiel.py       # Champs, valeurs, libellés, badges (miroir de shared-types et apps/ui)
│   ├── recapitulatif.py     # Récapitulatif, détail d'usage, valeurs des étapes (miroir des builders web)
│   ├── cnig.py              # Lecture et contrôle d'un fichier CNIG Friches (51 colonnes)
│   ├── reglages.py          # Réglages déclarés dans l'arbre de QGIS, adresse d'API de test (variable d'environnement)
│   ├── client_api.py        # Appels réels : enrichissement puis calcul, site par site
│   ├── declaration.py       # Déclaration de la structure au registre des intégrateurs (ADR-0005)
│   ├── attributaire.py      # Ligne attributaire d'un site analysé, synthèse territoriale
│   ├── modele.py            # Site analysé (parcours site à site, hors panneau)
│   ├── service.py           # Interface du service (enrichir / évaluer), erreurs
│   └── service_simule.py    # Implémentation simulée du parcours site à site, hors panneau
├── carto/                   # Interactions cartographiques
│   ├── couches.py           # Couches mutabilité et qualification, symbologie, étiquettes, fond OSM
│   ├── exemple.py           # Couche de parcelles d'exemple (parcours site à site)
│   └── selection.py         # Identifiant cadastral, contiguïté, surbrillance (idem)
├── ui/                      # Panneau latéral (widgets Qt natifs)
│   ├── accueil.py           # Déclarant : structure, type, domaine, prénom, nom, e-mail (obligatoires), verrou
│   ├── options.py           # Page « Mutafriches » de Préférences › Options (coordonnées en lecture seule)
│   ├── parcours.py          # État : fichier CNIG, analyse par l'API, résultats
│   ├── prototype.py         # Pages Accueil, Import et Résultats (tableau de bord territorial)
│   ├── graphiques.py        # Anneaux, légendes et petits tableaux dessinés avec QPainter
│   ├── contenus.py          # Wording
│   ├── pages.py             # Socle des pages, chargement, champ de saisie terrain
│   ├── resultats.py         # Détail d'un site (hors panneau, à rebrancher)
│   └── dock.py              # Bandeau, en-tête, page courante
├── modeles/modele-cnig.csv  # Modèle de fichier vide proposé à l'utilisateur
└── demo/                    # Parcours site à site, hors panneau
    ├── terrain/parcelles.geojson  # Parcelles d'exemple (IGN, Trélazé), outils/generer_terrain.py
    ├── scenarios/*.json     # Réponses détaillées de 3 friches de l'exemple, outils/figer-reponses.sh
    └── generique.json       # Grille du profil générique, idem (ne pas éditer)
captures/                    # Captures QGIS et tableaux de bord produits par scripts/e2e.sh (local, ignoré)
outils/                      # Génération des données de démonstration (hors ZIP)
scripts/                     # Packaging, tests, parcours E2E dans QGIS
tests/                       # Tests unittest exécutés avec le Python de QGIS
tests/donnees/               # Jeux d'essai de Montereau (table figée, inventaires CNIG), hors du ZIP
```

## Règles de code STRICTES

### 1. Python typé

- TOUJOURS annoter paramètres et retours (`def enrichir(self, parcelles: list[str]) -> Tache:`).
- Données JSON : typer au plus près (`dict[str, object]`, `TypedDict` si la forme est stable).
- Pas de `from x import *`.

### 2. Imports Qt via `qgis.PyQt`, énumérations qualifiées

```python
# INTERDIT : lie le code à PyQt5 et casse le passage à QGIS 4 / Qt6
from PyQt5.QtWidgets import QPushButton

label.setAlignment(Qt.AlignLeft)

# OBLIGATOIRE
from qgis.PyQt.QtWidgets import QPushButton

label.setAlignment(Qt.AlignmentFlag.AlignLeft)
```

Les énumérations qualifiées fonctionnent déjà sous PyQt5 5.15 : les utiliser partout. Cela ne
vaut **pas** compatibilité Qt6 tant qu'elle n'a pas été testée.

### 3. Pas d'emojis/icônes dans le code ni dans l'interface

### 4. Accents français OBLIGATOIRES

Code, commentaires, libellés, messages d'erreur, infobulles : orthographe française complète
(données, récupérées, critère, fiabilité, accès, contrôle, être, à…).

### 5. Commentaires : simples et brefs

Une ligne, le **pourquoi** et jamais le quoi. Pas de docstrings longues sauf sémantique non
évidente. Référencer la source en une ligne (`# Miroir de TYPE_PROPRIETAIRE_LABELS (shared-types)`).

### 6. Interface : Qt natif inspiré du DSFR

- **Parcours et wording calqués sur l'application web** (`apps/ui/src/features/analyser`,
  `qualification`, `resultats`) : mêmes étapes, ordre des champs, libellés, infobulles, choix vide
  « Sélectionner une option » et champs obligatoires. Textes centralisés dans `ui/contenus.py`.
  Toute divergence avec le web doit être justifiée (ex. : messages de chargement sans émojis).
- Récapitulatif et détail d'usage : portage Python des builders `buildRecapitulatifSite` et
  `buildDetailUsage` (affichage pur) dans `core/recapitulatif.py`, à tenir aligné sur shared-types.

- Couleurs et styles centralisés dans `ui/style.py` (bleu France `#000091`, boutons
  rectangulaires, états de chargement et d'erreur explicites). Pas de couleur en dur ailleurs.
- **Ne jamais annoncer de conformité DSFR** : l'extension s'en inspire, elle n'a pas été validée.
- Composants accessibles : libellés associés aux champs (`setBuddy`), `setAccessibleName`
  sur les boutons sans texte explicite, navigation clavier fonctionnelle.
- Le panneau doit rester utilisable étroit (≈ 320 px) : défilement vertical, pas d'horizontal.
- Bandeau réservé à l'API de test désignée par `MUTAFRICHES_API_URL` (tests et captures de
  l'équipe). Jamais de bandeau en production.

### 7. Séparation réel / simulé

- L'interface ne connaît que l'interface `ServiceMutafriches` (`core/service.py`) : le service
  simulé doit pouvoir être remplacé par un client HTTP sans toucher à `ui/`.
- **Ne JAMAIS recopier l'algorithme de mutabilité ni le calcul de fiabilité** dans le plugin.
  Les réponses simulées sont **figées** par `outils/figer-reponses.sh`, qui exécute le calcul du
  dépôt Mutafriches sur les scénarios fictifs. Pas de score aléatoire, pas de faux calcul.
- Une réponse simulée qui ne correspond pas exactement à la saisie doit être signalée comme
  telle dans l'interface.
- Un indice de mutabilité n'est **pas** une probabilité de réussite : ne jamais le formuler ainsi.

## Workflow obligatoire

### Découpage et livraison d'une feature

- **Branche dédiée** avant tout commit (`feat/<slug>`, `fix/<slug>`, `chore/<slug>`). JAMAIS
  de commit sur `main`.
- **Commits atomiques** : séparer au minimum code, données de démonstration régénérées,
  documentation et bump de version. Annoncer le découpage avant de committer.
- **Réutiliser** les composants existants (`ui/widgets.py`, `core/referentiel.py`).
- **ADR** dans `docs/adr/` pour tout choix architectural significatif (interface, stockage,
  canal réseau, compatibilité de version).
- **README** : le mettre à jour si l'installation, le packaging ou le parcours change.
- **Proposer systématiquement des tests manuels dans QGIS** en fin de feature : parcours
  numéroté, cas limites, pièges (profil QGIS, coordonnées déjà déclarées dans le profil,
  extension à recharger).
- **Proposer un titre et un descriptif de PR** (Conventional Commits, moins de 70 caractères).

### Vérification post-implémentation

```bash
./scripts/valider.sh    # Tout d'un coup : format, lint, types, tests, ZIP et son contrôle
./scripts/e2e.sh        # Parcours complet dans une vraie session QGIS (profil isolé)
```

`valider.sh` enchaîne `ruff format`, `ruff check --fix`, `mypy`, `scripts/tests.sh`,
`scripts/package.sh` et `scripts/verifier-paquet.py` ; avec `--check`, il ne modifie rien
(c'est ce que joue la CI). **Le lancer avant chaque commit** : un commit doit le laisser vert.

- **Outillage** : Ruff (format et lint) et mypy, configurés dans `pyproject.toml`, installés
  par `uv sync` dans `.venv/`. Ne jamais les installer dans le Python de QGIS.
- **Règles tenues par les outils** : annotations obligatoires (`ANN`, `disallow_untyped_defs`),
  `PyQt5` interdit au profit de `qgis.PyQt` (`TID251`), imports triés, syntaxe Python 3.12.
- **`# type: ignore`** : toujours avec son code d'erreur, jamais pour contourner un `Json` ;
  mypy signale ceux devenus inutiles.
- **Miroirs de shared-types** : toute constante recopiée de Mutafriches (colonnes CNIG,
  critères manuels, libellés d'usage, niveaux de fiabilité) est comparée à sa source par
  `tests/test_miroirs.py`, ignoré si le dépôt voisin est absent. Ajouter un cas à ce test
  pour toute nouvelle constante recopiée.
- **CI** (`.github/workflows/ci.yml`) : job qualité, et tests unitaires dans l'image Docker
  `qgis/qgis:3.44`. L'E2E avec captures reste manuel (macOS, session graphique).
- Autres scripts : `./scripts/reinitialiser.sh` (accueil mémorisé, QGIS fermé),
  `./scripts/captures-tutoriel.sh` (captures du tutoriel web, contre le staging).

Ne jamais présenter une vérification syntaxique ou une capture simulée comme un test dans
QGIS. Préciser la version et l'OS réellement testés.

### Données de démonstration

- Jeux d'essai : `python3 outils/figer_attributaire.py` gèle la table attributaire publique de
  Montereau dans `tests/donnees/`, hors du ZIP ; ne jamais éditer les fichiers produits. Le modèle
  CNIG proposé à l'utilisateur (`mutafriches/modeles/`) est vide (les 51 colonnes, aucune ligne) :
  il ne peut pas être envoyé tel quel ; les fichiers de Montereau servent aux tests, au serveur
  factice et aux captures seulement. Les sites SCET nommés
  sont des données partenaires publiques via l'API ; la saisie est déclarative.
- Terrain : modifier `outils/generer_terrain.py`, jamais les GeoJSON à la main.
- Réponses simulées : `./outils/figer-reponses.sh` (nécessite `../mutafriches` avec
  `node_modules` et `packages/shared-types/dist` à jour). Régénérer après toute évolution de
  l'algorithme dans Mutafriches ; la version d'algorithme figée est inscrite dans chaque JSON.
- Parcelles d'exemple **réelles** (Trélazé, PCI Express de l'IGN) mais enrichissement et
  résultats **fictifs** : ne jamais présenter un indice ou une donnée d'enrichissement comme réel.
- Les étiquettes du podium sont calculées au gel par `getPodiumTags` (code de l'interface web),
  jamais dans le plugin : ses seuils d'affichage n'y sont pas recopiés.
- Trois friches de l'exemple ont des réponses figées détaillées (dont une erreur récupérable) ;
  aucune interface ne les met en avant.
- Toute autre sélection, dans n'importe quelle couche : profil générique (surface mesurée sur la
  géométrie, part bâtie fictive de 20 %, contexte fictif, indices du point le plus proche d'une
  grille figée). Le plugin choisit un point de grille, il ne connaît pas les seuils de
  l'algorithme : ne pas les y recopier.

### Version de l'extension

- SemVer dans `mutafriches/metadata.txt` (`version=`), bump dans un commit dédié
  `chore(release): vX.Y.Z`. Indépendant de la version de l'algorithme Mutafriches.
- Une release se publie en poussant le tag `vX.Y.Z` : `.github/workflows/release.yml` y joint le
  ZIP, sa copie au nom stable `extension-qgis-mutafriches.zip` (cible du bouton de téléchargement
  du site, à ne jamais renommer seule) et les deux fichiers de test produits par
  `scripts/package.sh` (`dist/friches-cnig-test-montereau*.csv`) : le README donne à l'équipe
  leurs liens stables (`releases/latest/download/...`). Le tutoriel web pointe sur le fichier de 5 sites (décision de
  l'équipe) ; le panneau ne les propose pas.

### Commits

Conventional Commits : titre court à l'impératif en minuscules (moins de 70 caractères), une
seule ligne de description (le pourquoi). Aucune mention d'auteur ou de co-auteur.
Committer uniquement sur demande explicite. **Ne jamais `git push`** de sa propre initiative,
jamais en `--force`.

## Gotchas

### QtWebEngine absent de QGIS 3.44 macOS

- QtWebKit n'exécute pas non plus dsfr-chart (`SyntaxError` sur la syntaxe moderne) et QtCharts
  n'est pas embarqué : les graphiques du panneau sont dessinés avec QPainter (`ui/graphiques.py`).
- Un changement de page du panneau doit remettre le défilement en haut **après** la mise en
  page (`QTimer.singleShot(0, …)`) : le focus d'un bouton fait sinon défiler au milieu.

- Le build officiel QGIS 3.44 macOS (Qt 5.15.19) n'embarque **pas** `PyQt5.QtWebEngineWidgets` :
  le module `qgis.PyQt.QtWebEngineWidgets` existe mais échoue à l'import. Seul QtWebKit 5.212
  est présent, moteur obsolète et retiré de Qt6 / QGIS 4.
- D'où le choix d'une interface Qt native. Ne pas installer de paquet dans le Python de QGIS
  pour forcer WebEngine.

### Lancer le Python de QGIS hors de l'application (macOS)

- `python3.12` de l'app ne trouve pas sa bibliothèque standard seul :
  `PYTHONHOME=/Applications/QGIS.app/Contents/Resources/python3.11` (dossier nommé 3.11 mais
  Python 3.12), plus `QT_QPA_PLATFORM=offscreen` sans interface. `scripts/tests.sh` le fait.

### Sélection dans n'importe quelle couche

- La couche suivie est la couche active du panneau Couches, si c'est une couche de polygones.
- Identifiant cadastral cherché dans `idu`, `id`… (format à 14 caractères, Corse comprise) ;
  à défaut, l'identifiant de l'entité sert de référence.
- Surfaces et contiguïté calculées en Lambert 93 : une couche en WGS84 donnerait sinon des
  degrés carrés et une tolérance de contiguïté de plusieurs kilomètres.
- Dans un test, ajouter une couche à un projet vide lui impose son SCR : fixer le SCR voulu
  après une première couche.

### API réelle

- L'API exige un `Origin` déclaré au registre des intégrateurs (table `integrateurs`, ADR-0055 de
  Mutafriches) : 403 sinon. L'extension déclare le domaine de la structure (canal `qgis`) puis
  l'envoie avec `X-Mutafriches-Client: qgis/<version>` (`core/declaration.py`, ADR-0005).
- Déclaration limitée à **5 appels par heure et par IP** : ne jamais redéclarer une saisie
  inchangée (empreinte mémorisée par adresse d'API), ni en boucle dans un test contre le staging.
  Un domaine déclaré sur le staging ne vaut pas en production.
- Une API sans registre (404 sur la déclaration) reçoit l'origine historique
  `https://qgis.mutafriches.beta.gouv.fr`, toujours acceptée.
- Prénom, nom et e-mail partent chez Brevo, jamais en base : ne pas les journaliser ni les
  transmettre ailleurs.
- La case « J'accepte d'être contacté·e… » (`accepteContact`, attribut Brevo `ACCEPTE_CONTACT`)
  est **obligatoire** pour utiliser l'extension (ADR-0006), jamais pré-cochée : sans elle,
  l'accueil est refusé (`Utilisateur.erreurs`), alors que l'API n'exige que les coordonnées
  (`erreurs_coordonnees`). Les options l'affichent sans permettre de la retirer. Une structure
  déclarée sans accord par une version antérieure repasse par l'accueil, coordonnées verrouillées.
  La clé n'est envoyée que si elle vaut `true` ; l'API ne retire jamais un accord. Les 9 critères manuels sont tous obligatoires (« ne-sait-pas », jamais vide).
- 100 requêtes par minute et par IP, deux requêtes par site : ne pas paralléliser.
- L'API répond **500 « Erreur lors de l'enrichissement »** quand aucune parcelle du site
  n'existe au cadastre : c'est un échec du site, à expliquer en clair, jamais « Erreur 500 ».
- Les anciens fichiers exemple (sites fictifs, commune 99999) restent refusés au contrôle local :
  ne jamais les envoyer à l'API. Le modèle actuel est vide.
- **Réglages** : tous déclarés dans `core/reglages.py` (ADR-0004), jamais de clé `QgsSettings`
  en dur ailleurs ; tout nouveau réglage y entre avec sa description, puis dans `ui/options.py`
  s'il doit être modifiable. Ne jamais exposer un seuil ou un paramètre de calcul.
- **Production seule** (ADR-0006) : aucun réglage, aucune option, aucun mode ne change d'API. Ne
  jamais en réintroduire. Les tests et les captures désignent une autre API par
  `MUTAFRICHES_API_URL` au lancement de QGIS (`MUTAFRICHES_INTERVALLE_MS` pour le délai, lue
  seulement face à une API de test) ; le panneau affiche alors le bandeau « Environnement de test ».
- **Coordonnées verrouillées** une fois la structure déclarée (`coordonnees_verrouillees`,
  `ui/accueil.py`) : plus de lien « Modifier », options en lecture seule, pas de bouton
  d'effacement. Seul un refus d'accès de l'API (403, qui oublie la déclaration) rouvre la saisie. Désinstaller l'extension n'efface pas les réglages du
  profil : ne jamais le promettre à l'utilisateur.
- QGIS interrompt lui-même une requête de plus de 60 s (« Operation canceled ») : c'est un
  échec du site, retenté une fois, jamais une erreur bloquante pour l'inventaire.
- `scripts/captures-tutoriel.sh` écrit les captures du tutoriel web dans le dépôt voisin
  Mutafriches, contre le staging réel, jamais la production ; ne pas les retoucher à la main.
- `tests/serveur_factice.py` sert aux tests unitaires et à l'E2E ; ne jamais présenter un
  passage contre lui comme un test contre la production.
- Les réglages s'écrivent dans le profil courant : un test qui en change un doit le remettre en
  état (`entree.remove()`). Une adresse d'API locale se pose dans `os.environ`, jamais dans un
  réglage, et se retire en fin de test.

### Fond de carte et cadrage

- À l'ouverture du panneau sur un projet vide, le plugin ajoute le fond OSM et cadre la France.
  La carte ne prend la projection du projet qu'au tour d'événements suivant : tout cadrage qui
  suit un changement de SCR doit être différé (`QTimer.singleShot`), sinon il vise le monde.
- `QFileDialog.getSaveFileName` avec un simple nom de fichier s'ouvre à la racine du disque,
  en lecture seule sur macOS : toujours donner un dossier (`QStandardPaths`), et rattraper
  `OSError` à l'écriture.
- Les scripts de captures ne doivent rien préparer que le plugin ne fasse lui-même : une
  capture qui montre un état inatteignable ment au lecteur du tutoriel.

### Couches mémoire et fermeture de QGIS

- Les couches mémoire déclenchent une question à la fermeture : un script E2E doit
  `removeAllMapLayers()` avant `actionExit()`.
- Les widgets ajoutés par un rafraîchissement ne sont visibles qu'après `processEvents()` :
  un clic E2E juste après un changement d'état échoue sinon.

### Un site multiparcellaire est UN site

- Plusieurs parcelles sélectionnées forment une seule entité, pas un traitement par lot. Après
  « Analyser », le périmètre est figé : la sélection QGIS peut changer sans l'affecter.
- Les résultats sont recalculés à chaque passage par l'étape 3 : l'interface n'expose pas
  d'état « à recalculer ».

### Couche XYZ : encoder l'URI avec `QgsDataSourceUri`

- Une URI `type=xyz&url=...` encodée à la main (`urllib.parse.quote`) donne une couche
  « valide » mais des tuiles vides, sans erreur. Construire l'URI avec
  `QgsDataSourceUri.setParam()` puis `encodedUri()`.

### Clic sur la carte : parcelle sous le curseur, pas la plus proche

- `QgsMapToolIdentifyFeature` cherche dans un rayon de tolérance : sur des parcelles de
  quelques dizaines de m², il attrape une voisine. `OutilParcelles` teste l'inclusion du point.
- Les géométries sont en Lambert 93 ; le projet peut être dans un autre SCR (fond OSM en 3857) :
  toujours transformer emprises et points (`QgsCoordinateTransform`) avant cadrage ou clic.

### Critère neutre en mode détaillé

- Un critère au score NEUTRE (0,5) figure à la fois dans `detailsAvantages` et
  `detailsContraintes` (comportement voulu de l'algorithme). L'interface le présente une seule
  fois, comme neutre.

### Distances en km dans le détail

- Dans `detailsCalcul`, `distanceAutoroute` et `distanceRaccordementElectrique` sont en **km**
  (converties par l'algorithme) alors que l'enrichissement les donne en **mètres**.

## Points futurs (hors maquette)

- Réseau : passer par `QgsNetworkAccessManager` / `QgsBlockingNetworkRequest` (proxy et
  authentification QGIS), gérer débit, annulation, erreurs partielles.
- Canal analytique QGIS : le domaine déclaré identifie une structure, il n'authentifie
  personne (déclaration libre). Ne pas assimiler un traitement de masse à
  `PREFETCH` (réservé à la pré-chauffe automatique du cache).
- Entrées futures : clic avec résolution cadastrale, couche existante, saisie de références.
