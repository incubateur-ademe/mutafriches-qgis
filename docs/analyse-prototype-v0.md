# Analyse du besoin — prototype V0 (captures d'écran)

Date : 2026-11-05. Contexte : revue de l'expérience du plugin à partir des maquettes (accueil,
table multisite, dashboard, comparaison) et de la table attributaire ajoutée à Mutafriches.

## Ce que le prototype montre

| Étape | Écran | Ce qui est réel | Ce qui est figé |
|---|---|---|---|
| 1 | Fenêtre d'accueil : structure, mail, consentement | Saisie, validation, mémorisation QGIS | Rien n'est transmis |
| 2 | Envoi des sites au format CNIG | Lecture CSV/GeoJSON, contrôle des colonnes et des lignes, messages d'erreur | — |
| 3 | Analyse en cours | Attente de 2,5 s | Pas d'appel API |
| 4 | Panneau résultats + carte | Couches QGIS, symbologie, étiquettes, légende, tables attributaires | Table attributaire de Montereau (28 sites, algorithme v1.19, figée le 2026-11-05) |
| 5 | Tableau de bord territorial | Page DSFR + dsfr-chart dans le navigateur | Mêmes données |

## Réponses aux points ouverts

- **Table mutabilité** : colonnes dans l'ordre demandé, noms CNIG/`mf_*`. Le « % de
  compatibilité » est l'indice de mutabilité de l'usage prioritaire : il reste nommé « indice »,
  jamais « probabilité ».
- **Table qualification** (proposition) : critères automatiques lisibles + critères terrain en
  clair + `saisie_declarative` + données manquantes. Elle répond à « que sait-on de ce site, et
  que reste-t-il à renseigner ? », complément naturel de la table mutabilité.
- **Fiabilité** : raisonner en échelons de sites (niveaux de l'API) plutôt qu'en moyenne ; la
  moyenne est affichée mais en second.
- **Profils de sites** : table de correspondance à cinq classes sur l'écart intra-site, reprise
  de la maquette, libellés proposés : plat, peu contrasté, modéré, net, fort. À valider.
- **Carto** : étiquette « nom · usage · indice % » sur fond coloré par usage, légende par usage
  dans le panneau Couches. Faisable avec la symbologie native (catégorisée + étiquettes à
  propriété définie par expression), sans couche supplémentaire.
- **dsfr-chart dans QGIS** : impossible dans le panneau (pas de WebEngine, WebKit trop ancien) ;
  ouverture dans le navigateur. Alternative plus tard : graphiques Qt natifs dans le panneau.

## Hypothèses à confirmer

1. L'ordre des colonnes d'usage (« usages qui remontent le plus ») : à fournir depuis Metabase.
2. Les seuils des profils de sites et le libellé « forte compatibilité » (≥ 70).
3. Le fichier CNIG envoyé par l'utilisateur sera-t-il traité par une nouvelle route API
   (`POST` d'un inventaire) ou par la route par commune existante ? Le prototype apparie par
   parcelles, ce qui suppose la seconde.
4. Les liens « vers la carto » depuis le tableau de bord : impossibles depuis un navigateur
   externe ; prévoir plutôt une sélection dans QGIS depuis le panneau.
