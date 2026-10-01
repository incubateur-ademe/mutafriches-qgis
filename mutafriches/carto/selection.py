"""Sélection dans une couche de polygones QGIS, contrôle du périmètre, surbrillance du site."""

import re
from dataclasses import dataclass, field
from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMapLayer,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapCanvas, QgsMapMouseEvent, QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from ..core.modele import ParcelleSite
from ..core.referentiel import formater_hectares

# Miroir de parcelle-selection.types.ts (application web)
MAX_PARCELLES = 20
SURFACE_MAX_M2 = 100_000
# Tolérance de contiguïté : absorbe les micro-écarts de numérisation entre parcelles voisines
TOLERANCE_CONTIGUITE_M = 0.05
# Surfaces et contiguïté mesurées en Lambert 93, quel que soit le SCR de la couche
LAMBERT_93 = QgsCoordinateReferenceSystem("EPSG:2154")

# Champs portant l'identifiant cadastral selon les sources usuelles (PCI Express, Etalab…)
CHAMPS_IDENTIFIANT = ("idu", "id", "IDU", "ID", "id_parcelle", "geo_parcelle")
# Code INSEE (5 caractères, Corse en 2A / 2B), préfixe, section, numéro
FORMAT_IDU = re.compile(r"^(?:\d{5}|2[AB]\d{3})[0-9A-Z]{3}[0-9A-Z]{2}\d{4}$")


def couche_polygones(couche: Optional[QgsMapLayer]) -> Optional[QgsVectorLayer]:
    if isinstance(couche, QgsVectorLayer) and couche.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry:
        return couche
    return None


def champ_identifiant(couche: QgsVectorLayer) -> Optional[str]:
    """Premier champ dont les valeurs ressemblent à un identifiant cadastral (14 caractères)."""
    noms = couche.fields().names()
    entite = next(couche.getFeatures(QgsFeatureRequest().setLimit(1)), None)
    if entite is None:
        return None
    for nom in CHAMPS_IDENTIFIANT:
        if nom in noms and FORMAT_IDU.match(str(entite[nom] or "")):
            return nom
    return None


def libelle_parcelle(idu: str) -> str:
    return f"{idu[8:10].lstrip('0') or '0'} {idu[10:]}" if FORMAT_IDU.match(idu) else idu


@dataclass
class AnalysePerimetre:
    parcelles: list[ParcelleSite] = field(default_factory=list)
    # Union des parcelles, en Lambert 93
    geometrie: Optional[QgsGeometry] = None
    contigu: bool = True
    problemes: list[str] = field(default_factory=list)
    # Identifiant de parcelle vers identifiant d'entité, pour retirer une parcelle de la sélection
    entites: dict[str, int] = field(default_factory=dict)

    @property
    def surface_m2(self) -> float:
        return sum(p.surface_m2 for p in self.parcelles)

    @property
    def valide(self) -> bool:
        return bool(self.parcelles) and not self.problemes


def _composantes(geometries: list[QgsGeometry]) -> int:
    elargies = [g.buffer(TOLERANCE_CONTIGUITE_M, 2) for g in geometries]
    vues: set[int] = set()
    composantes = 0
    for depart in range(len(geometries)):
        if depart in vues:
            continue
        composantes += 1
        pile = [depart]
        while pile:
            i = pile.pop()
            if i in vues:
                continue
            vues.add(i)
            pile.extend(
                j for j in range(len(geometries)) if j not in vues and elargies[i].intersects(geometries[j])
            )
    return composantes


def analyser(couche: QgsVectorLayer, entites: list[QgsFeature]) -> AnalysePerimetre:
    if not entites:
        return AnalysePerimetre()
    champ = champ_identifiant(couche)
    vers_l93 = QgsCoordinateTransform(couche.crs(), LAMBERT_93, QgsProject.instance())
    elements = []
    for entite in entites:
        geometrie = QgsGeometry(entite.geometry())
        geometrie.transform(vers_l93)
        # Sans identifiant cadastral, on retombe sur l'identifiant de l'entité
        idu = str(entite[champ]) if champ else f"{couche.name()} #{entite.id()}"
        elements.append((idu, geometrie, entite.id()))
    elements.sort(key=lambda e: e[0])
    geometries = [g for _, g, _ in elements]
    analyse = AnalysePerimetre(
        parcelles=[ParcelleSite(i, libelle_parcelle(i), round(g.area(), 1)) for i, g, _ in elements],
        geometrie=QgsGeometry.unaryUnion(geometries),
        entites={i: fid for i, _, fid in elements},
    )
    if len(elements) > MAX_PARCELLES:
        analyse.problemes.append(f"Un site compte au plus {MAX_PARCELLES} parcelles.")
    if len(elements) > 1 and analyse.surface_m2 > SURFACE_MAX_M2:
        analyse.problemes.append(
            f"Un site de plusieurs parcelles ne dépasse pas {formater_hectares(SURFACE_MAX_M2)}."
        )
    if len(elements) > 1 and _composantes(geometries) > 1:
        analyse.contigu = False
        analyse.problemes.append(
            "Les parcelles ne sont pas toutes contiguës : un site doit former un seul ensemble."
        )
    return analyse


class OutilParcelles(QgsMapTool):
    """Un clic ajoute la parcelle sous le curseur, un second clic la retire."""

    def __init__(self, canvas: QgsMapCanvas) -> None:
        super().__init__(canvas)
        self.couche: Optional[QgsVectorLayer] = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def canvasReleaseEvent(self, evenement: QgsMapMouseEvent) -> None:
        if evenement.button() != Qt.MouseButton.LeftButton or self.couche is None:
            return
        # Parcelle contenant le point, pas la plus proche dans un rayon : les petites
        # parcelles voisines seraient sinon prises à la place de celle visée
        point = self.toLayerCoordinates(self.couche, evenement.mapPoint())
        cible = QgsGeometry.fromPointXY(point)
        requete = QgsFeatureRequest().setFilterRect(QgsRectangle(point, point))
        for entite in self.couche.getFeatures(requete):
            if entite.geometry().contains(cible):
                if entite.id() in self.couche.selectedFeatureIds():
                    self.couche.deselect(entite.id())
                else:
                    self.couche.select(entite.id())
                return


class Surbrillance:
    """Emprise du site en cours, indépendante de la sélection QGIS."""

    def __init__(self, canvas: QgsMapCanvas) -> None:
        self.canvas = canvas
        self.bande = QgsRubberBand(canvas, QgsWkbTypes.GeometryType.PolygonGeometry)
        self.bande.setColor(QColor(0, 0, 145, 200))
        self.bande.setFillColor(QColor(0, 0, 145, 40))
        self.bande.setWidth(3)

    def afficher(self, geometrie_wkt: str) -> None:
        # Géométrie stockée en Lambert 93, reprojetée vers le SCR de la carte
        self.bande.setToGeometry(QgsGeometry.fromWkt(geometrie_wkt), LAMBERT_93)
        self.bande.show()

    def effacer(self) -> None:
        self.bande.reset(QgsWkbTypes.GeometryType.PolygonGeometry)

    def supprimer(self) -> None:
        self.effacer()
        self.canvas.scene().removeItem(self.bande)
