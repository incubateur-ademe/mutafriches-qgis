# mutafriches-qgis

Extension QGIS de [Mutafriches](https://mutafriches.beta.gouv.fr) — **maquette locale non
publiée**.

Le panneau reprend le parcours de l'application web : sélection des parcelles d'un site dans une
couche QGIS, trois étapes de qualification, puis mutabilité sur sept usages et fiabilité.

> **Données fictives.** Les données récupérées et les résultats sont simulés à partir de
> réponses figées par le calcul Mutafriches : aucun appel à l'API n'est effectué.

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

Le panneau reprend le wording et le parcours de l'application web (`/analyser`, puis les 3 étapes
de qualification et `/resultats`).

1. Ouvrir le panneau **Mutafriches**.
2. Dans le panneau Couches, sélectionner une couche de parcelles (n'importe quelle couche de
   polygones ; l'identifiant cadastral est repéré dans un champ `idu` ou `id`). Sans couche
   sous la main : lien **Ajouter des parcelles d'exemple** (Trélazé, parcellaire IGN).
3. Cliquer sur une parcelle, puis sur une parcelle adjacente pour l'ajouter au site, puis
   **Analyser ce site** (environ 2 secondes de qualification automatique).
4. Compléter les 3 étapes : chaque liste démarre sur « Sélectionner une option » et doit être
   renseignée (« Ne sait pas » est possible). Le « ? » de chaque champ donne son aide ou sa source.
5. Résultats : indice de fiabilité, **voir récapitulatif du site**, podium des 3 usages les plus
   compatibles, tableau de tous les usages (survol : aperçu ; clic : détail des critères).

Parcelles d'exemple avec des réponses détaillées (toute autre sélection reçoit un profil
générique) :

- **Ancienne station-service** (11 ter rue Joseph Le Sciellour, friche Cartofriches) :
  AV 1255, 1256, 1257, 1258 ;
- **AV 1351** (sans adresse, à côté du 7 rue Pierre Timbaud) : site d'une parcelle ;
- **AV 1349 et AV 1350** (près du 18 square des Forges) : premier appel en échec (bouton
  Réessayer), puis trois données indisponibles.

Le site analysé est une sélection dans une couche QGIS : l'extension n'enregistre rien. Les
surfaces sont mesurées sur la géométrie (en Lambert 93, quel que soit le SCR de la couche) ; les
autres données et les indices sont fictifs.

## Développement

```bash
./scripts/tests.sh     # Tests unitaires avec le Python de QGIS (sans interface)
./scripts/package.sh   # ZIP installable
./scripts/e2e.sh       # Parcours complet dans une vraie session QGIS, sur un profil isolé
```

`scripts/e2e.sh` ouvre QGIS deux fois (parcelles d'exemple, puis couche utilisateur en WGS84
dans un projet en Web Mercator), sur un profil temporaire dans `dist/e2e/` : le profil de
l'utilisateur n'est pas modifié. Captures et rapports sont écrits dans `dist/e2e/`.

### Données de démonstration

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
