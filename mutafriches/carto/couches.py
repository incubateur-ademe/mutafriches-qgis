"""Couches de résultats du prototype : mutabilité et qualification, symbologie et étiquettes."""

import json
from typing import Optional

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDataSourceUri,
    QgsRasterLayer,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRendererCategory,
    QgsTextBackgroundSettings,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QMetaType, QSizeF
from qgis.PyQt.QtGui import QColor, QFont

from ..core.attributaire import (
    CRITERES_QUALIFICATION_AUTO,
    CRITERES_QUALIFICATION_SAISIS,
    ORDRE_USAGES,
    SiteAttributaire,
    libelle_saisie,
    libelle_usage,
)
from ..core.recapitulatif import valeur_etape
from ..core.referentiel import USAGES

NOM_COUCHE_MUTABILITE = "Mutafriches — Mutabilité"
NOM_COUCHE_QUALIFICATION = "Mutafriches — Qualification"
WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# Une couleur par usage, lisible sur fond de carte (palette du prototype, pas celle du web)
COULEURS_USAGES: dict[str, str] = {
    "residentiel": "#e4794a",
    "equipements": "#009099",
    "culture": "#a558a0",
    "tertiaire": "#000091",
    "industrie": "#7b7b7b",
    "renaturation": "#18753c",
    "photovoltaique": "#c3992a",
}
COULEUR_SANS_USAGE = "#cecece"


def _champ(nom: str, type_: QMetaType.Type = QMetaType.Type.QString) -> QgsField:
    return QgsField(nom, type_)


def _couche_vide(nom: str, champs: list[QgsField]) -> QgsVectorLayer:
    couche = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", nom, "memory")
    couche.dataProvider().addAttributes(champs)
    couche.updateFields()
    return couche


def _geometrie(site: SiteAttributaire) -> QgsGeometry:
    if site.geometrie is None:
        return QgsGeometry()
    geometrie = QgsGeometry.fromWkt(_wkt(site.geometrie))
    geometrie.convertToMultiType()
    return geometrie


def _wkt(geojson: dict) -> str:
    def anneau(a: list) -> str:
        return "(" + ",".join(f"{x} {y}" for x, y, *_ in a) + ")"

    if geojson["type"] == "Polygon":
        return "POLYGON(" + ",".join(anneau(a) for a in geojson["coordinates"]) + ")"
    if geojson["type"] == "MultiPolygon":
        return "MULTIPOLYGON(" + ",".join("(" + ",".join(anneau(a) for a in p) + ")" for p in geojson["coordinates"]) + ")"
    if geojson["type"] == "Point":
        x, y = geojson["coordinates"][:2]
        return f"POINT({x} {y})"
    return json.dumps(geojson)


# --- Table mutabilité ------------------------------------------------------------------------

def champs_mutabilite() -> list[QgsField]:
    # Colonnes dans l'ordre demandé ; noms calqués sur l'extension CNIG de l'export Mutafriches
    champs = [
        _champ("site_id"),
        _champ("site_nom"),
        _champ("mf_usage_prioritaire"),
        _champ("mf_usage_prioritaire_lib"),
        _champ("mf_indice_prioritaire", QMetaType.Type.Double),
    ]
    champs += [_champ(f"mf_indice_{u}", QMetaType.Type.Double) for u in ORDRE_USAGES]
    champs += [
        _champ("mf_fiabilite", QMetaType.Type.Double),
        _champ("mf_fiabilite_niveau"),
        _champ("mf_usages_exclus"),
        _champ("nb_parcelles", QMetaType.Type.Int),
        _champ("unite_fonciere_refcad"),
        _champ("comm_insee"),
        _champ("mf_version_algorithme"),
    ]
    return champs


def _entite_mutabilite(site: SiteAttributaire, champs: list[QgsField]) -> QgsFeature:
    entite = QgsFeature()
    entite.setFields(_fields(champs))
    entite.setGeometry(_geometrie(site))
    valeurs: list[object] = [
        site.site_id or site.cle,
        site.nom,
        site.usage_prioritaire,
        libelle_usage(site.usage_prioritaire),
        round(site.indice_max, 1),
    ]
    valeurs += [round(site.indices[u], 1) if u in site.indices else None for u in ORDRE_USAGES]
    valeurs += [
        site.fiabilite,
        site.fiabilite_niveau,
        "|".join(libelle_usage(u) for u in site.usages_exclus),
        len(site.parcelles),
        "|".join(site.parcelles),
        site.code_insee,
        str(site.proprietes.get("version_algorithme") or ""),
    ]
    entite.setAttributes(valeurs)
    return entite


# --- Table qualification ---------------------------------------------------------------------

def champs_qualification() -> list[QgsField]:
    champs = [_champ("site_id"), _champ("site_nom"), _champ("nb_parcelles", QMetaType.Type.Int), _champ("unite_fonciere_refcad")]
    champs += [_champ(colonne) for _, colonne in CRITERES_QUALIFICATION_AUTO]
    champs += [_champ("saisie_declarative"), _champ("date_saisie")]
    champs += [_champ(colonne) for _, colonne in CRITERES_QUALIFICATION_SAISIS]
    champs += [_champ("mf_fiabilite", QMetaType.Type.Double), _champ("mf_fiabilite_niveau"), _champ("donnees_manquantes")]
    return champs


def _entite_qualification(site: SiteAttributaire, champs: list[QgsField]) -> QgsFeature:
    entite = QgsFeature()
    entite.setFields(_fields(champs))
    entite.setGeometry(_geometrie(site))
    p = site.proprietes
    saisies = {cle: p.get(cle) for cle, _ in CRITERES_QUALIFICATION_SAISIS}
    valeurs: list[object] = [site.site_id or site.cle, site.nom, len(site.parcelles), "|".join(site.parcelles)]
    for cle, _ in CRITERES_QUALIFICATION_AUTO:
        valeur = valeur_etape(cle, p, {})  # type: ignore[arg-type]
        valeurs.append(", ".join(valeur) if isinstance(valeur, list) else (valeur or ""))
    valeurs += ["oui" if site.saisie_declarative else "non", str(p.get("date_saisie") or "")[:10]]
    valeurs += [libelle_saisie(cle, saisies.get(cle)) for cle, _ in CRITERES_QUALIFICATION_SAISIS]
    manquantes = [cle for cle, _ in CRITERES_QUALIFICATION_AUTO if p.get(cle) is None]
    valeurs += [site.fiabilite, site.fiabilite_niveau, ", ".join(manquantes)]
    entite.setAttributes(valeurs)
    return entite


def _fields(champs: list[QgsField]):  # type: ignore[no-untyped-def]
    from qgis.core import QgsFields

    fields = QgsFields()
    for champ in champs:
        fields.append(champ)
    return fields


# --- Symbologie et étiquettes ----------------------------------------------------------------

def _symbole(couleur: str) -> QgsFillSymbol:
    return QgsFillSymbol.createSimple(
        {"color": _rgba(couleur, 110), "outline_color": couleur, "outline_width": "0.6"}
    )


def _rgba(hexa: str, alpha: int) -> str:
    c = QColor(hexa)
    return f"{c.red()},{c.green()},{c.blue()},{alpha}"


def appliquer_symbologie(couche: QgsVectorLayer) -> None:
    categories = [
        QgsRendererCategory(usage, _symbole(COULEURS_USAGES[usage]), libelle_usage(usage))
        for usage in ORDRE_USAGES
    ]
    categories.append(QgsRendererCategory(None, _symbole(COULEUR_SANS_USAGE), "Aucun usage retenu"))
    couche.setRenderer(QgsCategorizedSymbolRenderer("mf_usage_prioritaire", categories))

    parametres = QgsPalLayerSettings()
    parametres.fieldName = (
        "\"site_nom\" || '\\n' || \"mf_usage_prioritaire_lib\" || ' · ' || round(\"mf_indice_prioritaire\") || ' %'"
    )
    parametres.isExpression = True
    parametres.placement = QgsPalLayerSettings.Placement.OverPoint
    parametres.centroidWhole = True
    format_texte = QgsTextFormat()
    police = QFont()
    police.setBold(True)
    format_texte.setFont(police)
    format_texte.setSize(9)
    format_texte.setColor(QColor("#ffffff"))
    fond = QgsTextBackgroundSettings()
    fond.setEnabled(True)
    fond.setType(QgsTextBackgroundSettings.ShapeType.ShapeRectangle)
    fond.setSize(QSizeF(1.5, 1.0))
    fond.setRadii(QSizeF(1.0, 1.0))
    fond.setFillColor(QColor(COULEUR_SANS_USAGE))
    fond.setStrokeColor(QColor("#ffffff"))
    fond.setStrokeWidth(0.4)
    format_texte.setBackground(fond)
    halo = QgsTextBufferSettings()
    halo.setEnabled(False)
    format_texte.setBuffer(halo)
    parametres.setFormat(format_texte)
    # Fond de l'étiquette à la couleur de l'usage : même lecture que le remplissage
    cas = "CASE " + " ".join(f"WHEN \"mf_usage_prioritaire\" = '{u}' THEN '{c}'" for u, c in COULEURS_USAGES.items()) + f" ELSE '{COULEUR_SANS_USAGE}' END"
    proprietes = parametres.dataDefinedProperties()
    proprietes.setProperty(QgsPalLayerSettings.Property.ShapeFillColor, QgsProperty.fromExpression(cas))
    parametres.setDataDefinedProperties(proprietes)
    couche.setLabelsEnabled(True)
    couche.setLabeling(QgsVectorLayerSimpleLabeling(parametres))


def appliquer_symbologie_qualification(couche: QgsVectorLayer) -> None:
    categories = [
        QgsRendererCategory("oui", _symbole("#18753c"), "Site qualifié (saisie déclarative)"),
        QgsRendererCategory("non", _symbole("#b34000"), "Site à qualifier (« Ne sait pas » partout)"),
    ]
    couche.setRenderer(QgsCategorizedSymbolRenderer("saisie_declarative", categories))


# --- Création dans le projet -----------------------------------------------------------------

def _remplacer(nom: str) -> None:
    projet = QgsProject.instance()
    for couche in projet.mapLayersByName(nom):
        projet.removeMapLayer(couche.id())


NOM_FOND = "Fond de carte OpenStreetMap"


def ajouter_fond_osm() -> None:
    """Fond OSM dans un projet vide, pour situer les sites (URI encodée par QgsDataSourceUri)."""
    projet = QgsProject.instance()
    if projet.mapLayers():
        return
    projet.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    uri = QgsDataSourceUri()
    uri.setParam("type", "xyz")
    uri.setParam("url", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    uri.setParam("zmax", "19")
    uri.setParam("zmin", "0")
    fond = QgsRasterLayer(bytes(uri.encodedUri()).decode(), NOM_FOND, "wms")
    if fond.isValid():
        projet.addMapLayer(fond)


def creer_couches(sites: list[SiteAttributaire], suffixe: str) -> tuple[QgsVectorLayer, QgsVectorLayer]:
    projet = QgsProject.instance()
    ajouter_fond_osm()
    nom_mutabilite = f"{NOM_COUCHE_MUTABILITE} ({suffixe})"
    nom_qualification = f"{NOM_COUCHE_QUALIFICATION} ({suffixe})"
    _remplacer(nom_mutabilite)
    _remplacer(nom_qualification)

    champs_m = champs_mutabilite()
    mutabilite = _couche_vide(nom_mutabilite, champs_m)
    mutabilite.dataProvider().addFeatures([_entite_mutabilite(s, champs_m) for s in sites])
    mutabilite.updateExtents()
    appliquer_symbologie(mutabilite)

    champs_q = champs_qualification()
    qualification = _couche_vide(nom_qualification, champs_q)
    qualification.dataProvider().addFeatures([_entite_qualification(s, champs_q) for s in sites])
    qualification.updateExtents()
    appliquer_symbologie_qualification(qualification)

    # Qualification sous la mutabilité, masquée par défaut : une seule lecture à la fois
    projet.addMapLayer(qualification)
    projet.addMapLayer(mutabilite)
    noeud = projet.layerTreeRoot().findLayer(qualification.id())
    if noeud is not None:
        noeud.setItemVisibilityChecked(False)
    return mutabilite, qualification


def emprise_carte(couche: QgsVectorLayer, destination: QgsCoordinateReferenceSystem):  # type: ignore[no-untyped-def]
    transformation = QgsCoordinateTransform(couche.crs(), destination, QgsProject.instance())
    emprise = transformation.transformBoundingBox(couche.extent())
    emprise.grow(max(emprise.width(), emprise.height()) * 0.08)
    return emprise


def couche_existante(nom: str) -> Optional[QgsVectorLayer]:
    couche = next(iter(QgsProject.instance().mapLayersByName(nom)), None)
    return couche if isinstance(couche, QgsVectorLayer) else None
