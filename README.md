# mutafriches-qgis

Extension QGIS de [Mutafriches](https://mutafriches.beta.gouv.fr) — **maquette locale non
publiée**.

Prototype V0 (ADR-0002) : l'utilisateur se présente, envoie son inventaire de sites au
**standard CNIG Friches**, et reçoit une table attributaire de mutabilité, une table de
qualification, une carte symbolisée par usage et un tableau de bord territorial dans le
panneau. Objectif : captures d'écran.

> **Deux modes.** En mode réel (défaut, ADR-0003), chaque site est enrichi puis évalué par l'API
> Mutafriches existante ; l'origine de l'extension doit y être autorisée. En mode démonstration,
> les résultats sont ceux de la table attributaire de Montereau-Fault-Yonne gelée dans le plugin.

Seule version testée : **QGIS 3.44.14 sous macOS (Apple Silicon)**.

## Installation

1. Construire le ZIP : `./scripts/package.sh` → `dist/mutafriches-<version>.zip`
2. Dans QGIS : **Extensions › Installer/Gérer les extensions › Installer depuis un ZIP**,
   choisir le fichier, puis **Installer l'extension**. Accepter l'avertissement sur les
   extensions non vérifiées (extension locale).
3. Un bouton **Mutafriches** apparaît dans une barre d'outils dédiée.

Pour mettre à jour : reconstruire le ZIP et le réinstaller par le même écran (la version
précédente est remplacée).

## Tester en 3 minutes

1. Ouvrir le panneau **Mutafriches** : il demande structure et mail (une fois). Sur un projet
   vide, un fond OpenStreetMap cadré sur la France est ajouté ; un projet qui a déjà des couches
   n'est pas modifié.
2. Choisir un fichier CNIG Friches (CSV ou GeoJSON). Chaque ligne est contrôlée et affichée
   OK ou KO avec ses erreurs ; les lignes KO sont écartées de l'envoi. **Télécharger un fichier
   exemple** enregistre un modèle à remplir, aux valeurs volontairement fictives (commune 99999) :
   envoyé tel quel, il est refusé au contrôle, chaque site d'exemple devant être remplacé.
   Pour une démonstration, utiliser `mutafriches/demo/montereau/friches-cnig-montereau.csv`
   (28 sites) ou `friches-cnig-erreurs.csv` (4 sites corrects, 6 lignes en erreur).
3. **Envoyer mes N sites** : après l'attente, deux couches apparaissent (Mutabilité, étiquetée
   par usage et indice ; Qualification, masquée), avec un fond OpenStreetMap si le projet était
   vide.
4. Panneau résultats, tableau de bord territorial : alerte « sites nécessitant votre attention »
   (lignes écartées, sites non retrouvés, sites peu fiables), chiffres clés, anneau des usages,
   barres par usage avec indice moyen, anneau de fiabilité, profils de sites, niveaux de
   compatibilité, sites à forte compatibilité (cliquer un site le sélectionne et cadre la carte).
   Boutons **Table mutabilité**, **Table qualification**, lien **Analyser un autre inventaire**.
   Les tables s'ouvrent aussi depuis le panneau Couches : clic droit sur la couche, « Ouvrir la
   table d'attributs », ou F6 sur la couche sélectionnée.

Un fichier CNIG d'une autre commune est accepté mais ses sites ne sont pas retrouvés dans la
table figée : le panneau le signale et affiche les résultats de Montereau.

### Réglages

Tous les réglages sont dans **Préférences › Options › Mutafriches**, page aussi ouverte par le
lien « Réglages » du panneau et par le menu Extensions › Mutafriches (ADR-0004) :

| Bloc | Réglages |
|---|---|
| Service | Environnement : production (défaut) ou démonstration |
| Vos informations | Structure, mail, consentement ; « Effacer mes informations » fait revenir l'accueil |
| Carte | Ajouter ou non le fond OpenStreetMap à l'ouverture d'un projet vide |
| Développement | Mode développeur : staging, adresse d'API libre, origine envoyée, délai entre sites |

| Environnement | API | Bandeau |
|---|---|---|
| Production | `https://mutafriches.beta.gouv.fr` | aucun |
| Staging (mode développeur) | `https://mutafriches.incubateur.ademe.dev` | « Environnement de test (staging) » |
| Démonstration | aucune, table figée de Montereau | « Mode démonstration » |

Changer de service vide les résultats et retire les deux couches Mutafriches du projet. Sans
mode développeur, le staging et l'adresse libre sont ignorés même s'ils sont enregistrés.
`MUTAFRICHES_DEV=1` au lancement de QGIS active aussi le mode développeur. Les réglages sont
enregistrés sous `plugins/mutafriches/` et visibles dans Options › Avancé.

L'extension pose l'en-tête `Origin: https://qgis.mutafriches.beta.gouv.fr`, autorisé sur les
deux API. Un site prend deux à cinq secondes ; un site dont la réponse dépasse le délai réseau
de QGIS (60 s par défaut) est retenté une fois, puis listé en échec sans interrompre les
suivants. Structure et mail restent dans le profil QGIS, rien n'est transmis.

Pour jouer le mode réel sans appeler Mutafriches : `python3 tests/serveur_factice.py 8799`, puis,
en mode développeur, adresse d'API libre `http://127.0.0.1:8799`.

### Revoir l'accueil

L'accueil (structure, mail, consentement) n'est demandé qu'une fois. Pour le revoir : le lien
**Modifier** en bas de la page d'envoi, ou **Effacer mes informations** dans les réglages.
QGIS fermé, `./scripts/reinitialiser.sh` fait la même chose.

## Captures

`./scripts/e2e.sh` écrit les captures de la fenêtre QGIS dans `captures/` (local, ignoré par git).

### Captures du tutoriel web

`./scripts/captures-tutoriel.sh` joue le parcours nominal dans QGIS contre l'API de staging et
écrit 13 captures WebP (1600 px) dans `../mutafriches/apps/ui/public/images/tutoriel-qgis/`,
lues par la page `/integrer-mutafriches/extension-qgis` de Mutafriches. Chaque passage analyse
réellement 32 sites sur le staging. `MF_TUTORIEL_API` change l'API visée, `MF_TUTORIEL_ETAPES=2`
ne reprend que la capture d'installation.

### Captures en mode clair (macOS)

QGIS suit l'apparence du système. Pour des captures claires sans changer tout le Mac, forcer
l'apparence claire pour QGIS seulement (à faire QGIS fermé, puis à retirer) :

```bash
defaults write org.qgis.qgis3 NSRequiresAquaSystemAppearance -bool true
```

```bash
defaults delete org.qgis.qgis3 NSRequiresAquaSystemAppearance
```

`scripts/e2e.sh` applique ce réglage le temps du parcours et le retire ensuite, sauf s'il
était déjà posé. Si QGIS reste sombre, vérifier le thème d'interface (Préférences, Général,
« Thème de l'interface » : `default`, pas « Night Mapping »), qui l'emporte sur l'apparence
du système. Pour que les tables attributaires
s'ouvrent ancrées en bas : Préférences, Sources de données, « Ouvrir la table attributaire
dans une fenêtre ancrée ».

## Développement

Prérequis : QGIS 3.44 et [uv](https://docs.astral.sh/uv/) (`brew install uv`), puis `uv sync`.

```bash
./scripts/valider.sh   # Format, lint, types, tests unitaires, ZIP et contrôle du ZIP
./scripts/e2e.sh       # Parcours complet dans une vraie session QGIS, sur un profil isolé
```

Ruff et mypy vivent dans `.venv/`, jamais dans le Python de QGIS. La CI joue
`./scripts/valider.sh --check` en deux jobs : qualité, et tests unitaires dans l'image Docker
officielle de QGIS. Les constantes recopiées de Mutafriches sont comparées à leur source par
`tests/test_miroirs.py` quand le dépôt voisin `../mutafriches` est présent.

`scripts/e2e.sh` joue le parcours du prototype dans QGIS sur un profil temporaire (le profil
de l'utilisateur n'est pas modifié) : captures dans `captures/`, rapport et journal dans
`dist/e2e/`.

### Données de démonstration

`python3 outils/figer_attributaire.py` (réseau) gèle la table attributaire de Montereau
(`mutafriches/demo/montereau/`) et en dérive le fichier CNIG d'exemple et un fichier refusé.

Les données du parcours site à site (conservées pour une future vue de détail) :
`./outils/figer-reponses.sh` régénère tout :

- `outils/generer_terrain.py` (Python de QGIS, réseau requis) interroge le WFS de la
  Géoplateforme et écrit les parcelles d'exemple (`mutafriches/demo/terrain/`) ; il prépare
  les entrées du gel (`outils/sources-scenarios/`) ;
- `outils/figer-reponses.ts` exécute le calcul de mutabilité du dépôt voisin `../mutafriches`
  sur ces entrées et fige les réponses (`mutafriches/demo/scenarios/`, `generique.json`), avec
  les étiquettes du podium calculées par le code de l'interface web. Le plugin n'embarque que
  ces réponses, jamais l'algorithme. Prérequis : `pnpm install` et
  `pnpm --filter shared-types build` dans Mutafriches.

Sources des parcelles d'exemple : Parcellaire Express (PCI) © IGN, Licence Ouverte 2.0 ; friche
de la station-service : [Cartofriches](https://cartofriches.cerema.fr), Cerema. Illustrations des
usages reprises de l'application Mutafriches.

Voir [AGENTS.md](AGENTS.md) pour l'architecture et les conventions, et `docs/adr/` pour les
choix structurants.
