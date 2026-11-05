# mutafriches-qgis

Extension QGIS de [Mutafriches](https://mutafriches.beta.gouv.fr) — **maquette locale non
publiée**.

Prototype V0 (ADR-0002) : l'utilisateur se présente, envoie son inventaire de sites au
**standard CNIG Friches**, et reçoit une table attributaire de mutabilité, une table de
qualification, une carte symbolisée par usage et un tableau de bord territorial (DSFR,
dsfr-chart) ouvert dans le navigateur. Objectif : captures d'écran.

> **Données figées.** Les résultats sont ceux de la table attributaire publique de
> Montereau-Fault-Yonne (77305), gelée dans le plugin : aucun appel à l'API n'est effectué.

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

1. Ouvrir le panneau **Mutafriches** : la fenêtre d'accueil demande structure et mail (une fois).
2. Choisir un fichier CNIG Friches (CSV ou GeoJSON), ou cliquer **Utiliser l'exemple de
   Montereau-Fault-Yonne** (28 sites). **Voir un fichier refusé** montre l'écran d'erreur.
3. **Envoyer mes 28 sites** : après l'attente, deux couches apparaissent (Mutabilité, étiquetée
   par usage et indice ; Qualification, masquée), avec un fond OpenStreetMap si le projet était
   vide.
4. Panneau : chiffres clés, répartition des usages et de la fiabilité, sites à forte
   compatibilité. Boutons **Table mutabilité**, **Table qualification**, **Ouvrir le tableau de
   bord territorial** (navigateur), **Zoomer sur les sites**, **Nouvelle analyse**.

Un fichier CNIG d'une autre commune est accepté mais ses sites ne sont pas retrouvés dans la
table figée : le panneau le signale et affiche les résultats de Montereau.

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

```bash
./scripts/tests.sh     # Tests unitaires avec le Python de QGIS (sans interface)
./scripts/package.sh   # ZIP installable
./scripts/e2e.sh       # Parcours complet dans une vraie session QGIS, sur un profil isolé
```

`scripts/e2e.sh` joue le parcours du prototype dans QGIS sur un profil temporaire (le profil
de l'utilisateur n'est pas modifié) et écrit captures et rapport dans `dist/e2e/` : accueil,
fichier refusé, exemple, résultats, tables attributaires. Le tableau de bord généré est copié
dans `dist/e2e/tableau-de-bord.html`.

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
