# Mutafriches QGIS - Instructions pour les agents

## Description du projet

Extension QGIS de Mutafriches : qualifier un site composé d'une ou plusieurs parcelles
cadastrales, puis consulter son potentiel de mutabilité pour sept usages et l'indice de
fiabilité associé, directement dans QGIS.

**Phase actuelle : maquette locale non publiée.** Le site analysé est une **sélection dans une
couche QGIS** (n'importe quelle couche de polygones) ; l'extension n'enregistre rien. Les
interactions QGIS (panneau, sélection, géométrie, saisie) sont réelles ; l'enrichissement et
l'évaluation sont **simulés** à partir de réponses figées. Aucun appel à l'API Mutafriches.

Projet Beta.gouv / incubateur ADEME. Application web et API :
`../mutafriches` (dépôt voisin, NestJS + React). Ses contrats (`packages/shared-types`) sont la
référence des valeurs, libellés et formes de réponse reproduits ici.

## Stack technique

- **QGIS 3.44** (seule version testée : 3.44.14, macOS arm64), PyQGIS, **Qt 5.15 / PyQt 5.15**
- **Python 3.12** embarqué par QGIS (aucune dépendance tierce)
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
│   ├── modele.py            # Site analysé (parcelles, réponses, résultats)
│   ├── service.py           # Interface du service (enrichir / évaluer), erreurs
│   └── service_simule.py    # Implémentation simulée (réponses figées, délai, erreur)
├── carto/                   # Interactions cartographiques
│   ├── exemple.py           # Couche de parcelles d'exemple (lien du tutoriel)
│   └── selection.py         # Couche active, identifiant cadastral, contiguïté, surbrillance
├── ui/                      # Panneau latéral (widgets Qt natifs)
│   ├── parcours.py          # État : sélection, 3 étapes, résultats
│   ├── contenus.py          # Wording, ordre des champs et infobulles des pages web
│   ├── pages.py             # Sélection et 3 étapes (calquées sur les pages web de qualification)
│   ├── resultats.py         # Résultats, podium, tableau, récapitulatif et détail d'un usage
│   └── dock.py              # Bandeau, en-tête, page courante
└── demo/
    ├── terrain/parcelles.geojson  # Parcelles d'exemple (IGN, Trélazé), outils/generer_terrain.py
    ├── scenarios/*.json     # Réponses détaillées de 3 friches de l'exemple, outils/figer-reponses.sh
    └── generique.json       # Grille du profil générique, idem (ne pas éditer)
outils/                      # Génération des données de démonstration (hors ZIP)
scripts/                     # Packaging, tests, parcours E2E dans QGIS
tests/                       # Tests unittest exécutés avec le Python de QGIS
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
- Bandeau permanent « Mode démonstration — données fictives » tant que le service est simulé.

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
  numéroté, cas limites, pièges (profil QGIS, démonstration à réinitialiser, extension à
  recharger).
- **Proposer un titre et un descriptif de PR** (Conventional Commits, moins de 70 caractères).

### Vérification post-implémentation

```bash
./scripts/tests.sh      # Tests unitaires avec le Python de QGIS
./scripts/package.sh    # Construit dist/mutafriches-<version>.zip
./scripts/e2e.sh        # Parcours complet dans une vraie session QGIS (profil isolé)
```

Ne jamais présenter une vérification syntaxique ou une capture simulée comme un test dans
QGIS. Préciser la version et l'OS réellement testés.

### Données de démonstration

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

### Commits

Conventional Commits : titre court à l'impératif en minuscules (moins de 70 caractères), une
seule ligne de description (le pourquoi). Aucune mention d'auteur ou de co-auteur.
Committer uniquement sur demande explicite. **Ne jamais `git push`** de sa propre initiative,
jamais en `--force`.

## Gotchas

### QtWebEngine absent de QGIS 3.44 macOS

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
- Canal analytique QGIS : un en-tête `Origin` n'identifie ni n'authentifie un intégrateur ;
  côté API, `?integrateur=` n'est lu qu'en iframe. Ne pas assimiler un traitement de masse à
  `PREFETCH` (réservé à la pré-chauffe automatique du cache).
- Entrées futures : clic avec résolution cadastrale, couche existante, saisie de références.
