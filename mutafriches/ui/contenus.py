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
INTRO_ACCUEIL = (
    "Pour analyser vos sites, déclarez votre structure : c'est son domaine qui identifie vos appels "
    "à l'API Mutafriches. La déclaration est faite une fois, sans attendre l'équipe."
)
# Libellés, aides et mention : miroir du formulaire de déclaration web (FormulaireDeclaration)
LIBELLE_STRUCTURE = "Nom de votre structure"
LIBELLE_TYPE_STRUCTURE = "Type de structure"
LIBELLE_DOMAINE = "Domaine de votre structure"
AIDE_DOMAINE = "Par exemple ma-collectivite.fr"
LIBELLE_PRENOM = "Votre prénom"
LIBELLE_NOM = "Votre nom"
LIBELLE_MAIL = "Adresse e-mail de contact"
AIDE_MAIL = "Pour le suivi de votre accès et les échanges sur le fonctionnement du service"
# Miroir de LIBELLE_CONSENTEMENT_CONTACT (formulaire de déclaration web, PR 285 de Mutafriches)
LIBELLE_ACCEPTE_CONTACT = (
    "J'accepte d'être contacté·e pour partager mes retours d'expérience et être informé·e des "
    "évolutions du service Mutafriches (ADEME)"
)
AIDE_ACCEPTE_CONTACT = "Facultatif, sans effet sur votre accès au service"
CHOIX_VIDE = "Sélectionner une option"
URL_CONFIDENTIALITE = "https://mutafriches.beta.gouv.fr/politique-de-confidentialite"
# {lien} : lien vers la politique de confidentialité
MENTION_ACCUEIL = (
    "Vos prénom, nom et adresse e-mail sont conservés dans notre outil d'e-mailing, pas dans la "
    "base de Mutafriches. {lien}"
)
LIBELLE_CONFIDENTIALITE = "Politique de confidentialité"
ENVOI_DECLARATION = "Envoi en cours…"
ACCUEIL_A_COMPLETER = "Complétez vos informations : elles sont désormais nécessaires pour analyser vos sites."
DECLARATION_REFUSEE = "Votre structure n'a pas pu être déclarée à l'API Mutafriches."
TITRE_IMPORT = "Trouver le bon usage pour vos friches"
# Tableau de bord territorial
TITRE_REPARTITION = "Répartition des usages les plus compatibles"
AIDE_REPARTITION = "Nombre de sites dont c'est l'usage le plus compatible."
TITRE_FORTE_COMPATIBILITE = "Sites à forte compatibilité"
AIDE_FORTE_COMPATIBILITE = (
    "Classement des sites dont l'usage le plus compatible dépasse 70 %. Cliquer sur un site pour le "
    "sélectionner et le cadrer sur la carte."
)
TITRE_PROFILS = "Profils des sites"
AIDE_PROFILS = (
    "Les sites dont la répartition des usages est contrastée, avec de forts écarts, sont considérés "
    "comme mieux qualifiés que ceux au profil plat."
)
LIEN_AMELIORER_FIABILITE = "Améliorer la fiabilité"
LIEN_COMPRENDRE_RESULTATS = "Comprendre les résultats"
AIDE_COMPRENDRE_RESULTATS = (
    "Ouvre la page « Comprendre les analyses » du site Mutafriches : définition de chaque critère "
    "et sources des données utilisées."
)
AIDE_AMELIORER_FIABILITE = (
    "Critères de terrain en rouge : inconnus. Renseignez-les dans votre fichier CNIG, puis relancez l'analyse."
)
RAPPEL_DEMONSTRATION = (
    "Mode démonstration : résultats figés d'un inventaire d'exemple. Pour analyser vos sites, "
    "choisissez « Production » dans Préférences › Options › Mutafriches."
)
URL_STANDARD_CNIG = "https://schema.data.gouv.fr/cnigfr/schema-friches/"
# {standard} : lien vers le standard, posé sur les mots « standard CNIG »
INTRO_IMPORT = (
    "Chargez votre inventaire de sites au {standard} Friches. Mutafriches qualifiera chacun de vos "
    "sites et calculera leur mutabilité sur 7 usages de reconversion."
)
LIBELLE_STANDARD_CNIG = "standard CNIG"
AIDE_FICHIER = (
    "Fichier CSV ou GeoJSON au standard CNIG Friches (v2023-12). Colonnes attendues : site_id, "
    "site_nom, comm_insee, unite_fonciere_refcad (parcelles de 14 caractères, séparées par |) et "
    "geompoint, par exemple POINT(2.9555 48.3895). Le modèle vide porte les 51 colonnes du standard, "
    "à remplir avec vos sites."
)
LIEN_MODELE_CNIG = "Télécharger un modèle de fichier vide"
AIDE_ERREUR_CNIG = "Les sites KO sont écartés de l'analyse. Corrigez le fichier puis chargez-le de nouveau. Standard : schema.data.gouv.fr (cnigfr/schema-friches)."
SOUS_TITRE_ANALYSE = "Cela peut prendre de quelques secondes à quelques minutes."
AIDE_ERREUR_API = (
    "L'extension appelle l'API Mutafriches avec le domaine déclaré de votre structure. En cas de "
    "blocage, écrivez à contact@mutafriches.beta.gouv.fr. En attendant, le mode démonstration "
    "(Préférences › Options › Mutafriches) montre le parcours sur des données figées."
)
AIDE_AUCUN_SITE = (
    "Vérifiez les identifiants de parcelles de votre fichier (14 caractères, parcelles existantes), puis "
    "relancez l'envoi. Si l'erreur persiste pour des parcelles valides, écrivez à "
    "contact@mutafriches.beta.gouv.fr."
)
# Page « Mutafriches » des options de QGIS
AIDE_OPTION_ENVIRONNEMENT = (
    "Production : vos sites sont analysés par le service Mutafriches. Staging : environnement de "
    "test de l'équipe, signalé par un bandeau. Démonstration : aucun appel réseau, résultats figés "
    "d'un inventaire d'exemple."
)
AIDE_OPTION_INFORMATIONS = (
    "Déclaration de votre structure, envoyée à Mutafriches à la prochaine analyse si elle change. Vos "
    "prénom, nom et adresse e-mail sont conservés dans l'outil d'e-mailing de Mutafriches, pas dans sa base."
)
AIDE_OPTION_FOND = (
    "À l'ouverture du panneau sur un projet sans couche, un fond de carte OpenStreetMap est ajouté. "
    "Décochez si votre structure n'autorise pas les fonds de carte externes."
)
AIDE_OPTION_DEV = "Donne accès aux réglages de l'API : adresse libre, origine envoyée, délai entre deux sites."
AIDE_OPTION_INTERVALLE = (
    "L'API accepte 100 requêtes par minute et deux requêtes sont faites par site : ne pas descendre "
    "sous 1500 ms hors d'un serveur local."
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
