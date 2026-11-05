"""Présentation des données du site, miroir des builders de l'application web (affichage seul).

- buildRecapitulatifSite, buildDetailUsage, getImpactCritere : packages/shared-types/src/recapitulatif
- transformEnrichmentToUiData : apps/ui/src/features/analyser/utils/enrichissment.mapper.ts
"""

from dataclasses import dataclass, field
from typing import Optional, Union

from .referentiel import (
    CRITERES,
    DONNEE_NON_ACCESSIBLE,
    LIBELLES_RECAP_ENRICHIS,
    LIBELLES_RECAP_SAISIE,
    MESSAGE_ZONE_EXCLUSION_ENR,
    NE_SAIT_PAS,
    SECTIONS,
    VALEUR_NON_DISPONIBLE,
    formater_booleen,
    formater_distance,
    formater_pourcentage,
    formater_surface,
    libelle,
)

Json = dict[str, object]

# Miroir de deriverRaccordementEau (shared-types) : du bâti de plus de 20 m² implique un raccordement
SEUIL_BATI_RACCORDEMENT_EAU_M2 = 20


def deriver_raccordement_eau(surface_bati: Optional[float]) -> str:
    if surface_bati is None:
        return NE_SAIT_PAS
    return "oui" if surface_bati > SEUIL_BATI_RACCORDEMENT_EAU_M2 else "non"


def _nombre(valeur: object) -> Optional[float]:
    return float(valeur) if isinstance(valeur, (int, float)) and not isinstance(valeur, bool) else None


def _booleen(valeur: object) -> Optional[bool]:
    return valeur if isinstance(valeur, bool) else None


def _saisie(cle: str, c: dict[str, str]) -> str:
    valeur = c.get(cle)
    if valeur == NE_SAIT_PAS:
        return "Ne sait pas"
    return libelle(LIBELLES_RECAP_SAISIE[cle], valeur)


def valeur_recapitulatif(cle: str, e: Json, c: dict[str, str]) -> str:
    """Valeur affichée d'un critère, comme les résolveurs de buildRecapitulatifSite."""
    if cle in LIBELLES_RECAP_SAISIE:
        return _saisie(cle, c)
    valeur = e.get(cle)
    if cle in ("surfaceSite", "surfaceBati"):
        return formater_surface(_nombre(valeur))
    if cle in ("distanceRaccordementElectrique", "distanceReseauChaleur", "distanceTransportCommun", "distanceAutoroute"):
        return formater_distance(_nombre(valeur))
    if cle == "tauxLogementsVacants":
        return formater_pourcentage(_nombre(valeur))
    if cle in ("siteEnCentreVille", "proximiteCommercesServices", "presenceRisquesTechnologiques", "siteEnQpv", "saturationReseauEnr"):
        return formater_booleen(_booleen(valeur))
    if cle in LIBELLES_RECAP_ENRICHIS:
        return libelle(LIBELLES_RECAP_ENRICHIS[cle], valeur)
    return VALEUR_NON_DISPONIBLE


@dataclass
class LigneRecap:
    cle: str
    libelle: str
    valeur: str
    saisie: str  # « Automatique » ou « Manuelle »
    source: Optional[str] = None
    mention: Optional[str] = None
    informatif: bool = False


@dataclass
class SectionRecap:
    titre: str
    lignes: list[LigneRecap] = field(default_factory=list)


def construire_recapitulatif(enrichissement: Json, complementaires: dict[str, str]) -> list[SectionRecap]:
    sections = {cle: SectionRecap(titre) for cle, titre in SECTIONS.items()}
    zaer = enrichissement.get("zaer")
    for critere in CRITERES:
        mention = None
        if critere.cle == "zoneAccelerationEnr" and isinstance(zaer, dict) and zaer.get("enZoneExclusion"):
            mention = MESSAGE_ZONE_EXCLUSION_ENR
        sections[critere.section].lignes.append(
            LigneRecap(
                critere.cle,
                critere.libelle,
                valeur_recapitulatif(critere.cle, enrichissement, complementaires),
                "Automatique" if critere.automatique else "Manuelle",
                critere.source,
                mention,
            )
        )
    # Donnée informative, hors algorithme (informations.metadata.ts)
    sections["site-bati"].lignes.append(
        LigneRecap(
            "ilotChaleurUrbain",
            "Site concerné par un îlot de chaleur",
            libelle(LIBELLES_RECAP_ENRICHIS["ilotChaleurUrbain"], enrichissement.get("ilotChaleurUrbain")),
            "Automatique",
            "ICU (CSTB)",
            informatif=True,
        )
    )
    return [s for s in sections.values() if s.lignes]


@dataclass(frozen=True)
class Impact:
    libelle: str
    niveau: str


IMPACT_BLOQUANT = Impact("Bloquant", "bloquant")


def impact_critere(score_brut: float) -> Impact:
    """Miroir de getImpactCritere : traduction du score brut en libellé."""
    if score_brut >= 2:
        return Impact("Très positif", "tres-positif")
    if score_brut >= 1:
        return Impact("Positif", "positif")
    if 0 < score_brut < 1:
        return Impact("Neutre", "neutre")
    if -1 <= score_brut < 0:
        return Impact("Négatif", "negatif")
    if score_brut < -1:
        return Impact("Très négatif", "tres-negatif")
    return Impact("Neutre", "neutre")


@dataclass
class LigneDetail:
    libelle: str
    valeur: str
    poids: float
    impact: Impact


def construire_detail_usage(
    resultat: Json, enrichissement: Json, complementaires: dict[str, str]
) -> list[tuple[str, list[LigneDetail]]]:
    """Miroir de buildDetailUsage : valeur du récapitulatif, poids et impact par critère."""
    calcul = resultat.get("detailsCalcul")
    details: dict[str, Json] = {}
    if isinstance(calcul, dict):
        for cle in ("detailsAvantages", "detailsContraintes", "detailsCriteresVides"):
            for detail in calcul.get(cle, []):  # type: ignore[union-attr]
                details[str(detail["critere"])] = detail
    excluants = resultat.get("criteresExcluants") or []
    sections: dict[str, list[LigneDetail]] = {cle: [] for cle in SECTIONS}
    for critere in CRITERES:
        detail = details.get(critere.cle)
        if detail is None:
            continue
        impact = (
            IMPACT_BLOQUANT
            if critere.cle in excluants  # type: ignore[operator]
            else impact_critere(float(detail["scoreBrut"]))  # type: ignore[arg-type]
        )
        sections[critere.section].append(
            LigneDetail(
                critere.libelle,
                valeur_recapitulatif(critere.cle, enrichissement, complementaires),
                float(detail["poids"]),  # type: ignore[arg-type]
                impact,
            )
        )
    return [(SECTIONS[cle], lignes) for cle, lignes in sections.items() if lignes]


# --- Valeurs affichées dans les étapes de qualification (transformEnrichmentToUiData) -------

Affichage = Union[str, list[str]]


def _distance_ou(valeur: object, message_aucun: str) -> str:
    if valeur is None:
        return message_aucun
    nombre = _nombre(valeur)
    return formater_distance(nombre) if nombre is not None else ""


def _oui_non(valeur: object) -> str:
    return ("Oui" if valeur else "Non") if isinstance(valeur, bool) else ""


def risques_naturels(e: Json) -> list[str]:
    badges = []
    rga = e.get("risqueRetraitGonflementArgile")
    if rga == "fort":
        badges.append("Retrait gonflement argiles : Fort")
    elif rga == "faible-ou-moyen":
        badges.append("Retrait gonflement argiles : Faible ou moyen")
    if e.get("risqueCavitesSouterraines") == "oui":
        badges.append("Cavités souterraines")
    if e.get("risqueInondation") == "oui":
        badges.append("Inondations")
    return badges or ["Aucun"]


def valeur_etape(cle: str, e: Json, c: dict[str, str]) -> Affichage:
    """Valeur d'une donnée enrichie dans les étapes ; chaîne vide = donnée non accessible."""
    if cle == "commune":
        return str(e.get("commune") or "")
    if cle == "parcelles":
        ids = e.get("identifiantsParcelles")
        return [str(i) for i in ids] if isinstance(ids, list) and len(ids) > 1 else str(e.get("identifiantParcelle") or "")
    if cle in ("surfaceSite", "surfaceBati"):
        nombre = _nombre(e.get(cle))
        return formater_surface(nombre) if nombre is not None else ""
    if cle == "distanceRaccordementElectrique":
        return _distance_ou(e.get(cle, ""), "Aucune infrastructure à moins de 5 km")
    if cle == "distanceReseauChaleur":
        return _distance_ou(e.get(cle, ""), "Aucun réseau de chaleur à proximité")
    if cle == "distanceTransportCommun":
        return _distance_ou(e.get(cle, ""), "Aucun arrêt à moins de 2 km")
    if cle == "distanceAutoroute":
        return _distance_ou(e.get(cle, ""), "Aucun accès autoroutier à moins de 50 km")
    if cle == "raccordementEau":
        return {"oui": "Oui", "non": "Non"}.get(deriver_raccordement_eau(_nombre(e.get("surfaceBati"))), "Non déterminé")
    if cle == "ilotChaleurUrbain":
        valeur = e.get(cle)
        return {"oui": "Oui (+ de 5,5 °C)", "non": "Non — aucun îlot de chaleur identifié", "non-couvert": "Commune non couverte"}.get(
            str(valeur), DONNEE_NON_ACCESSIBLE
        )
    if cle in ("siteEnCentreVille", "proximiteCommercesServices", "presenceRisquesTechnologiques", "siteEnQpv", "saturationReseauEnr"):
        return _oui_non(e.get(cle))
    if cle == "tauxLogementsVacants":
        nombre = _nombre(e.get(cle))
        return formater_pourcentage(nombre) if nombre is not None else ""
    if cle == "distanceIte":
        return {
            "moins-1km-bon-etat": "Moins d'1 km en bon état",
            "moins-1km-mauvais-etat": "Moins d'1 km en mauvais état",
            "plus-1km": "Plus d'1 km",
        }.get(str(e.get(cle)), "")
    if cle == "risquesNaturels":
        return risques_naturels(e)
    if cle == "zonageAbcLogement":
        valeur = e.get(cle, "")
        if valeur is None:
            return "Commune hors référentiel"
        return {"abis": "A BIS"}.get(str(valeur), str(valeur).upper())
    if cle == "zoneAccelerationEnr":
        zaer = e.get("zaer")
        if isinstance(zaer, dict) and zaer.get("enZoneExclusion"):
            return LIBELLES_RECAP_ENRICHIS["zoneAccelerationEnr"]["exclusion"]
        return {"non": "Non", "oui": "Oui", "oui-solaire-pv-ombriere": "Oui Solaire photovoltaïque"}.get(
            str(e.get(cle)), ""
        )
    if cle in LIBELLES_RECAP_ENRICHIS:
        valeur = e.get(cle)
        return LIBELLES_RECAP_ENRICHIS[cle].get(str(valeur), "") if valeur else ""
    return ""
