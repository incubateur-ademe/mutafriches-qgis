# ADR-0002 : Prototype V0 — inventaire CNIG en entrée, table attributaire et tableau de bord en sortie

- Statut : accepté (prototype, captures d'écran)
- Date : 2026-11-05

## Contexte

Le parcours site à site de la maquette (ADR-0001) ne montre pas la valeur du plugin pour une
collectivité ou une agence qui arrive avec un **inventaire de friches**. Mutafriches expose
désormais une table attributaire par commune (`GET /api/attributaire/sites`, ADR-0053 du
dépôt Mutafriches) et un export au standard CNIG Friches. Le besoin : un flux « j'envoie mes
sites, je reçois une table de mutabilité, une table de qualification et un tableau de bord
territorial », à présenter en captures d'écran avant tout développement réel.

## Décision

1. **Entrée au standard CNIG Friches** (CSV ou GeoJSON, TableSchema `cnigfr/schema-friches`
   v1.0.6). Le plugin contrôle les colonnes obligatoires (`site_id`, `site_nom`, `comm_insee`,
   `unite_fonciere_refcad`, `geompoint`), l'unicité des identifiants, le format des parcelles et
   du code INSEE, et refuse le fichier en listant les erreurs ligne par ligne.
2. **Résultats figés** : la réponse GeoJSON publique de Montereau-Fault-Yonne (77305) est
   gelée dans le plugin par `outils/figer_attributaire.py`. Les sites du fichier envoyé sont
   appariés à la table par leurs parcelles ; à défaut, la table entière est affichée avec un
   avertissement. Aucun calcul dans le plugin.
3. **Deux couches mémoire** créées dans le projet :
   - *Mutabilité* : `site_id`, `site_nom`, usage prioritaire (code et libellé), indice de l'usage
     prioritaire, un indice par usage dans l'ordre des usages les plus fréquents, fiabilité (note
     et niveau), usages exclus, nombre de parcelles, `unite_fonciere_refcad`, `comm_insee`,
     version d'algorithme. Noms calqués sur l'extension `mf_*` de l'export CNIG de Mutafriches.
   - *Qualification* : identité du site, douze critères automatiques lisibles (surfaces,
     zonage, centre-ville, commerces, transports, électricité, eau, risques, zonages),
     `saisie_declarative`, date de saisie, les neuf critères terrain en clair, fiabilité et
     liste des données manquantes.
4. **Symbologie livrée** : remplissage par usage prioritaire, étiquette « nom, usage, indice »
   sur fond de la couleur de l'usage, légende dans le panneau Couches. Un fond OpenStreetMap
   est ajouté si le projet est vide.
5. **Tableau de bord territorial dans le panneau**, en widgets Qt natifs : anneaux et barres
   dessinés avec QPainter, petits tableaux en grille. Une première version en HTML avec
   dsfr-chart, ouverte dans le navigateur, a été écartée : sortir de QGIS casse le parcours, et
   ni QtWebEngine (absent sur macOS) ni QtWebKit (syntaxe JavaScript trop ancienne) ni QtCharts
   (non embarqué) ne permettent de l'afficher dans le panneau.
6. **Accueil** : fenêtre modale « qui êtes-vous » (structure, mail, consentement), mémorisée
   dans `QgsSettings`. Prototype : rien n'est envoyé.

## Grilles de lecture

- Niveaux de fiabilité : ceux de l'API (`fiabilite_niveau`, miroir de `NIVEAUX_FIABILITE`).
- Niveaux de compatibilité : paliers d'affichage de l'application web (`badge_potentiel`) ;
  « forte compatibilité » = indice prioritaire supérieur ou égal à 70 (« Excellent »).
- Profils de sites : écart entre le meilleur et le moins bon usage, en cinq classes (moins de
  10, 10 à 15, 15 à 20, 20 à 30, 30 et plus). **Grille propre au prototype, à valider.**
- Ordre des colonnes d'usage : `ORDRE_USAGES` dans `core/attributaire.py`, à caler sur la
  répartition nationale (Metabase) ; valeur provisoire tirée de la table figée.

## Conséquences

- Le parcours site à site (sélection de parcelles, trois étapes de saisie) sort du panneau ;
  `resultats.py`, `recapitulatif.py` et le service simulé restent dans le code pour une future
  vue de détail d'un site.
- Les couleurs des graphiques du panneau sont celles de la carte (une couleur par usage).
- Passage au réel : remplacer `charger_table` par un appel à `GET /api/attributaire/sites`
  (ou un futur `POST` recevant le fichier CNIG), via `QgsNetworkAccessManager`.
