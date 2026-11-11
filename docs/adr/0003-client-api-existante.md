# ADR-0003 : Mode réel sur l'API Mutafriches existante, sans changement côté API

- Statut : accepté
- Date : 2026-11-11

## Contexte

Le prototype V0 (ADR-0002) affiche une table attributaire figée. L'API Mutafriches n'a ni
import d'inventaire, ni route par lot, ni table d'utilisateurs, ni clé d'API, et
`POST /evenements` est fermé aux origines tierces (analyse du dépôt, `docs/plan-implementation-reelle.md`).
Attendre ces évolutions (chantiers M1 à M4 du plan) retarderait tout usage réel.

## Décision

L'extension appelle l'API telle qu'elle est :

- **Un site = deux appels**, enchaînés par l'extension : `POST /enrichissement`
  (`{identifiants}`) puis `POST /evaluation/calculer` (`{donneesEnrichies, donneesComplementaires}`).
  Séquentiel, un site toutes les 1,5 s au plus (limite de 100 requêtes par minute et par IP),
  attente et nouvel essai sur un 429, annulation possible, erreur site par site.
- **Origine conventionnelle** `https://qgis.mutafriches.beta.gouv.fr`, posée dans l'en-tête
  `Origin` et à déclarer dans `ALLOWED_INTEGRATOR_ORIGINS` (procédure intégrateur de Mutafriches).
  Elle sert d'identifiant `integrateur` dans les statistiques. Tant qu'elle n'est pas déclarée,
  l'API répond 403 : l'extension l'explique et propose le mode démonstration.
- **Critères manuels** : les 9 champs sont envoyés, « ne-sait-pas » par défaut. Quatre colonnes
  CNIG (`bati_etat`, `bati_patrimoine`, `bati_pollution`, `sol_pollution_existe`) sont traduites
  quand la valeur est sans ambiguïté (inverse de l'export CNIG de Mutafriches).
- **Résultats** : la ligne attributaire d'un site est construite depuis les deux réponses
  (`core/attributaire.site_depuis_api`, miroir de `resumerPourAttributaire`). Couches, tables et
  tableau de bord sont inchangés.
- **Identification** : structure, mail et consentement restent dans le profil QGIS. Rien n'est
  envoyé à Mutafriches, faute de route pour les recevoir.
- **Trois environnements** : `production` (défaut), `staging`
  (`https://mutafriches.incubateur.ademe.dev`) et `demonstration` (table figée de Montereau).
  Les utilisateurs basculent entre production et démonstration ; le staging n'est proposé qu'en
  mode développeur (`MUTAFRICHES_DEV=1` ou réglage `mutafriches/dev`). Un bandeau permanent
  signale tout environnement autre que la production, et un changement d'environnement vide les
  résultats et retire les couches, pour ne jamais afficher des résultats de test comme réels.
  Même origine sur les deux API : leurs bases sont séparées. Réglages
  `mutafriches/api/{environnement,url,origine,intervalle_ms}` dans `QgsSettings`.
- Réseau par `QgsNetworkAccessManager` (proxy et certificats de QGIS), délai de 90 s par requête.

## Conséquences

- Aucun déploiement côté Mutafriches : une variable d'environnement et une ligne Metabase.
- Tous les utilisateurs partagent la même origine : pas de distinction par structure, pas
  d'événements fins. Reportés aux chantiers M1 et M2.
- Tout site analysé entre dans la table attributaire publique de sa commune.
- Les seuils d'affichage (profils, forte compatibilité) restent dans l'extension jusqu'à M4.
- Un inventaire de 100 sites prend plusieurs minutes et pèse sur le quota BDNB : au-delà d'une
  cinquantaine de sites, attendre l'import serveur (M3).
- Tests : `tests/serveur_factice.py` rejoue la table figée sous la forme des vraies réponses et
  contrôle `Origin` ; les tests unitaires et l'E2E QGIS jouent le mode réel contre lui. Le mode
  réel a été joué contre le staging le 2026-11-11 (origine déclarée) : inventaire de 28 sites de
  Montereau-Fault-Yonne, trois passages. L'un a vu une requête dépasser le délai réseau de QGIS
  (60 s) : un délai dépassé est depuis retenté une fois, puis compté comme l'échec du site seul.
