"""Textes et ordre des écrans, repris de l'application web (apps/ui/src/features)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Info:
    """Donnée récupérée automatiquement (EnrichedInfoField)."""

    cle: str
    libelle: str
    aide: str
    lien: str | None = None


@dataclass(frozen=True)
class Saisie:
    """Champ à renseigner (FormSelectField)."""

    cle: str


SEPARATEUR = "separateur"
Element = object

# Ordre des pages QualificationSitePage, QualificationEnvironnementPage, QualificationRisquesPage
ETAPES: dict[int, tuple[str, str, list[Element]]] = {
    1: (
        "Qualifier le site et son bâti",
        "Qualifier l'environnement du site",
        [
            Info("commune", "Commune", "Récupéré depuis l'API IGN Cadastre :", "apicarto.ign.fr/api/doc/cadastre"),
            Info(
                "parcelles",
                "Identifiant parcelle",
                "Récupéré depuis l'API IGN Cadastre :",
                "apicarto.ign.fr/api/doc/cadastre",
            ),
            Info(
                "surfaceSite",
                "Surface du site",
                "Récupéré depuis l'API IGN Cadastre :",
                "apicarto.ign.fr/api/doc/cadastre",
            ),
            Info("surfaceBati", "Surface bâtie", "Récupéré depuis l'API BDNB :", "api-portail.bdnb.io"),
            Saisie("typeProprietaire"),
            SEPARATEUR,
            Info(
                "distanceRaccordementElectrique",
                "Distance au raccordement électrique",
                "Récupéré depuis l'API Enedis :",
                "data.enedis.fr/api/explore/v2.1/catalog/datasets",
            ),
            Info(
                "raccordementEau",
                "Raccordement aux réseaux d'eau",
                "Déduit automatiquement de la présence de bâti sur le site (surface bâtie BDNB). Un "
                "site nu est considéré non raccordé.",
            ),
            Info(
                "distanceReseauChaleur",
                "Distance au réseau de chaleur",
                "Distance séparant le site du réseau de chaleur le plus proche. Récupéré depuis l'API "
                "France Chaleur Urbaine :",
                "data.gouv.fr/dataservices/api-france-chaleur-urbaine",
            ),
            SEPARATEUR,
            Saisie("valeurArchitecturaleHistorique"),
            Saisie("etatBatiInfrastructure"),
            SEPARATEUR,
            Saisie("presencePollution"),
            Info(
                "ilotChaleurUrbain",
                "Site concerné par un îlot de chaleur",
                "Donnée informative : elle n'entre pas dans le calcul de mutabilité. Issue de la "
                "cartographie nationale des indicateurs liés à l'îlot de chaleur urbain (CSTB), qui "
                "couvre environ 600 communes, et à l'intérieur de celles-ci les seules zones urbaines "
                "denses.",
                "data.gouv.fr/datasets/cartographie-nationale-des-indicateurs-lies-a-lilot-de-chaleur-urbain",
            ),
        ],
    ),
    2: (
        "Qualifier l'environnement du site",
        "Qualifier les risques et zonages du site",
        [
            Info(
                "siteEnCentreVille",
                "Site en centre ville",
                "Récupéré depuis l'API de l'annuaire du Service public :",
                "api-lannuaire.service-public.fr",
            ),
            Info(
                "proximiteCommercesServices",
                "Proximité des commerces et services",
                "Récupéré depuis la base permanente des équipements (BPE) :",
                "insee.fr/fr/metadonnees/source/serie/s1161",
            ),
            Info(
                "tauxLogementsVacants",
                "Taux de logements vacants",
                "Récupéré depuis l'API tabulaire de data.gouv.fr :",
                "data.gouv.fr/datasets/logements-vacants",
            ),
            SEPARATEUR,
            Info(
                "distanceTransportCommun",
                "Distance aux transports en commun",
                "Récupéré depuis le jeu de données de Transport.data.gouv.fr :",
                "transport.data.gouv.fr/datasets/arrets-de-transport-en-france",
            ),
            Info(
                "distanceAutoroute",
                "Distance par la route à un accès autoroutier",
                "Distance par la route jusqu'à l'entrée d'autoroute ou de voie express la plus proche, "
                "calculée avec les services IGN Géoplateforme (BD TOPO et calcul d'itinéraire).",
            ),
            Saisie("qualiteVoieDesserte"),
            Info(
                "distanceIte",
                "Distance à une installation de chargement industrielle",
                "Récupéré depuis la base ITE 3000 du Cerema (Installations Terminales Embranchées fret) :",
                "data.gouv.fr/datasets/base-ite-3000",
            ),
            SEPARATEUR,
            Saisie("qualitePaysage"),
            Saisie("trameVerteEtBleue"),
            Saisie("presenceEspecesProtegees"),
            Saisie("presenceZoneHumide"),
        ],
    ),
    3: (
        "Qualifier les risques et zonages du site",
        "Analyse de mutabilité",
        [
            Info(
                "presenceRisquesTechnologiques",
                "Présence de risques technologiques",
                "Récupéré depuis les données de l'API GéoRisques :",
                "georisques.gouv.fr/doc-api",
            ),
            Info(
                "risquesNaturels",
                "Risques naturels",
                "Récupéré depuis les données de l'API GéoRisques :",
                "georisques.gouv.fr/citoyen-recherche-map",
            ),
            SEPARATEUR,
            Info(
                "zonageEnvironnemental",
                "Type de zonage environnemental",
                "Données enrichies via les API Carto Nature et GPU de l'IGN.",
            ),
            Info(
                "zonageReglementaire",
                "Type de zonage réglementaire",
                "Données enrichies via les API Carto Nature et GPU de l'IGN.",
            ),
            SEPARATEUR,
            Info(
                "zonagePatrimonial",
                "Type de zonage patrimonial",
                "Données enrichies via les API Carto Nature et GPU de l'IGN.",
            ),
            Info(
                "zoneAccelerationEnr",
                "Zone d'accélération des énergies renouvelables",
                "Données enrichies via le WFS Géoplateforme (ZAER).",
            ),
            SEPARATEUR,
            Info(
                "zonageAbcLogement",
                "Type de zone pour le logement",
                "Récupéré depuis : Liste des communes selon le zonage ABC (data.gouv.fr).",
            ),
            Info(
                "siteEnQpv",
                "Quartier Prioritaire de la politique de la Ville (QPV)",
                "Site localisé ou non au sein d'un Quartier Prioritaire de la politique de la Ville "
                "(QPV), d'après les périmètres publiés par l'ANCT.",
            ),
            Info(
                "saturationReseauEnr",
                "Saturation électrique du réseau pour projets d'énergies renouvelables",
                "Données Enedis et RTE, fournies à titre indicatif et sans valeur contractuelle.",
                "openservices.enedis.fr",
            ),
        ],
    ),
}

# Prototype V0 : accueil, envoi des sites, résultats
TITRE_ACCUEIL = "Bienvenue dans Mutafriches !"
INTRO_ACCUEIL = "Pour nous aider à améliorer le service, dites-nous qui vous êtes."
CONSENTEMENT_ACCUEIL = "J'accepte d'être contacté par l'équipe Mutafriches (ADEME) à des fins d'amélioration du service"
TITRE_IMPORT = "Trouver le bon usage pour vos friches"
INTRO_IMPORT = (
    "Envoyez votre inventaire de sites au standard CNIG Friches : Mutafriches qualifie chaque site "
    "et calcule sa mutabilité pour sept usages."
)
AIDE_FICHIER = (
    "Fichier CSV ou GeoJSON au standard CNIG Friches (v2023-12). Colonnes attendues : site_id, "
    "site_nom, comm_insee, unite_fonciere_refcad (parcelles séparées par |) et geompoint."
)
AIDE_EXEMPLE_CNIG = (
    "Besoin du bon format ? Le fichier exemple contient trois sites fictifs à remplacer par les "
    "vôtres ; il n'a de valeur que comme modèle."
)
BOUTON_MODELE_CNIG = "Télécharger un fichier exemple"
AIDE_ERREUR_CNIG = "Les lignes en erreur sont écartées de l'envoi. Corrigez le fichier puis choisissez-le à nouveau. Standard : schema.data.gouv.fr (cnigfr/schema-friches)."
SOUS_TITRE_ANALYSE_REELLE = "Comptez deux à cinq secondes par site, davantage pour un site de nombreuses parcelles."
AIDE_ERREUR_API = (
    "L'extension appelle l'API Mutafriches avec une origine dédiée, à faire autoriser par l'équipe "
    "(contact@mutafriches.beta.gouv.fr). En attendant, le mode démonstration montre le parcours sur "
    "des données figées."
)
AIDE_AUCUN_SITE = (
    "Vérifiez les identifiants de parcelles de votre fichier (14 caractères, parcelles existantes), puis "
    "relancez l'envoi. Si l'erreur persiste pour des parcelles valides, écrivez à "
    "contact@mutafriches.beta.gouv.fr."
)
# Page « Mutafriches » des options de QGIS
AIDE_OPTION_ENVIRONNEMENT = (
    "Production : vos sites sont analysés par le service Mutafriches. Démonstration : aucun appel "
    "réseau, résultats figés d'un inventaire d'exemple."
)
AIDE_OPTION_INFORMATIONS = "Ces informations restent sur votre poste : elles ne sont pas transmises à Mutafriches."
AIDE_OPTION_FOND = (
    "À l'ouverture du panneau sur un projet sans couche, un fond de carte OpenStreetMap est ajouté. "
    "Décochez si votre structure n'autorise pas les fonds de carte externes."
)
AIDE_OPTION_DEV = "Donne accès à l'environnement de staging et aux réglages de l'API. Sans effet sur vos analyses."
AIDE_OPTION_INTERVALLE = (
    "L'API accepte 100 requêtes par minute et deux requêtes sont faites par site : ne pas descendre "
    "sous 1500 ms hors d'un serveur local."
)
MESSAGE_ANALYSE_LOT = (
    "Pour chaque site, nous recueillons des informations localisées depuis plus de dix bases de "
    "données nationales, puis calculons sa mutabilité pour sept usages."
)

# AnalyserPage et carte de sélection
TITRE_SELECTION = "Trouver le bon usage pour une friche"
INTRO_SELECTION = (
    "Pour démarrer l'analyse de l'usage le plus adapté à votre site en friche, sélectionner une parcelle sur la carte."
)
TUTORIEL = (
    "1. Dans le panneau Couches, sélectionnez une couche de parcelles.\n"
    "2. Cliquez sur une parcelle, puis sur une parcelle adjacente pour l'ajouter au site.\n"
    "3. Cliquez sur « Analyser ce site » et complétez les 3 étapes."
)
AIDE_ADJACENTE = "Cliquer sur une parcelle adjacente pour l'ajouter au site"

# EnrichmentLoadingCallout (messages repris sans leurs émojis)
TITRE_CHARGEMENT = "Qualification automatique de la parcelle en cours..."
SOUS_TITRE_CHARGEMENT = "Cela peut prendre quelques secondes."
MESSAGES_CHARGEMENT = (
    "Saviez-vous que 150 000 hectares de friches peuvent accueillir de nouveaux projets sans "
    "artificialiser les sols ? Découvrons ensemble à quels usages votre site est le plus adapté.",
    "Replanter 1 milliard d'arbres d'ici 2032 est une priorité du gouvernement. Découvrons "
    "ensemble si votre site est adapté à la renaturation.",
    "Multiplier par dix la production d'énergie photovoltaïque pour atteindre 42,8 TWh est une "
    "priorité du gouvernement. Découvrons ensemble si votre site est adapté au photovoltaïque au sol.",
    "Pour définir l'usage le plus adapté à la reconversion de votre site, nous recueillons un "
    "maximum d'informations localisées depuis plus de dix bases de données nationales.",
    "Construire des projets plus durables commence par une bonne connaissance du terrain. "
    "Découvrons ensemble quels sont les usages les plus adaptés sur votre site.",
)

# ResultatsPage
AIDE_ANALYSE = (
    "Ces résultats constituent une première orientation, basée sur les éléments que nous avons "
    "recueillis et que vous avez renseigné. Ils doivent être croisés avec votre connaissance du "
    "territoire et ne se substituent pas à des études de programmation."
)
AIDE_FIABILITE = (
    "L'indice de fiabilité reflète la complétude des informations concernant la friche. Il baisse "
    'si des données manquent ou si vous indiquez "Je ne sais pas".'
)
AIDE_USAGES = (
    "Pour les sites de plus d'un hectare, il vous est recommandé de privilégier un mixte d'usages "
    "dans votre programmation."
)
