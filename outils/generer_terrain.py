"""Génère le terrain de démonstration et les sources des réponses simulées.

Parcelles d'exemple réelles : parcellaire (PCI Express) de l'IGN à Trélazé (49), autour de la
rue Pierre Timbaud et d'une friche référencée dans Cartofriches (Cerema). L'enrichissement et
les résultats restent fictifs.

Sorties :
- mutafriches/demo/terrain/parcelles.geojson (Lambert 93, parcelles d'exemple)
- outils/sources-scenarios/<scenario>.json et generique.json (entrées du gel des réponses)

Usage : ./outils/figer-reponses.sh (lance ce script avec le Python de QGIS, requiert le réseau)
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

from qgis.core import QgsApplication, QgsGeometry

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_TERRAIN = RACINE / "mutafriches" / "demo" / "terrain"
DOSSIER_SOURCES = RACINE / "outils" / "sources-scenarios"
WFS = "https://data.geopf.fr/wfs/ows"
CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}}

# Emprise WGS84 (ouest, sud, est, nord) couvrant les trois friches et leurs abords
EMPRISE = (-0.4775, 47.4415, -0.4605, 47.4505)
CODE_INSEE = "49353"
COMMUNE = "Trélazé"


def wfs(type_name: str) -> list[dict]:
    ouest, sud, est, nord = EMPRISE
    requete = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": type_name,
        "SRSNAME": "EPSG:2154",
        "BBOX": f"{sud},{ouest},{nord},{est},urn:ogc:def:crs:EPSG::4326",
        "OUTPUTFORMAT": "application/json",
        "COUNT": "10000",
    }
    with urllib.request.urlopen(f"{WFS}?{urllib.parse.urlencode(requete)}", timeout=120) as reponse:
        return json.load(reponse)["features"]


def arrondir(coordonnees: object) -> object:
    if isinstance(coordonnees, list) and coordonnees and isinstance(coordonnees[0], (int, float)):
        return [round(coordonnees[0], 2), round(coordonnees[1], 2)]
    return [arrondir(c) for c in coordonnees]  # type: ignore[union-attr]


def ecrire(nom: str, entites: list[dict]) -> None:
    contenu = {"type": "FeatureCollection", "name": nom, "crs": CRS, "features": entites}
    chemin = DOSSIER_TERRAIN / f"{nom}.geojson"
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{nom} : {len(entites)} entités ({chemin.stat().st_size // 1024} Ko)")


def geometrie(entite: dict) -> QgsGeometry:
    return QgsGeometry.fromWkt(_wkt(entite["geometry"]))


def _wkt(geom: dict) -> str:
    def anneau(a: list) -> str:
        return "(" + ",".join(f"{x} {y}" for x, y, *_ in a) + ")"

    if geom["type"] == "Polygon":
        return "POLYGON(" + ",".join(anneau(a) for a in geom["coordinates"]) + ")"
    if geom["type"] == "MultiPolygon":
        return "MULTIPOLYGON(" + ",".join(
            "(" + ",".join(anneau(a) for a in p) + ")" for p in geom["coordinates"]
        ) + ")"
    raise ValueError(geom["type"])


def generer_terrain() -> tuple[dict[str, QgsGeometry], list[QgsGeometry]]:
    DOSSIER_TERRAIN.mkdir(parents=True, exist_ok=True)
    parcelles = []
    geometries: dict[str, QgsGeometry] = {}
    for f in wfs("CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle"):
        p = f["properties"]
        f["geometry"]["coordinates"] = arrondir(f["geometry"]["coordinates"])
        parcelles.append(
            {
                "type": "Feature",
                "properties": {
                    "idu": p["idu"],
                    "section": p["section"],
                    "numero": p["numero"],
                    "libelle": f"{p['section']} {p['numero']}",
                    "code_insee": p["code_insee"],
                    "commune": p["nom_com"],
                    "contenance": p["contenance"],
                },
                "geometry": f["geometry"],
            }
        )
        geometries[p["idu"]] = geometrie(f)
    ecrire("parcelles", sorted(parcelles, key=lambda e: e["properties"]["idu"]))

    # Bâtiments utilisés seulement pour la surface bâtie des friches types, non embarqués
    batiments = wfs("BDTOPO_V3:batiment")
    return geometries, [geometrie(b) for b in batiments]


# Enrichissement simulé : valeurs FICTIVES, clés et énumérations alignées sur
# EnrichissementOutputDto (packages/shared-types). Les surfaces sont calculées sur le terrain.
SOURCES_COMPLETES = [
    "Cadastre",
    "BDNB-SurfaceBatie",
    "Enedis-Raccordement",
    "API Service Public",
    "bpe",
    "Lovac",
    "Transport Data Gouv",
    "IGN WFS",
    "IGN Itinéraire",
    "GeoRisques-RGA",
    "GeoRisques-Cavites",
    "GeoRisques-TRI",
    "GeoRisques-ICPE",
    "ApiCartoNature",
    "ApiCartoGPU",
    "ZAER-ENR",
    "ZonageABC-Logement",
    "ITE-Fret",
    "France-Chaleur-Urbaine",
    "QPV-ANCT",
    "Enedis-Zones-Contrainte-EnR",
]

CONTEXTE_QUARTIER = {
    "codeInsee": CODE_INSEE,
    "commune": COMMUNE,
    "siteEnCentreVille": False,
    "distanceAutoroute": 4200,
    "distanceTransportCommun": 210,
    "proximiteCommercesServices": True,
    "distanceIte": "plus-1km",
    "distanceRaccordementElectrique": 150,
    "distanceReseauChaleur": 380,
    "tauxLogementsVacants": 6.9,
    "presenceRisquesTechnologiques": False,
    "risqueRetraitGonflementArgile": "faible-ou-moyen",
    "risqueCavitesSouterraines": "non",
    "risqueInondation": "non",
    "siteReferencePollue": False,
    "zonageReglementaire": "zone-urbaine-u",
    "zonageEnvironnemental": "hors-zone",
    "zonagePatrimonial": "non-concerne",
    "zonageAbcLogement": "b2",
    "siteEnQpv": False,
    "saturationReseauEnr": False,
    "zoneAccelerationEnr": "non",
    # Commune absente de la cartographie nationale des îlots de chaleur (donnée informative)
    "ilotChaleurUrbain": "non-couvert",
}

NE_SAIT_PAS = {
    cle: "ne-sait-pas"
    for cle in [
        "typeProprietaire",
        "etatBatiInfrastructure",
        "presencePollution",
        "valeurArchitecturaleHistorique",
        "qualitePaysage",
        "qualiteVoieDesserte",
        "trameVerteEtBleue",
        "presenceEspecesProtegees",
        "presenceZoneHumide",
    ]
}

SANS_SAISIE = {"id": "sans-saisie", "titre": "Sans connaissance terrain", "reponses": {}}

SCENARIOS = [
    {
        "id": "station-service",
        "titre": "Ancienne station-service",
        "description": "Friche de 4 parcelles contiguës (Cartofriches), une donnée indisponible.",
        "nomSuggere": "Ancienne station-service",
        "parcelles": ["AV1255", "AV1256", "AV1257", "AV1258"],
        "echecsAvantSucces": 0,
        "enrichissement": {
            "siteReferencePollue": True,
            "sourcesEchouees": ["France-Chaleur-Urbaine"],
            "champsManquants": ["distanceReseauChaleur"],
        },
        # Clé retirée plutôt que null : null signifie « recherche aboutie, aucun résultat »
        "clesAbsentes": ["distanceReseauChaleur"],
        "variantes": [
            SANS_SAISIE,
            {
                "id": "partielle",
                "titre": "Connaissance terrain partielle",
                "reponses": {
                    "typeProprietaire": "prive",
                    "etatBatiInfrastructure": "degradation-heterogene",
                },
            },
            {
                "id": "complete",
                "titre": "Connaissance terrain complète",
                "reponses": {
                    "typeProprietaire": "prive",
                    "etatBatiInfrastructure": "degradation-heterogene",
                    "presencePollution": "oui-autres-composes",
                    "valeurArchitecturaleHistorique": "ordinaire",
                    "qualitePaysage": "ordinaire",
                    "qualiteVoieDesserte": "accessible",
                    "trameVerteEtBleue": "corridor-a-preserver",
                    "presenceEspecesProtegees": "non",
                    "presenceZoneHumide": "non",
                },
            },
        ],
    },
    {
        "id": "pierre-timbaud",
        "titre": "Site de la rue Pierre Timbaud",
        "description": "Site d'une seule parcelle, toutes les données automatiques disponibles.",
        "nomSuggere": "Site de la rue Pierre Timbaud",
        "parcelles": ["AV1351"],
        "echecsAvantSucces": 0,
        "enrichissement": {
            "distanceTransportCommun": 320,
            "distanceRaccordementElectrique": 80,
            "distanceReseauChaleur": 540,
            "sourcesEchouees": [],
            "champsManquants": [],
        },
        "clesAbsentes": [],
        "variantes": [
            SANS_SAISIE,
            {
                "id": "complete",
                "titre": "Connaissance terrain complète",
                "reponses": {
                    "typeProprietaire": "prive",
                    "etatBatiInfrastructure": "degradation-moyenne",
                    "presencePollution": "oui-composes-volatils",
                    "valeurArchitecturaleHistorique": "ordinaire",
                    "qualitePaysage": "sans-interet",
                    "qualiteVoieDesserte": "accessible",
                    "trameVerteEtBleue": "hors-trame",
                    "presenceEspecesProtegees": "non",
                    "presenceZoneHumide": "non",
                },
            },
        ],
    },
    {
        "id": "pont-malembert",
        "titre": "Site du Pont-Malembert",
        "description": (
            "Site de 2 parcelles : le premier appel échoue (erreur récupérable), "
            "puis plusieurs sources restent indisponibles."
        ),
        "nomSuggere": "Site du Pont-Malembert",
        "parcelles": ["AV1349", "AV1350"],
        "echecsAvantSucces": 1,
        "enrichissement": {
            "distanceTransportCommun": 450,
            "distanceIte": "moins-1km-mauvais-etat",
            "zonageReglementaire": "zone-urbaine-u-activite",
            "sourcesEchouees": ["BDNB-SurfaceBatie", "Enedis-Raccordement", "GeoRisques-Cavites"],
            "champsManquants": [
                "surfaceBati",
                "distanceRaccordementElectrique",
                "risqueCavitesSouterraines",
            ],
        },
        "clesAbsentes": ["surfaceBati", "distanceRaccordementElectrique", "risqueCavitesSouterraines"],
        "variantes": [
            SANS_SAISIE,
            {
                "id": "complete",
                "titre": "Connaissance terrain complète",
                "reponses": {
                    "typeProprietaire": "prive",
                    "etatBatiInfrastructure": "degradation-tres-importante",
                    "presencePollution": "oui-amiante",
                    "valeurArchitecturaleHistorique": "sans-interet",
                    "qualitePaysage": "ordinaire",
                    "qualiteVoieDesserte": "degradee",
                    "trameVerteEtBleue": "hors-trame",
                    "presenceEspecesProtegees": "non",
                    "presenceZoneHumide": "non",
                },
            },
        ],
    },
]

# Profil générique : n'importe quelle sélection reçoit le contexte fictif du quartier, avec ses
# surfaces réelles. Les indices sont figés pour une grille de surfaces (site x part bâtie).
GRILLE_SURFACES_SITE = [300, 1000, 2500, 5000, 8000, 12500, 20000, 40000, 80000]
GRILLE_PARTS_BATIES = [0.0, 0.2, 0.5]
VARIANTES_GENERIQUES = [
    SANS_SAISIE,
    {
        "id": "complete",
        "titre": "Connaissance terrain complète (réponses types)",
        "reponses": {
            "typeProprietaire": "prive",
            "etatBatiInfrastructure": "degradation-moyenne",
            "presencePollution": "non",
            "valeurArchitecturaleHistorique": "ordinaire",
            "qualitePaysage": "ordinaire",
            "qualiteVoieDesserte": "accessible",
            "trameVerteEtBleue": "hors-trame",
            "presenceEspecesProtegees": "non",
            "presenceZoneHumide": "non",
        },
    },
]


def surface_batie(site: QgsGeometry, batiments: list[QgsGeometry]) -> float:
    boite = site.boundingBox()
    return sum(
        b.intersection(site).area() for b in batiments if b.boundingBox().intersects(boite)
    )


def contigu(geometries: list[QgsGeometry]) -> bool:
    union = QgsGeometry.unaryUnion([g.buffer(0.05, 2) for g in geometries])
    return not union.isMultipart() or len(union.asGeometryCollection()) == 1


def variantes_completes(variantes: list[dict]) -> list[dict]:
    return [{**v, "reponses": {**NE_SAIT_PAS, **v["reponses"]}} for v in variantes]


def generer_sources(parcelles: dict[str, QgsGeometry], batiments: list[QgsGeometry]) -> None:
    DOSSIER_SOURCES.mkdir(parents=True, exist_ok=True)
    for sc in SCENARIOS:
        ids = sorted(f"{CODE_INSEE}000{p}" for p in sc["parcelles"])
        geoms = [parcelles[i] for i in ids]
        if not contigu(geoms):
            raise SystemExit(f"Scénario {sc['id']} : parcelles non contiguës")
        site = QgsGeometry.unaryUnion(geoms)
        predominante = max(ids, key=lambda i: parcelles[i].area())
        enr = dict(CONTEXTE_QUARTIER)
        enr.update(
            {
                "identifiantParcelle": predominante,
                "surfaceSite": round(site.area()),
                "surfaceBati": round(surface_batie(site, batiments)),
            }
        )
        if len(ids) > 1:
            enr.update(
                {
                    "identifiantsParcelles": ids,
                    "nombreParcelles": len(ids),
                    "parcellePredominante": predominante,
                    "communePredominante": COMMUNE,
                }
            )
        enr.update(sc["enrichissement"])
        for cle in sc["clesAbsentes"]:
            enr.pop(cle, None)
        echouees = set(enr["sourcesEchouees"])
        enr["sourcesUtilisees"] = [s for s in SOURCES_COMPLETES if s not in echouees]
        source = {
            "id": sc["id"],
            "titre": sc["titre"],
            "description": sc["description"],
            "nomSuggere": sc["nomSuggere"],
            "parcelles": ids,
            "echecsAvantSucces": sc["echecsAvantSucces"],
            "enrichissement": enr,
            "variantes": variantes_completes(sc["variantes"]),
        }
        ecrire_json(DOSSIER_SOURCES / f"{sc['id']}.json", source)
        print(f"{sc['id']} : {len(ids)} parcelle(s), {enr['surfaceSite']} m², bâti {enr.get('surfaceBati')} m²")

    gabarit = dict(CONTEXTE_QUARTIER)
    gabarit.update(
        {"sourcesUtilisees": SOURCES_COMPLETES, "sourcesEchouees": [], "champsManquants": []}
    )
    ecrire_json(
        DOSSIER_SOURCES / "generique.json",
        {
            "gabarit": gabarit,
            "points": [
                {"surfaceSite": s, "surfaceBati": round(s * part)}
                for s in GRILLE_SURFACES_SITE
                for part in GRILLE_PARTS_BATIES
            ],
            "variantes": variantes_completes(VARIANTES_GENERIQUES),
        },
    )


def ecrire_json(chemin: Path, contenu: dict) -> None:
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    geometries_parcelles, geometries_batiments = generer_terrain()
    generer_sources(geometries_parcelles, geometries_batiments)
