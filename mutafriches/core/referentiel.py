"""Champs, valeurs et libellés. Miroir de packages/shared-types et de apps/ui (Mutafriches)."""

from dataclasses import dataclass
from typing import Optional

NE_SAIT_PAS = "ne-sait-pas"
VALEUR_NON_DISPONIBLE = "Non disponible"
DONNEE_NON_ACCESSIBLE = "Donnée non accessible"
CHOIX_VIDE = "Sélectionner une option"
CHAMP_OBLIGATOIRE = "Ce champ est obligatoire"


@dataclass(frozen=True)
class ChampTerrain:
    cle: str
    libelle: str
    section: str
    # Options du formulaire web, « Ne sait pas » compris (sans le choix vide)
    options: tuple[tuple[str, str], ...]
    aide: str


# Miroir de apps/ui/src/features/qualification/config/fields et des infobulles des pages
CHAMPS_TERRAIN: tuple[ChampTerrain, ...] = (
    ChampTerrain(
        "typeProprietaire",
        "Type de propriétaire",
        "site-bati",
        (
            ("public", "Public"),
            ("prive", "Privé"),
            ("mixte", "Mixte public et privé"),
            ("copro-indivision", "Copropriété / Indivision"),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Renseignez à quel type de propriétaire le site appartient. Cette donnée permet "
        "d'apprécier la dureté foncière.",
    ),
    ChampTerrain(
        "valeurArchitecturaleHistorique",
        "Valeur patrimoniale des constructions",
        "site-bati",
        (
            ("pas-de-bati", "Pas de bâti"),
            ("sans-interet", "Bâti sans qualité patrimoniale particulière"),
            ("ordinaire", "Bâti courant, mais cohérent avec le site"),
            ("interet-remarquable", "Bâti à valeur patrimoniale remarquable"),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Donnez nous votre avis sur l'intérêt architectural et/ou patrimonial du bâti présent "
        "sur le site. Ce critère est subjectif et relatif à votre appréciation.",
    ),
    ChampTerrain(
        "etatBatiInfrastructure",
        "État du bâti",
        "site-bati",
        (
            ("pas-de-bati", "Pas de bâti"),
            ("degradation-inexistante", "Bâti intact"),
            ("degradation-faible", "Bâti faiblement dégradé"),
            ("degradation-moyenne", "Bâti moyennement dégradé"),
            ("degradation-tres-importante", "Bâti très dégradé"),
            ("degradation-heterogene", "Bâti dégradé de manière hétérogène"),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Renseignez l'état des constructions présentes sur le site. Le menu déroulant vous "
        "propose une graduation de l'état de dégradation.",
    ),
    ChampTerrain(
        "presencePollution",
        "Présence de pollution",
        "site-bati",
        (("oui", "Oui"), ("non", "Non"), (NE_SAIT_PAS, "Ne sait pas")),
        "Entrez l'information dont vous disposez sur la présence de pollution sur votre site "
        "(sol et bâti). Si la case 'Oui' est présélectionnée, c'est que nous avons retrouvé un "
        "risque de pollution à moins de 500 m dans une base de données nationales des sites et "
        "sols pollués.",
    ),
    ChampTerrain(
        "qualiteVoieDesserte",
        "Qualité de la voie de desserte",
        "environnement",
        (
            ("degradee", "Accessibilité dégradée (voie en mauvais état, gabarit restreint, etc.)"),
            (
                "peu-accessible",
                "Accessibilité limitée (connexion au réseau viaire limitée, gabarit excluant "
                "certains types de véhicules, etc.)",
            ),
            (
                "accessible",
                "Accessible (voie bien connectée, de bonne qualité et suffisamment dimensionnée)",
            ),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Indiquez la qualité de la desserte du site par les voies de circulation.",
    ),
    ChampTerrain(
        "qualitePaysage",
        "Intérêt du paysage environnant",
        "environnement",
        (
            ("sans-interet", "Paysage dégradé (zone d'activités, parkings, ensembles urbains, etc.)"),
            (
                "ordinaire",
                "Paysage courant (tissu périurbain banal, champs ouverts, lotissements, etc.)",
            ),
            (
                "interet-remarquable",
                "Paysage remarquable (centre historique, littoral et cours d'eau, coteau, "
                "panorama, forêt ancienne, etc.)",
            ),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Donnez-nous votre avis sur l'intérêt paysager de l'environnement du site.",
    ),
    ChampTerrain(
        "trameVerteEtBleue",
        "Trame verte et bleue",
        "environnement",
        (
            ("hors-trame", "Hors trame"),
            ("reservoir-biodiversite", "Réservoir de biodiversité"),
            ("corridor-a-preserver", "Corridor à préserver"),
            ("corridor-a-restaurer", "Corridor à restaurer"),
            (NE_SAIT_PAS, "Ne sait pas"),
        ),
        "Indiquez si le site est situé dans un corridor écologique ou un réservoir de "
        "biodiversité.",
    ),
    ChampTerrain(
        "presenceEspecesProtegees",
        "Présence d'une espèce protégée",
        "environnement",
        (("oui", "Oui"), ("non", "Non"), (NE_SAIT_PAS, "Ne sait pas")),
        "Renseignez si votre site est concerné ou non par la présence d'une espèce protégée, "
        "vous obtiendrez cette information en réalisation des études faune/flore sur votre site.",
    ),
    ChampTerrain(
        "presenceZoneHumide",
        "Présence d'une zone humide",
        "environnement",
        (("oui", "Oui"), ("non", "Non"), (NE_SAIT_PAS, "Ne sait pas")),
        "Renseignez si votre site est concerné ou non par la présence d'une zone humide.",
    ),
)

CHAMPS_PAR_CLE: dict[str, ChampTerrain] = {c.cle: c for c in CHAMPS_TERRAIN}
CLES_TERRAIN: tuple[str, ...] = tuple(c.cle for c in CHAMPS_TERRAIN)

# Pollution « Oui » : type à préciser (apps/ui/.../PollutionField.tsx)
TYPES_POLLUTION: tuple[tuple[str, str], ...] = (
    ("oui-amiante", "Présence d'amiante dans le bâti"),
    ("oui-composes-volatils", "Composés volatils"),
    ("oui-autres-composes", "Autres composés"),
    ("deja-geree", "Pollution déjà gérée"),
)
PAS_DE_BATI = "pas-de-bati"

SECTIONS: dict[str, str] = {
    "site-bati": "Le site et son bâti",
    "environnement": "L'environnement du site",
    "risques-zonages": "Les risques et zonages du site",
}

# Miroir de USAGE_CONFIG (apps/ui/src/features/resultats/utils/usagesLabels.utils.ts)
USAGES: dict[str, str] = {
    "residentiel": "Habitat & commerce de proximité",
    "equipements": "Équipement public",
    "culture": "Équipement culturel & touristique",
    "tertiaire": "Bureaux",
    "industrie": "Industrie",
    "renaturation": "Espace renaturé",
    "photovoltaique": "Centrale photovoltaïque au sol",
}
IMAGES_USAGES: dict[str, str] = {
    "residentiel": "habitats.png",
    "equipements": "equipement-public.png",
    "culture": "equipement-culturel.png",
    "tertiaire": "bureaux.png",
    "industrie": "industrie.png",
    "renaturation": "espace-renature.png",
    "photovoltaique": "centrale-photovoltaique.png",
}
MESSAGE_USAGE_EXCLU = "Certaines caractéristiques du site peuvent bloquer sa mutabilité vers cet usage"


@dataclass(frozen=True)
class Badge:
    libelle: str
    texte: str
    fond: str


BADGE_EXCLU = Badge("EXCLU", "#755348", "#FEE9E5")


def badge_potentiel(indice: float, exclu: bool = False) -> Badge:
    """Miroir de getBadgeConfig : seuils d'affichage de l'interface web."""
    if exclu:
        return BADGE_EXCLU
    if indice >= 70:
        return Badge("EXCELLENT", "#18753C", "#B8FEC9")
    if indice >= 60:
        return Badge("TRÈS BON", "#208D49", "#C9FCAC")
    if indice >= 50:
        return Badge("BON", "#716043", "#FEECC2")
    if indice >= 40:
        return Badge("MOYEN", "#716043", "#FEDED9")
    return Badge("FAIBLE", "#8D533E", "#FFBDBE")


@dataclass(frozen=True)
class Critere:
    cle: str
    libelle: str
    section: str
    automatique: bool
    source: Optional[str] = None


# Miroir de CRITERES_METADATA (ordre, libellé, saisie) et SOURCE_LABELS (packages/shared-types)
CRITERES: tuple[Critere, ...] = (
    Critere("surfaceSite", "Surface du site", "site-bati", True, "Cadastre"),
    Critere("surfaceBati", "Surface bâtie", "site-bati", True, "BDNB"),
    Critere("typeProprietaire", "Type de propriétaire", "site-bati", False),
    Critere("distanceRaccordementElectrique", "Distance au raccordement électrique", "site-bati", True, "Enedis"),
    Critere("raccordementEau", "Raccordement aux réseaux d'eau", "site-bati", False),
    Critere("distanceReseauChaleur", "Distance au réseau de chaleur", "site-bati", True, "France Chaleur Urbaine"),
    Critere("valeurArchitecturaleHistorique", "Valeur patrimoniale des constructions", "site-bati", False),
    Critere("etatBatiInfrastructure", "État du bâti", "site-bati", False),
    Critere("presencePollution", "Présence de pollution", "site-bati", False),
    Critere("siteEnCentreVille", "Site en centre-ville", "environnement", True, "API Service Public"),
    Critere("proximiteCommercesServices", "Proximité commerces et services", "environnement", True, "BPE (INSEE)"),
    Critere("tauxLogementsVacants", "Taux de logements vacants", "environnement", True, "LOVAC"),
    Critere("distanceTransportCommun", "Distance aux transports en commun", "environnement", True, "Transport Data Gouv"),
    Critere("distanceAutoroute", "Distance par la route à un accès autoroutier", "environnement", True, "IGN"),
    Critere(
        "distanceIte",
        "Distance à une installation terminale embranchée fret",
        "environnement",
        True,
        "ITE fret (Cerema)",
    ),
    Critere("qualiteVoieDesserte", "Qualité de la voie de desserte", "environnement", False),
    Critere("qualitePaysage", "Intérêt du paysage environnant", "environnement", False),
    Critere("trameVerteEtBleue", "Trame verte et bleue", "environnement", False),
    Critere("presenceEspecesProtegees", "Présence d'espèces protégées", "environnement", False),
    Critere("presenceZoneHumide", "Présence d'une zone humide", "environnement", False),
    Critere("presenceRisquesTechnologiques", "Présence de risques technologiques", "risques-zonages", True, "GéoRisques"),
    Critere("risqueRetraitGonflementArgile", "Retrait-gonflement des argiles", "risques-zonages", True, "GéoRisques"),
    Critere("risqueCavitesSouterraines", "Cavités souterraines", "risques-zonages", True, "GéoRisques"),
    Critere("risqueInondation", "Risque d'inondation", "risques-zonages", True, "GéoRisques"),
    Critere("zonageEnvironnemental", "Zonage environnemental", "risques-zonages", True, "API Carto Nature"),
    Critere("zonageReglementaire", "Zonage réglementaire", "risques-zonages", True, "API Carto GPU"),
    Critere("zonagePatrimonial", "Zonage patrimonial", "risques-zonages", True, "API Carto GPU"),
    Critere("zoneAccelerationEnr", "Zone d'accélération des EnR", "risques-zonages", True, "ZAER-ENR"),
    Critere("zonageAbcLogement", "Zonage ABC (logement)", "risques-zonages", True, "Zonage ABC"),
    Critere(
        "siteEnQpv",
        "Quartier prioritaire de la politique de la ville",
        "risques-zonages",
        True,
        "QPV-ANCT",
    ),
    Critere(
        "saturationReseauEnr",
        "Saturation du réseau électrique pour les projets EnR",
        "risques-zonages",
        True,
        "Enedis-Zones-Contrainte-EnR",
    ),
)
CRITERES_PAR_CLE: dict[str, Critere] = {c.cle: c for c in CRITERES}

# Miroir de valeurs.labels.ts : libellés courts du récapitulatif (réponses saisies)
LIBELLES_RECAP_SAISIE: dict[str, dict[str, str]] = {
    "typeProprietaire": {
        "public": "Public",
        "prive": "Privé",
        "mixte": "Mixte public et privé",
        "copro-indivision": "Copropriété / Indivision",
    },
    "raccordementEau": {"oui": "Oui", "non": "Non"},
    "etatBatiInfrastructure": {
        "degradation-inexistante": "Bâti intact",
        "degradation-faible": "Bâti faiblement dégradé",
        "degradation-moyenne": "Bâti moyennement dégradé",
        "degradation-heterogene": "Bâti dégradé de manière hétérogène",
        "degradation-tres-importante": "Bâti très dégradé",
        "pas-de-bati": "Pas de bâti",
    },
    "presencePollution": {
        "non": "Non",
        "deja-geree": "Déjà gérée",
        "oui-composes-volatils": "Oui - composés volatils",
        "oui-amiante": "Oui - amiante",
        "oui-autres-composes": "Oui - autres composés",
    },
    "valeurArchitecturaleHistorique": {
        "sans-interet": "Bâti sans qualité patrimoniale particulière",
        "ordinaire": "Bâti courant, mais cohérent avec le site",
        "interet-remarquable": "Bâti à valeur patrimoniale remarquable",
        "pas-de-bati": "Pas de bâti",
    },
    "qualitePaysage": {
        "sans-interet": "Paysage dégradé ou sans qualité notable",
        "ordinaire": "Paysage courant",
        "interet-remarquable": "Paysage remarquable",
    },
    "qualiteVoieDesserte": {
        "accessible": "Accessible",
        "peu-accessible": "Accessibilité limitée",
        "degradee": "Accessibilité dégradée",
    },
    "trameVerteEtBleue": {
        "hors-trame": "Hors trame",
        "reservoir-biodiversite": "Réservoir de biodiversité",
        "corridor-a-preserver": "Corridor à préserver",
        "corridor-a-restaurer": "Corridor à restaurer",
    },
    "presenceEspecesProtegees": {"oui": "Oui", "non": "Non"},
    "presenceZoneHumide": {"oui": "Oui", "non": "Non"},
}

# Miroir de valeurs.labels.ts : critères enrichis
LIBELLES_RECAP_ENRICHIS: dict[str, dict[str, str]] = {
    "risqueRetraitGonflementArgile": {"aucun": "Aucun", "faible-ou-moyen": "Faible ou moyen", "fort": "Fort"},
    "risqueCavitesSouterraines": {"non": "Non", "oui": "Oui"},
    "risqueInondation": {"non": "Non", "oui": "Oui"},
    "zonageEnvironnemental": {
        "hors-zone": "Hors zone",
        "natura-2000": "Natura 2000",
        "znieff-type-1-2": "ZNIEFF type 1 / 2",
        "parc-naturel-regional": "Parc naturel régional",
        "parc-naturel-national": "Parc naturel national",
        "reserve-naturelle": "Réserve naturelle",
        "proximite-zone": "À proximité d'une zone protégée",
    },
    "zonageReglementaire": {
        "zone-urbaine-u": "Zone urbaine (U)",
        "zone-urbaine-u-habitat": "Zone urbaine - habitat",
        "zone-urbaine-u-equipement": "Zone urbaine - équipement",
        "zone-urbaine-u-activite": "Zone urbaine - activité",
        "zone-a-urbaniser-au": "Zone à urbaniser (AU)",
        "zone-vocation-activites": "Zone à vocation d'activités",
        "secteur-ouvert-a-la-construction": "Secteur ouvert à la construction",
        "secteur-non-ouvert-a-la-construction": "Secteur non ouvert à la construction",
        "secteur-reglement-urbanisme": "Secteur avec règlement d'urbanisme",
        "zone-agricole-a": "Zone agricole (A)",
        "zone-naturelle-n": "Zone naturelle (N)",
        NE_SAIT_PAS: "Ne sait pas",
    },
    "zonagePatrimonial": {
        "non-concerne": "Non concerné",
        "monument-historique": "Monument historique",
        "site-inscrit-classe": "Site inscrit / classé",
        "perimetre-abf": "Périmètre ABF",
        "zppaup": "ZPPAUP",
        "avap": "AVAP",
        "spr": "Site patrimonial remarquable (SPR)",
    },
    "zonageAbcLogement": {"abis": "Zone A bis", "a": "Zone A", "b1": "Zone B1", "b2": "Zone B2", "c": "Zone C"},
    "zoneAccelerationEnr": {
        "non": "Non",
        "oui": "Oui",
        "oui-solaire-pv-ombriere": "Oui - PV ombrière",
        "exclusion": "Exclu des zones d'accélération ENR",
    },
    "distanceIte": {
        "moins-1km-bon-etat": "Moins d'1 km, en bon état",
        "moins-1km-mauvais-etat": "Moins d'1 km, en mauvais état",
        "plus-1km": "Plus d'1 km",
    },
    "ilotChaleurUrbain": {
        "oui": "Oui (+ de 5,5 °C)",
        "non": "Non — aucun îlot de chaleur identifié",
        "non-couvert": "Commune non couverte par la cartographie",
    },
}
MESSAGE_ZONE_EXCLUSION_ENR = "Pas de projet possible hors photovoltaïque en toiture."


# --- Formats, miroir de valeurs.labels.ts (locale fr-FR) -----------------------------------

def _nombre(valeur: float, decimales: int = 0) -> str:
    texte = f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")
    if decimales and "," in texte:
        texte = texte.rstrip("0").rstrip(",")
    return texte


def formater_surface(m2: Optional[float]) -> str:
    return VALEUR_NON_DISPONIBLE if m2 is None else f"{_nombre(round(m2))} m²"


def formater_hectares(m2: float) -> str:
    return f"{_nombre(m2 / 10000, 2)} ha"


def formater_distance(metres: Optional[float]) -> str:
    if metres is None:
        return VALEUR_NON_DISPONIBLE
    if metres >= 1000:
        return f"{_nombre(metres / 1000, 1)} km"
    return f"{_nombre(round(metres))} m"


def formater_pourcentage(valeur: Optional[float]) -> str:
    return VALEUR_NON_DISPONIBLE if valeur is None else f"{_nombre(valeur, 2)} %"


def formater_booleen(valeur: Optional[bool]) -> str:
    if valeur is None:
        return VALEUR_NON_DISPONIBLE
    return "Oui" if valeur else "Non"


def formater_note(note: float) -> str:
    return _nombre(note, 1)


def libelle(table: dict[str, str], valeur: object) -> str:
    if valeur is None or valeur == "":
        return VALEUR_NON_DISPONIBLE
    return table.get(str(valeur), VALEUR_NON_DISPONIBLE)
