"""Jeux d'essai de Montereau-Fault-Yonne : inventaires CNIG et table attributaire figée.

Hors du ZIP de l'extension : ils ne servent qu'aux tests, au serveur factice et aux captures.
`outils/figer_attributaire.py` les régénère, ne pas les éditer à la main.
"""

import json
from pathlib import Path

from mutafriches.core.attributaire import Json, SiteAttributaire
from mutafriches.core.referentiel import USAGES

DOSSIER = Path(__file__).resolve().parent / "donnees"
FICHIER_ATTRIBUTAIRE = DOSSIER / "attributaire-77305.geojson"
FICHIER_CNIG_EXEMPLE = DOSSIER / "friches-cnig-montereau.csv"
FICHIER_CNIG_ERREURS = DOSSIER / "friches-cnig-erreurs.csv"


def charger_table(fichier: Path = FICHIER_ATTRIBUTAIRE) -> tuple[list[SiteAttributaire], Json]:
    """Sites de la table figée (GET /api/attributaire/sites), sans passer par l'API."""
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
    meta: Json = {"versionAlgorithme": sites[0].proprietes.get("version_algorithme", "") if sites else ""}
    return sites, meta
