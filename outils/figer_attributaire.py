"""Gèle la table attributaire publique de Montereau-Fault-Yonne pour le prototype.

Sorties (mutafriches/demo/montereau/) :
- attributaire-77305.geojson : réponse GeoJSON de GET /api/attributaire/sites, telle quelle
- friches-cnig-montereau.csv : les mêmes sites au standard CNIG Friches (51 colonnes), fichier
  d'entrée d'exemple du prototype
- friches-cnig-erreurs.csv : fichier avec plusieurs lignes en erreur, pour l'écran de contrôle
- modele-cnig.csv : modèle à remplir, valeurs manifestement fictives (pas une vraie commune)

Usage : python3 outils/figer_attributaire.py (réseau requis)
"""

import csv
import io
import json
import urllib.request
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "mutafriches" / "demo" / "montereau"
API = "https://mutafriches.beta.gouv.fr/api/attributaire/sites?codeInsee=77305&format=geojson"

# Colonnes du TableSchema cnigfr/schema-friches v1.0.6, dans l'ordre (miroir de shared-types)
COLONNES_CNIG = [
    "site_id",
    "site_nom",
    "site_type",
    "site_adresse",
    "site_identif_date",
    "site_actu_date",
    "site_url",
    "site_ademe_url",
    "site_securite",
    "site_occupation",
    "site_statut",
    "site_projet_url",
    "site_reconv_annee",
    "site_reconv_type",
    "activite_libelle",
    "activite_code",
    "activite_fin_annee",
    "comm_nom",
    "comm_insee",
    "bati_type",
    "bati_nombre",
    "bati_surface",
    "bati_pollution",
    "bati_vacance",
    "bati_patrimoine",
    "bati_etat",
    "local_ancien_annee",
    "local_recent_annee",
    "proprio_type",
    "proprio_personne",
    "proprio_nom",
    "sol_pollution_annee",
    "sol_pollution_existe",
    "sol_pollution_origine",
    "sol_pollution_commentaire",
    "sol_depollution_fiche",
    "unite_fonciere_surface",
    "unite_fonciere_refcad",
    "urba_zone_type",
    "urba_zone_lib",
    "urba_zone_formdomi",
    "urba_zaer",
    "urba_doc_type",
    "desserte_distance",
    "desserte_commentaire",
    "source_nom",
    "source_url",
    "source_producteur",
    "source_contact",
    "geompoint",
    "geomsurf",
]
INCONNU = "inconnu"
LISTES = {
    "site_type",
    "site_securite",
    "site_occupation",
    "site_statut",
    "bati_type",
    "bati_pollution",
    "bati_vacance",
    "bati_patrimoine",
    "bati_etat",
    "proprio_type",
    "proprio_personne",
    "sol_pollution_existe",
    "sol_pollution_origine",
    "urba_zone_type",
    "urba_zaer",
    "urba_doc_type",
}


def wkt(geometrie: dict) -> str:
    def anneau(a: list) -> str:
        return "(" + ",".join(f"{x} {y}" for x, y in a) + ")"

    if geometrie["type"] == "Polygon":
        return "POLYGON(" + ",".join(anneau(a) for a in geometrie["coordinates"]) + ")"
    return (
        "MULTIPOLYGON(" + ",".join("(" + ",".join(anneau(a) for a in p) + ")" for p in geometrie["coordinates"]) + ")"
    )


def centroide(geometrie: dict) -> tuple[float, float]:
    points = [
        p
        for poly in (geometrie["coordinates"] if geometrie["type"] == "MultiPolygon" else [geometrie["coordinates"]])
        for p in poly[0]
    ]
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def ligne_cnig(entite: dict, numero: int) -> dict[str, str]:
    p = entite["properties"]
    ligne = {c: (INCONNU if c in LISTES else "") for c in COLONNES_CNIG}
    lon, lat = centroide(entite["geometry"])
    ligne.update(
        {
            "site_id": f"77305_{numero:03d}",
            "site_nom": p["nom"] or f"Site {p['parcelle_predominante']}",
            "site_identif_date": "2025-06-01",
            "site_actu_date": date.today().isoformat(),
            "comm_nom": p["commune"],
            "comm_insee": p["code_insee"],
            "bati_surface": str(p["surfaceBati"] or ""),
            "unite_fonciere_surface": str(p["surfaceSite"] or ""),
            "unite_fonciere_refcad": p["parcelles"],
            "source_nom": "Inventaire SCET" if p["partenaire"] else "Mutafriches",
            # Comme le fichier de référence du CNIG : latitude puis longitude
            "geompoint": f"POINT({lat:.6f} {lon:.6f})",
            "geomsurf": wkt(entite["geometry"]),
        }
    )
    return ligne


def ecrire_csv(chemin: Path, colonnes: list[str], lignes: list[dict[str, str]]) -> None:
    tampon = io.StringIO()
    redacteur = csv.DictWriter(tampon, fieldnames=colonnes, lineterminator="\r\n")
    redacteur.writeheader()
    redacteur.writerows(lignes)
    chemin.write_bytes(b"\xef\xbb\xbf" + tampon.getvalue().encode("utf-8"))


if __name__ == "__main__":
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=60) as reponse:
        brut = reponse.read()
    collection = json.loads(brut)
    collection["figeLe"] = date.today().isoformat()
    (DOSSIER / "attributaire-77305.geojson").write_text(
        json.dumps(collection, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    entites = sorted(
        collection["features"],
        key=lambda e: (e["properties"]["nom"] is None, e["properties"]["nom"] or "", e["properties"]["cle_site"]),
    )
    lignes = [ligne_cnig(e, i + 1) for i, e in enumerate(entites)]
    ecrire_csv(DOSSIER / "friches-cnig-montereau.csv", COLONNES_CNIG, lignes)
    # Fichier mêlant lignes correctes et lignes en erreur : doublon, parcelle mal formée, nom
    # vide, code INSEE invalide, géométrie absente, parcelles vides
    erreurs = [dict(l) for l in lignes[:10]]
    erreurs[2]["site_id"] = erreurs[1]["site_id"]
    erreurs[3]["unite_fonciere_refcad"] = "AB 160|77305000AB0161"
    erreurs[5]["site_nom"] = ""
    erreurs[6]["comm_insee"] = "7730"
    erreurs[7]["geompoint"] = ""
    erreurs[8]["unite_fonciere_refcad"] = ""
    ecrire_csv(DOSSIER / "friches-cnig-erreurs.csv", COLONNES_CNIG, erreurs)

    # Modèle à remplir : valeurs fictives impossibles à confondre avec un vrai inventaire
    modele = []
    for numero, (nom, type_site, parcelles) in enumerate(
        [
            ("Ancienne usine (exemple à remplacer)", "industrielle", "99999000ZZ0001|99999000ZZ0002"),
            ("Friche commerciale (exemple à remplacer)", "commerciale", "99999000ZZ0010"),
            ("Terrain nu (exemple à remplacer)", "autre", "99999000ZZ0020|99999000ZZ0021|99999000ZZ0022"),
        ],
        start=1,
    ):
        ligne = {c: (INCONNU if c in LISTES else "") for c in COLONNES_CNIG}
        ligne.update(
            {
                "site_id": f"99999_{numero:03d}",
                "site_nom": nom,
                "site_type": type_site,
                "site_identif_date": "2026-01-01",
                "site_actu_date": "2026-01-01",
                "comm_nom": "Commune-Exemple",
                "comm_insee": "99999",
                "unite_fonciere_refcad": parcelles,
                "source_nom": "Votre structure",
                "geompoint": "POINT(0.000000 0.000000)",
            }
        )
        modele.append(ligne)
    ecrire_csv(DOSSIER / "modele-cnig.csv", COLONNES_CNIG, modele)
    print(f"{len(entites)} sites figés dans {DOSSIER}")
