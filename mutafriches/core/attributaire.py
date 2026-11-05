"""Table attributaire figée (GET /api/attributaire/sites) et synthèse territoriale du prototype."""

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .referentiel import CHAMPS_PAR_CLE, USAGES, badge_potentiel

Json = dict[str, object]

DOSSIER_MONTEREAU = Path(__file__).resolve().parent.parent / "demo" / "montereau"
FICHIER_ATTRIBUTAIRE = DOSSIER_MONTEREAU / "attributaire-77305.geojson"
FICHIER_CNIG_EXEMPLE = DOSSIER_MONTEREAU / "friches-cnig-montereau.csv"
FICHIER_CNIG_ERREURS = DOSSIER_MONTEREAU / "friches-cnig-erreurs.csv"
FICHIER_MODELE_CNIG = DOSSIER_MONTEREAU / "modele-cnig.csv"

# Ordre des colonnes d'usage : usages les plus souvent prioritaires en premier. Valeur provisoire
# à caler sur Metabase (répartition nationale des usages prioritaires) ; ici l'ordre observé sur
# la table figée.
ORDRE_USAGES: tuple[str, ...] = (
    "renaturation",
    "tertiaire",
    "industrie",
    "residentiel",
    "equipements",
    "culture",
    "photovoltaique",
)

# Niveaux de fiabilité, dans l'ordre d'affichage (miroir de NIVEAUX_FIABILITE, shared-types)
NIVEAUX_FIABILITE: tuple[str, ...] = ("Très fiable", "Fiable", "Moyennement fiable", "Peu fiable", "Très peu fiable")

# Grille de lecture propre au prototype : écart entre le meilleur et le moins bon usage d'un site
PROFILS_ECART: tuple[tuple[float, str, str], ...] = (
    (10, "Profil plat", "Rien ne se détache"),
    (15, "Profil peu contrasté", "Un usage se dessine à peine"),
    (20, "Contraste modéré", "Un usage se détache"),
    (30, "Contraste net", "Un ou deux usages dominent"),
    (float("inf"), "Fort contraste", "Vocation marquée"),
)

# Critères automatiques retenus pour la table de qualification, dans l'ordre d'affichage
CRITERES_QUALIFICATION_AUTO: tuple[tuple[str, str], ...] = (
    ("surfaceSite", "surface_site_m2"),
    ("surfaceBati", "surface_batie_m2"),
    ("zonageReglementaire", "zonage_reglementaire"),
    ("siteEnCentreVille", "centre_ville"),
    ("proximiteCommercesServices", "commerces_services"),
    ("distanceTransportCommun", "dist_transports_m"),
    ("distanceRaccordementElectrique", "dist_electricite_m"),
    ("raccordementEau", "raccordement_eau"),
    ("presenceRisquesTechnologiques", "risques_technologiques"),
    ("risqueInondation", "risque_inondation"),
    ("zonageEnvironnemental", "zonage_environnemental"),
    ("zonagePatrimonial", "zonage_patrimonial"),
)
# Critères saisis (déclaratifs), avec leur nom de colonne
CRITERES_QUALIFICATION_SAISIS: tuple[tuple[str, str], ...] = (
    ("typeProprietaire", "proprietaire"),
    ("etatBatiInfrastructure", "etat_bati"),
    ("presencePollution", "pollution"),
    ("valeurArchitecturaleHistorique", "valeur_patrimoniale"),
    ("qualitePaysage", "qualite_paysage"),
    ("qualiteVoieDesserte", "voie_desserte"),
    ("trameVerteEtBleue", "trame_verte_bleue"),
    ("presenceEspecesProtegees", "especes_protegees"),
    ("presenceZoneHumide", "zone_humide"),
)


@dataclass
class SiteAttributaire:
    cle: str
    nom: str
    parcelles: list[str]
    commune: str
    code_insee: str
    indices: dict[str, float]
    usage_prioritaire: Optional[str]
    usages_exclus: list[str]
    fiabilite: float
    fiabilite_niveau: str
    saisie_declarative: bool
    proprietes: Json
    geometrie: Optional[Json]
    # Renseigné quand le site vient du fichier CNIG envoyé par l'utilisateur
    site_id: str = ""

    @property
    def indice_max(self) -> float:
        return self.indices.get(self.usage_prioritaire or "", 0.0) if self.usage_prioritaire else 0.0

    @property
    def ecart(self) -> float:
        valeurs = [v for v in self.indices.values() if v is not None]
        return max(valeurs) - min(valeurs) if valeurs else 0.0

    @property
    def profil(self) -> str:
        return profil_ecart(self.ecart)[0]

    @property
    def niveau_compatibilite(self) -> str:
        return badge_potentiel(self.indice_max).libelle.capitalize()


@dataclass
class Synthese:
    commune: str
    code_insee: str
    nombre_sites: int
    # Nombre de sites par usage prioritaire, dans l'ordre d'affichage (usages absents à 0)
    par_usage: dict[str, int]
    par_fiabilite: dict[str, int]
    par_profil: dict[str, int]
    par_compatibilite: dict[str, int]
    fiabilite_moyenne: float
    indice_moyen_par_usage: dict[str, float]
    sites_forte_compatibilite: list[SiteAttributaire] = field(default_factory=list)
    sites_a_qualifier: list[SiteAttributaire] = field(default_factory=list)
    version_algorithme: str = ""
    date_table: str = ""


def profil_ecart(ecart: float) -> tuple[str, str]:
    for seuil, libelle, lecture in PROFILS_ECART:
        if ecart < seuil:
            return libelle, lecture
    return PROFILS_ECART[-1][1], PROFILS_ECART[-1][2]


def libelle_usage(usage: Optional[str]) -> str:
    return USAGES.get(usage or "", usage or "")


def libelle_saisie(cle: str, valeur: object) -> str:
    champ = CHAMPS_PAR_CLE.get(cle)
    if champ is None or valeur is None:
        return "" if valeur is None else str(valeur)
    return dict(champ.options).get(str(valeur), str(valeur))


def charger_table(fichier: Path = FICHIER_ATTRIBUTAIRE) -> tuple[list[SiteAttributaire], Json]:
    collection = json.loads(fichier.read_text(encoding="utf-8"))
    sites = []
    for entite in collection["features"]:
        p = entite["properties"]
        indices = {u: float(p[f"indice_{u}"]) for u in USAGES if p.get(f"indice_{u}") is not None}
        sites.append(
            SiteAttributaire(
                cle=str(p["cle_site"]),
                nom=str(p.get("nom") or f"Site {p.get('parcelle_predominante') or p['cle_site']}"),
                parcelles=str(p["parcelles"]).split("|"),
                commune=str(p.get("commune") or ""),
                code_insee=str(p["code_insee"]),
                indices=indices,
                usage_prioritaire=p.get("usage_prioritaire"),
                usages_exclus=[u for u in str(p.get("usages_exclus") or "").split("|") if u],
                fiabilite=float(p["fiabilite"]),
                fiabilite_niveau=str(p["fiabilite_niveau"]),
                saisie_declarative=bool(p.get("saisie_declarative")),
                proprietes=p,
                geometrie=entite.get("geometry"),
            )
        )
    meta: Json = {
        "avertissement": collection.get("avertissement", ""),
        "figeLe": collection.get("figeLe", ""),
        "versionAlgorithme": sites[0].proprietes.get("version_algorithme", "") if sites else "",
    }
    return sites, meta


def apparier(sites: list[SiteAttributaire], parcelles_par_site_id: dict[str, list[str]]) -> list[SiteAttributaire]:
    """Sites de la table dont les parcelles sont exactement celles d'un site du fichier envoyé."""
    par_cle = {",".join(sorted(parcelles)): site_id for site_id, parcelles in parcelles_par_site_id.items()}
    apparies = []
    for site in sites:
        site_id = par_cle.get(",".join(sorted(site.parcelles)))
        if site_id is not None:
            site.site_id = site_id
            apparies.append(site)
    return apparies


def synthese(sites: list[SiteAttributaire], meta: Json) -> Synthese:
    usages = Counter(s.usage_prioritaire for s in sites if s.usage_prioritaire)
    fiabilites = Counter(s.fiabilite_niveau for s in sites)
    profils = Counter(s.profil for s in sites)
    compatibilites = Counter(s.niveau_compatibilite for s in sites)
    moyens = {
        u: round(sum(s.indices[u] for s in sites if u in s.indices) / max(1, sum(1 for s in sites if u in s.indices)), 1)
        for u in ORDRE_USAGES
    }
    forte = sorted((s for s in sites if s.indice_max >= 70), key=lambda s: -s.indice_max)
    a_qualifier = sorted((s for s in sites if not s.saisie_declarative), key=lambda s: s.fiabilite)
    return Synthese(
        commune=sites[0].commune if sites else "",
        code_insee=sites[0].code_insee if sites else "",
        nombre_sites=len(sites),
        par_usage={u: usages.get(u, 0) for u in ORDRE_USAGES},
        par_fiabilite={n: fiabilites.get(n, 0) for n in NIVEAUX_FIABILITE},
        par_profil={libelle: profils.get(libelle, 0) for _, libelle, _ in PROFILS_ECART},
        par_compatibilite={n: compatibilites.get(n, 0) for n in ("Excellent", "Très bon", "Bon", "Moyen", "Faible")},
        fiabilite_moyenne=round(sum(s.fiabilite for s in sites) / len(sites), 1) if sites else 0.0,
        indice_moyen_par_usage=moyens,
        sites_forte_compatibilite=forte,
        sites_a_qualifier=a_qualifier,
        version_algorithme=str(meta.get("versionAlgorithme", "")),
        date_table=str(meta.get("figeLe", "")),
    )
