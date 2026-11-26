# mutafriches-qgis

Extension QGIS de [Mutafriches](https://mutafriches.beta.gouv.fr) — **maquette locale non
publiée**.

Prototype V0 (ADR-0002) : l'utilisateur se présente, envoie son inventaire de sites au
**standard CNIG Friches**, et reçoit une table attributaire de mutabilité, une table de
qualification, une carte symbolisée par usage et un tableau de bord territorial dans le
panneau. Objectif : captures d'écran.

> **Production seule.** Chaque site est enrichi puis évalué par l'API Mutafriches de production
> (ADR-0003), au nom de la structure déclarée à l'accueil. L'extension n'a ni démonstration, ni
> choix d'environnement, ni mode développeur (ADR-0006).

Seule version testée : **QGIS 3.44.14 sous macOS (Apple Silicon)**.

## Installation

1. Télécharger [la dernière version de l'extension](https://github.com/incubateur-ademe/mutafriches-qgis/releases/latest/download/extension-qgis-mutafriches.zip),
   ou construire le ZIP : `./scripts/package.sh` → `dist/mutafriches-<version>.zip`
2. Dans QGIS : **Extensions › Installer/Gérer les extensions › Installer depuis un ZIP**,
   choisir le fichier, puis **Installer l'extension**. Accepter l'avertissement sur les
   extensions non vérifiées (extension locale).
3. Un bouton **Mutafriches** apparaît dans une barre d'outils dédiée.

Pour mettre à jour : reconstruire le ZIP et le réinstaller par le même écran (la version
précédente est remplacée).

## Tester en 3 minutes

1. Ouvrir le panneau **Mutafriches** : il demande de déclarer sa structure (nom, type, domaine, prénom,
   nom et e-mail, obligatoires, une fois), avec une case décochée par défaut, elle aussi
   obligatoire, pour accepter d'être contacté (retours d'expérience, évolutions du service). Une fois la structure
   déclarée, ces informations ne sont plus modifiables dans l'extension. Sur un projet
   vide, un fond OpenStreetMap cadré sur la France est ajouté ; un projet qui a déjà des couches
   n'est pas modifié.
2. Choisir un fichier CNIG Friches (CSV ou GeoJSON). Chaque ligne est contrôlée et affichée
   OK ou KO avec ses erreurs ; les lignes KO sont écartées de l'envoi. Deux encadrés résument le
   contrôle, chacun seulement s'il a des sites : les sites KO, puis les sites OK. L'infobulle du champ
   propose **Télécharger un modèle de fichier vide** : les 51 colonnes du standard, sans aucune
   ligne, à remplir avec vos sites. Envoyé tel quel, il est refusé (« aucun site »).
   Pour un essai, utiliser `tests/donnees/friches-cnig-montereau.csv` (28 sites) ou
   `friches-cnig-erreurs.csv` (4 sites corrects, 6 lignes en erreur), contre une API de test.
3. **Analyser mes N sites** : après l'attente, deux couches apparaissent (Mutabilité, étiquetée
   par usage et indice ; Qualification, masquée), avec un fond OpenStreetMap si le projet était
   vide.
4. Panneau résultats, tableau de bord territorial : bouton **Comprendre les résultats** (page
   « Comprendre les analyses » du site, critères et sources ; l'URL porte `?source=qgis`, lu par
   le suivi d'événements du site), nombre de sites, fiabilité moyenne et lien
   **Améliorer la fiabilité** (table de qualification, critères de terrain inconnus en rouge),
   répartition des usages les plus compatibles, sites à forte compatibilité (cliquer un site le
   sélectionne et cadre la carte), profils des sites. Les sites non analysés sont signalés dans
   la barre de messages de QGIS. Boutons **Voir table de mutabilité** et **Voir table de
   qualification** ; lien **Analyser un autre inventaire** à côté du logo.
   Les tables s'ouvrent aussi depuis le panneau Couches : clic droit sur la couche, « Ouvrir la
   table d'attributs », ou F6 sur la couche sélectionnée.

### Réglages

Les réglages sont dans **Préférences › Options › Mutafriches**, page aussi ouverte par le menu
Extensions › Mutafriches (ADR-0004). Le panneau n'a ni lien de réglages ni bascule de mode :

| Bloc | Contenu |
|---|---|
| Vos informations | Structure, type, domaine, prénom, nom, e-mail et accord pour être contacté : en lecture seule |
| Carte | Ajouter ou non le fond OpenStreetMap à l'ouverture d'un projet vide |

L'extension n'interroge que la production, `https://mutafriches.beta.gouv.fr` : aucun réglage ne
permet d'en changer (ADR-0006). Les réglages sont enregistrés sous `plugins/mutafriches/` et
visibles dans Options › Avancé.

Pour les tests et les captures, l'équipe désigne une autre API au lancement de QGIS :

```bash
MUTAFRICHES_API_URL=https://mutafriches.incubateur.ademe.dev /Applications/QGIS.app/Contents/MacOS/QGIS
```

Le panneau affiche alors le bandeau « Environnement de test », suivi de l'adresse.
`MUTAFRICHES_INTERVALLE_MS` raccourcit le délai entre deux sites ; elle n'est lue que face à une
API de test.

L'extension déclare la structure au registre des intégrateurs de Mutafriches
(`POST /api/integrateurs/declarations`, canal `qgis`, ADR-0005), une fois par adresse d'API, puis
appelle l'API avec le domaine déclaré dans `Origin` et `X-Mutafriches-Client: qgis/<version>`.
Prénom, nom et e-mail sont conservés dans l'outil d'e-mailing de Mutafriches (Brevo), pas dans
sa base. L'e-mail, obligatoire, sert au suivi de l'accès ; la case d'accord pour être sollicité,
obligatoire elle aussi (ADR-0006), est transmise en `accepteContact: true`. Une API sans registre (production avant déploiement) reçoit l'origine historique
`https://qgis.mutafriches.beta.gouv.fr`. Un site prend deux à cinq secondes ; un site dont la réponse dépasse le délai réseau
de QGIS (60 s par défaut) est retenté une fois, puis listé en échec sans interrompre les
suivants.

Pour jouer le parcours sans appeler Mutafriches : `python3 tests/serveur_factice.py 8799`, puis
lancer QGIS avec `MUTAFRICHES_API_URL=http://127.0.0.1:8799`.

### Revoir l'accueil

L'accueil (déclaration de la structure) n'est proposé que tant qu'elle est incomplète. Une fois
la structure déclarée, ses coordonnées ne se modifient plus dans l'extension (ADR-0006) : la
désinstaller ne les efface pas, QGIS garde ses réglages dans le profil. Le lien **Modifier**, en
bas de la page d'envoi, ne revient qu'après un refus d'accès de l'API. Pour repartir de zéro,
QGIS fermé : `./scripts/reinitialiser.sh`, qui oublie aussi les déclarations faites.

## Tester de bout en bout (équipe)

Deux inventaires de **vrais sites** de Montereau-Fault-Yonne sont joints à chaque release, pour
jouer le parcours complet contre l'API :

| Fichier | Sites | Durée indicative |
|---|---|---|
| [friches-cnig-test-montereau-5-sites.csv](https://github.com/incubateur-ademe/mutafriches-qgis/releases/latest/download/friches-cnig-test-montereau-5-sites.csv) | 5 | une vingtaine de secondes |
| [friches-cnig-test-montereau.csv](https://github.com/incubateur-ademe/mutafriches-qgis/releases/latest/download/friches-cnig-test-montereau.csv) | 28 | deux à trois minutes |

1. Lancer QGIS avec `MUTAFRICHES_API_URL=https://mutafriches.incubateur.ademe.dev` : le panneau affiche le bandeau « Environnement de test ».
2. Charger l'un des deux fichiers, puis **Analyser mes N sites**.

Ces fichiers servent aux tests : envoyés en production, ils ajoutent leurs sites à la table
attributaire publique de la commune et pèsent sur les statistiques d'usage. Le panneau ne les
propose pas ; le tutoriel web donne le lien du fichier de 5 sites, pour un premier essai.
`scripts/package.sh` les produit dans `dist/` à partir de
`tests/donnees/friches-cnig-montereau.csv`.

## Publier une version

Pousser le tag de la version, une fois le bump fusionné dans `main` :

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

`.github/workflows/release.yml` construit alors le paquet et joint quatre fichiers à la release :
`mutafriches-X.Y.Z.zip`, sa copie `extension-qgis-mutafriches.zip` et les deux inventaires de test.
Le bouton « Télécharger l'extension » du site vise
`releases/latest/download/extension-qgis-mutafriches.zip` : une release publiée sans ce fichier
casse le bouton. Ne pas renommer ce fichier sans changer le lien dans le dépôt Mutafriches
(`apps/ui/src/features/integrer/data/tutoriel-qgis.ts`).

## Captures

`./scripts/e2e.sh` écrit les captures de la fenêtre QGIS dans `captures/` (local, ignoré par git).

### Captures du tutoriel web

`./scripts/captures-tutoriel.sh` joue le parcours nominal dans QGIS contre l'API de staging,
jamais la production, et écrit 11 captures WebP (1600 px) dans
`../mutafriches/apps/ui/public/images/tutoriel-qgis/`, lues par la page
`/utiliser-mutafriches/extension-qgis` de Mutafriches. Le bandeau de test y est masqué. Chaque
passage analyse réellement 28 sites sur le staging. `MF_TUTORIEL_API` change l'API visée, `MF_TUTORIEL_ETAPES=2`
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

### Jeux d'essai et données figées

`python3 outils/figer_attributaire.py` (réseau) gèle la table attributaire de Montereau dans
`tests/donnees/` et en dérive l'inventaire CNIG d'essai et un fichier avec erreurs : ces fichiers
servent aux tests, au serveur factice et aux captures, et restent hors du ZIP. Le même outil écrit
le modèle de fichier vide de l'extension (`mutafriches/modeles/modele-cnig.csv`).

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
