# ADR-0004 : Réglages déclarés dans QGIS et page « Mutafriches » des options

- Statut : accepté
- Date : 2026-11-11

## Contexte

Les réglages de l'extension (environnement, adresse d'API, mode développeur, informations de
l'utilisateur) étaient de simples clés `mutafriches/...` dans `QgsSettings`. Pour les modifier,
il fallait la console Python ou une variable d'environnement : l'éditeur avancé de QGIS 3.44
n'affiche que les réglages déclarés et ne permet pas d'en créer. Le sélecteur de staging vivait
dans le panneau, visible seulement après cette manipulation.

## Décision

- **Réglages déclarés** dans l'arbre de QGIS (`QgsSettingsTree.createPluginTreeNode`), sous
  `plugins/mutafriches/` : ils apparaissent avec leur description dans Préférences › Options ›
  Avancé. Module unique `core/reglages.py` ; plus aucune clé en dur ailleurs.
- **Page « Mutafriches »** dans Préférences › Options (`QgsOptionsWidgetFactory`), aussi
  ouverte par le lien « Réglages » du panneau et par le menu de l'extension. Quatre blocs :

| Bloc | Réglages | Public |
|---|---|---|
| Service | Environnement : production ou démonstration | Tous |
| Vos informations | Structure, mail, consentement, bouton « Effacer » | Tous |
| Carte | Fond OpenStreetMap à l'ouverture d'un projet vide | Tous |
| Développement | Mode développeur ; staging, adresse d'API libre, origine, délai entre sites | Équipe |

- **Mode développeur** : une case de la page (ou `MUTAFRICHES_DEV=1`). Sans lui, le staging et
  l'adresse libre sont ignorés même s'ils sont enregistrés : un réglage oublié ne peut pas
  détourner les analyses d'un utilisateur.
- **Non exposés** : seuils d'affichage du tableau de bord, critères, tout ce qui relève du
  calcul. Ils appartiennent à Mutafriches.
- **Reprise** : les clés des versions 0.1.x sont copiées une fois vers les nouvelles, puis
  effacées (`migrer_anciens_reglages`).
- Un changement de service depuis les options vide les résultats et retire les couches, comme
  le faisait le sélecteur du panneau.

## Conséquences

- Le sélecteur d'environnement du panneau disparaît ; le lien production / démonstration reste.
- `scripts/reinitialiser.sh` reste utile QGIS fermé, mais le bouton « Effacer mes informations »
  le remplace dans l'usage courant.
- Les profils de test (E2E, captures) écrivent leurs réglages dans la section `[plugins]` du
  fichier de profil, avec `mutafriches\dev=true` pour qu'une adresse d'API locale soit lue.
- Version 0.2.0.
