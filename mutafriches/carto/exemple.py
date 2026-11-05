"""Couche de parcelles d'exemple, pour tester sans couche cadastrale sous la main."""

from pathlib import Path

from qgis.core import QgsCoordinateReferenceSystem, QgsFillSymbol, QgsProject, QgsVectorLayer

FICHIER_PARCELLES = Path(__file__).resolve().parent.parent / "demo" / "terrain" / "parcelles.geojson"
NOM_COUCHE = "Parcelles d'exemple (Trélazé, IGN)"


def ajouter_parcelles_exemple() -> QgsVectorLayer:
    projet = QgsProject.instance()
    existante = next(iter(projet.mapLayersByName(NOM_COUCHE)), None)
    if isinstance(existante, QgsVectorLayer):
        return existante
    if not projet.mapLayers():
        projet.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    couche = QgsVectorLayer(str(FICHIER_PARCELLES), NOM_COUCHE, "ogr")
    if not couche.isValid():
        raise RuntimeError(f"Parcelles d'exemple illisibles : {FICHIER_PARCELLES}")
    # Contour sans remplissage : reste lisible sur un fond de carte
    couche.renderer().setSymbol(
        QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "90,90,90", "outline_width": "0.3"})
    )
    projet.addMapLayer(couche)
    return couche
