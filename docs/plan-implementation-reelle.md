# Plan d'implémentation réelle du prototype

Date : 2026-11-06. Base : prototype V0 (ADR-0002) et inventaire du dépôt Mutafriches sur `main`
(4973353f). Ce qui suit distingue ce qui existe, ce qui manque, et l'ordre proposé.

## Constat côté Mutafriches

| Besoin du plugin | Existe | Manque |
|---|---|---|
| Identifier l'utilisateur | `integrateur` déduit de l'hôte `Origin` (liste blanche `ALLOWED_INTEGRATOR_ORIGINS`), `visitorId` anonyme, `partenaire:<slug>` | Table utilisateur ou contact, e-mail, consentement, clé d'API (piste `X-API-Key` dans ADR-0011, jamais faite), route d'inscription |
| Tracer l'usage | Table `evenements_utilisateur`, enum `TypeEvenement`, `POST /evenements` ; colonnes `source_utilisation` et `integrateur` sur enrichissements, sites, évaluations | `POST /evenements` fermé aux origines tierces (`OriginGuard` strict, `ALLOWED_ORIGINS` remplace la liste), `integrateur` ignoré dans le corps, aucune valeur « qgis » |
| Envoyer un inventaire | `POST /enrichissement` (un site, 60 parcelles max), `POST /api/partenaires/:slug/sites` (20 max, partenaire existant), moteur de script coordonnées → IDU (ADR-0029), export CNIG | Import CNIG, route par lot, résolution géométrie → IDU côté API, contrôles de contiguïté, surface et commune, traitement asynchrone et suivi de tâche |
| Recevoir enrichissement et mutabilité | `POST /enrichissement` puis `POST /evaluation/calculer` (9 champs, « ne-sait-pas » permis), caches 24 h, `GET /evaluation/:id` | Appel unique enrichissement + calcul ; `getPodiumTags` n'existe que dans l'UI web |
| Tableau de bord territorial | `GET /api/attributaire/sites?codeInsee=` (ouvert, cache 5 min, indices homogènes, usage prioritaire, exclus, fiabilité) | Échelles EPCI et département, filtre par inventaire, agrégats côté API |

Contraintes transverses : 100 requêtes par minute et par IP, corps JSON de 2 Mo, quota BDNB
d'environ 10 000 appels par mois et par IP, aucun délai global de requête, aucune file de
tâches.

## Volet Mutafriches

### M1. Clients d'intégration et clé d'API (ADR)

- Table `integrateurs_clients` : `id`, `cle_api` (hachée), `nom_client` (« qgis »), `version`,
  `structure`, `email`, `consentement_contact` (bool + date), `created_at`, `derniere_activite`.
  Données personnelles : finalité, durée de conservation (36 mois comme le reste), purge à
  prévoir ; mentionner dans la politique de confidentialité.
- `POST /api/clients/inscription` : `{client: "qgis", version, structure, email, consentement}`
  → `{cleApi}`. Rate limit serré, pas de guard `Origin`. Un e-mail = une clé, réémission possible.
- `ApiKeyGuard` acceptant `X-API-Key` en alternative à `Origin` sur `POST /enrichissement`,
  `POST /evaluation/calculer`, `POST /evenements` et les nouvelles routes. Remplit
  `source_utilisation = API_CLIENT` (nouvelle valeur de `SourceUtilisation`, colonne varchar) et
  `integrateur = qgis:<id client>`.
- Metabase : ajouter `WHEN integrateur LIKE 'qgis:%' THEN 'Plugin QGIS'` au bloc `CASE`.

### M2. Tracking depuis le plugin

- Ouvrir `POST /evenements` aux clients à clé (guard ci-dessus), lire `integrateur` depuis le
  contexte de la clé, plus `client_version`.
- Nouveaux `TypeEvenement` (migration de l'enum) : `qgis_ouverture_panneau`,
  `qgis_import_inventaire` (`donnees` : nombre de lignes, OK, KO), `qgis_analyse_lancee`,
  `qgis_analyse_terminee` (durée, sites OK, sites en échec), `qgis_ouverture_table`,
  `qgis_ouverture_site_carte`.
- Dashboard Metabase 9 : onglet « Plugin QGIS » (installations actives, inventaires envoyés,
  sites analysés, durée médiane, taux d'échec).

### M3. Import d'inventaire CNIG et traitement par lot (ADR)

- `POST /api/inventaires` : corps JSON `{format: "cnig-csv"|"cnig-geojson", contenu}` ou
  multipart. Analyseur CNIG en entrée dans `packages/shared-types/src/cnig/` (symétrique de
  `construireFricheCnig`), validation ligne à ligne renvoyée telle quelle : `site_id` unique,
  `comm_insee`, `unite_fonciere_refcad` (IDU normalisés par `normalizeParcelId`), `geompoint`.
  Réponse : `{inventaireId, lignes: [{ligne, siteId, statut: ok|ko, erreurs[]}]}`.
- Table `inventaires` (`id`, `client_id`, `nom`, `code_insee_dominant`, `nb_sites`,
  `statut`, dates) et `inventaire_sites` (`inventaire_id`, `site_id_cnig`, `cle_site`,
  `statut`, `erreur`, `evaluation_id`). Réutiliser `cleSite()` de la table attributaire.
- `POST /api/inventaires/:id/analyser` : lance le traitement côté serveur, site par site,
  enrichissement puis calcul avec « ne-sait-pas » ou avec les valeurs CNIG traduites
  (`bati_etat`, `bati_patrimoine`, `sol_pollution_existe`, `proprio_personne` : inverse des
  correspondances de l'export). Concurrence 4, respect du quota BDNB, pas de pré-chauffe.
- `GET /api/inventaires/:id` : avancement (`{traites, total, enCours, erreurs[]}`) interrogé par
  le plugin toutes les 2 s. Sans file de tâches : exécution dans le processus avec table de
  suivi, suffisant pour quelques dizaines de sites ; passer à une file si des inventaires de
  plusieurs centaines de sites arrivent (précédent EPFGE : 1 300 sites).
- `GET /api/inventaires/:id/resultats?format=geojson` : mêmes colonnes à plat que la table
  attributaire (`indice_<usage>`, `usage_prioritaire`, `usages_exclus`, `fiabilite`,
  `fiabilite_niveau`, critères), plus `site_id`, `site_nom`, `statut`, `erreur`. C'est ce que le
  plugin charge en couche.
- Contrôles de cohérence côté API, absents aujourd'hui : contiguïté (union des géométries
  cadastrales, tolérance 5 cm comme le plugin), surface d'un seul tenant, commune unique,
  60 parcelles max. Statuts : `ok`, `a_verifier` (non bloquant), `erreur`.
- Résolution géométrie → IDU : sortir le moteur de `scripts/coord-to-idu` en service injectable,
  l'exposer dans l'import pour les lignes sans `unite_fonciere_refcad` mais avec `geomsurf`.
  `proj4` passe en dépendance de production.

### M4. Tableau de bord territorial

- `GET /api/inventaires/:id/synthese` : comptages par usage prioritaire, par niveau de fiabilité,
  par profil d'écart (grille à valider), sites à forte compatibilité (seuil repris de
  `badge_potentiel`), sites à reprendre. Calculé côté API pour que le plugin et une future page
  web lisent la même chose.
- Extension de `GET /api/attributaire/sites` aux échelles `?epci=` et `?departement=` (sujet
  déjà ouvert), utile pour comparer l'inventaire à la commune.
- Partager `getPodiumTags` dans shared-types si les étiquettes doivent apparaître dans QGIS.

### Ordre et dépendances côté Mutafriches

1. M1 (clé d'API, inscription, source `API_CLIENT`) : préalable à tout le reste.
2. M3 sans asynchrone : import + validation ligne à ligne, puis analyse synchrone par site
   (le plugin enchaîne lui-même) ; c'est le minimum pour un vrai parcours.
3. M2 (événements) : court, dès que M1 existe.
4. M3 asynchrone et M4 : quand le volume le justifie.

## Volet plugin

### P1. Client HTTP et configuration

- `core/client_http.py` implémentant l'interface `ServiceMutafriches` étendue :
  `inscrire(structure, mail, consentement) -> cle`, `importer_inventaire(fichier)`,
  `analyser(inventaire_id, progression, succes, echec)`, `resultats(inventaire_id)`,
  `evenement(type, donnees)`. Via `QgsNetworkAccessManager` (proxy et certificats QGIS),
  réponses asynchrones, annulation, délais explicites.
- URL de base et clé stockées dans `QgsSettings` (`mutafriches/api/url`, `mutafriches/api/cle`),
  la clé dans `QgsAuthManager` de préférence. Réglage « environnement » (prod, préprod, local).
- `User-Agent: mutafriches-qgis/<version> QGIS/<version>` pour le suivi côté serveur.

### P2. Accueil réel

- L'accueil appelle `POST /api/clients/inscription`, stocke la clé, affiche l'erreur réseau. Le
  consentement reste obligatoire pour l'envoi de l'e-mail, pas pour utiliser le plugin : sans
  consentement, inscription avec e-mail quand même (nécessaire à la clé) mais
  `consentement_contact = false`.
- Bandeau « Mode démonstration » remplacé par un indicateur d'environnement.

### P3. Import et contrôle

- Garder le contrôle local ligne à ligne (`core/cnig.py`) comme première barrière, puis
  envoyer le fichier et fusionner avec la validation serveur (même format de retour).
- Supprimer l'appariement par parcelles sur la table figée (`core/attributaire.apparier`) : les
  résultats viennent de `GET /api/inventaires/:id/resultats`.

### P4. Analyse et résultats

- Barre de progression réelle (`traites / total`), annulation, reprise après erreur
  partielle : les sites en erreur apparaissent dans « Sites à reprendre » avec le motif serveur.
- Couches : inchangées (`carto/couches.py`), alimentées par le GeoJSON serveur ; conserver la
  symbologie, les étiquettes et le clic site → carte.
- Synthèse : lue depuis `GET /api/inventaires/:id/synthese` ; `core/attributaire.synthese`
  devient un simple adaptateur. Les seuils (profils, forte compatibilité) ne vivent plus dans
  le plugin.

### P5. Tracking

- Appels `POST /evenements` non bloquants, sans réessai, désactivables dans les réglages.

### P6. Qualité et livraison

- Tests unitaires avec un serveur HTTP local factice (`http.server`) rejouant les fixtures
  actuelles de Montereau : le service simulé reste le mode hors ligne du plugin.
- E2E QGIS contre la préprod, avec la clé d'un compte de test.
- ADR-0003 (client HTTP, stockage de la clé, environnements), README, bump de version,
  publication sur le dépôt d'extensions QGIS en `experimental`.

### Ordre côté plugin

P1 puis P2 dès que M1 est en préprod ; P3 et P4 dès que M3 synchrone existe ; P5 avec M2 ;
P6 en continu. Tant que M3 n'existe pas, le plugin peut déjà fonctionner en « vrai » sur un
inventaire en enchaînant lui-même `POST /enrichissement` et `POST /evaluation/calculer` site
par site (sous la limite de 100 requêtes par minute) : c'est une étape intermédiaire possible
pour valider le parcours sans attendre l'import serveur.

## Points à trancher

- Où vit la donnée personnelle (structure, e-mail) : Mutafriches ou Notion comme aujourd'hui
  pour les intégrateurs ? Le plan suppose Mutafriches, avec purge.
- Un inventaire envoyé alimente-t-il la table attributaire publique (`attributaire_sites`)
  comme un site partenaire, ou reste-t-il privé au client ? Le plan suppose privé par défaut.
- Seuils des profils de sites et de la forte compatibilité : à fixer côté API, une fois.
- Volume cible par inventaire : en dessous de 50 sites, le synchrone suffit ; au-delà, file de
  tâches.
