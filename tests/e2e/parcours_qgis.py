"""Parcours exécuté dans une vraie session QGIS (lancé par scripts/e2e.sh).

Phases : « parcours » (parcelles d'exemple, sélection, 3 étapes, résultats, nouvelle analyse)
et « couche-utilisateur » (couche quelconque en WGS84 dans un projet en Web Mercator).
Les clics sur la carte et sur les boutons passent par de vrais événements Qt.
"""

import json
import os
import traceback
from pathlib import Path
from typing import Callable, Optional

import qgis.utils
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QPoint, Qt, QTimer
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QPushButton, QWidget

SORTIE = Path(os.environ["MF_E2E_SORTIE"])
PHASE = os.environ.get("MF_E2E_PHASE", "parcours")
iface = qgis.utils.iface
rapport: dict[str, object] = {"phase": PHASE, "controles": [], "erreurs": []}
etapes: list[tuple[int, Callable[[], None]]] = []
contexte: dict[str, object] = {}

STATION = [f"49353000AV{n}" for n in ("1255", "1256", "1257", "1258")]
L93 = QgsCoordinateReferenceSystem("EPSG:2154")


def controler(nom: str, condition: bool, detail: object = "") -> None:
    rapport["controles"].append({"nom": nom, "ok": bool(condition), "detail": str(detail)})  # type: ignore[union-attr]


def capture(nom: str) -> None:
    QApplication.processEvents()
    iface.mainWindow().grab().save(str(SORTIE / f"{PHASE}-{nom}.png"))


def plugin():  # type: ignore[no-untyped-def]
    return qgis.utils.plugins["mutafriches"]


def parcours():  # type: ignore[no-untyped-def]
    return plugin().parcours


def dock() -> QWidget:
    return plugin().dock


def cliquer(libelle: str) -> None:
    candidats = [
        b
        for b in dock().findChildren(QPushButton)
        if b.isVisible() and b.isEnabled() and b.text().strip().startswith(libelle)
    ]
    if not candidats:
        raise AssertionError(f"Bouton visible introuvable : {libelle}")
    QTest.mouseClick(candidats[0], Qt.MouseButton.LeftButton)


def vers_carte(source: QgsCoordinateReferenceSystem) -> QgsCoordinateTransform:
    return QgsCoordinateTransform(source, iface.mapCanvas().mapSettings().destinationCrs(), QgsProject.instance())


def cliquer_entite(couche: QgsVectorLayer, entite: QgsFeature) -> None:
    point = vers_carte(couche.crs()).transform(QgsPointXY(entite.geometry().pointOnSurface().asPoint()))
    canvas = iface.mapCanvas()
    pixel = canvas.getCoordinateTransform().transform(point)
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(int(pixel.x()), int(pixel.y())))


def entite(couche: QgsVectorLayer, champ: str, valeur: str) -> QgsFeature:
    return next(couche.getFeatures(QgsFeatureRequest().setFilterExpression(f"\"{champ}\" = '{valeur}'")))


def zoomer(couche: QgsVectorLayer, geometrie: QgsGeometry, marge: float = 120) -> None:
    emprise = geometrie.boundingBox()
    emprise.grow(marge)
    iface.mapCanvas().setExtent(vers_carte(couche.crs()).transformBoundingBox(emprise))
    iface.mapCanvas().refresh()


def parcelle_libre(couche: QgsVectorLayer, eloignee_de: list[str]) -> QgsFeature:
    """Parcelle visible, hors friches types, non contiguë à la sélection donnée."""
    zone = QgsGeometry.unaryUnion([entite(couche, "idu", i).geometry() for i in eloignee_de]).buffer(2, 2)
    visible = vers_carte(couche.crs()).transformBoundingBox(
        iface.mapCanvas().extent(), QgsCoordinateTransform.TransformDirection.ReverseTransform
    )
    visible.scale(0.7)
    reserves = {i for s in parcours().service.scenarios for i in s.parcelles}
    for e in couche.getFeatures(QgsFeatureRequest().setFilterRect(visible)):
        g = e.geometry()
        if e["idu"] in reserves or not 800 < g.area() < 4000 or not visible.contains(g.boundingBox()):
            continue
        if not g.intersects(zone):
            return e
    raise AssertionError("Aucune parcelle libre visible")


def page(etape_: int):  # type: ignore[no-untyped-def]
    return dock().pages[etape_]


def remplir(etape_: int, valeurs: Optional[dict[str, str]] = None) -> None:
    """Renseigne les champs de l'étape ; les champs non précisés reçoivent « Ne sait pas »."""
    valeurs = valeurs or {}
    # Champs masqués compris : un champ peut réapparaître en cours de remplissage (« Pas de bâti »)
    for cle, champ in page(etape_).champs.items():
        valeur = valeurs.get(cle, "ne-sait-pas")
        if champ.type_pollution is not None and valeur.startswith("oui-"):
            champ.liste.setCurrentIndex(champ.liste.findData("oui"))
            champ.type_pollution.setCurrentIndex(champ.type_pollution.findData(valeur))
        else:
            champ.liste.setCurrentIndex(champ.liste.findData(valeur))


def modal(action: Callable[[QWidget], None], delai_ms: int = 700) -> None:
    """Agit sur la prochaine fenêtre modale : exec() bloque l'étape qui l'ouvre."""

    def agir() -> None:
        fenetre = QApplication.activeModalWidget()
        try:
            action(fenetre)
        except Exception:  # noqa: BLE001
            rapport["erreurs"].append({"etape": "modal", "trace": traceback.format_exc()})  # type: ignore[union-attr]
            if fenetre is not None:
                fenetre.close()

    QTimer.singleShot(delai_ms, agir)


def traverser_etapes(etape_1: Optional[dict[str, str]] = None) -> None:
    remplir(1, etape_1)
    cliquer("Suivant")
    remplir(2)
    cliquer("Suivant")
    cliquer("Suivant")


def etape(delai_ms: int = 300) -> Callable[[Callable[[], None]], Callable[[], None]]:
    def decorer(fonction: Callable[[], None]) -> Callable[[], None]:
        etapes.append((delai_ms, fonction))
        return fonction

    return decorer


# --- Phase 1 : parcours complet sur les parcelles d'exemple ------------------------------------

if PHASE == "parcours":

    @etape(1500)
    def ouvrir_panneau() -> None:
        iface.mainWindow().resize(1600, 1000)
        plugin().action.trigger()
        controler("panneau ouvert avec tutoriel", dock().isVisible() and parcours().couche is None)
        capture("01-tutoriel")

    @etape()
    def ajouter_exemple() -> None:
        cliquer("Ajouter des parcelles d'exemple")
        couches = list(QgsProject.instance().mapLayers().values())
        controler("une seule couche ajoutée", len(couches) == 1, [c.name() for c in couches])
        controler("parcelles de Trélazé", next(couches[0].getFeatures())["code_insee"] == "49353")
        controler("sélection active d'office", parcours().selection_active())

    @etape(1000)
    def selectionner_station() -> None:
        couche = parcours().couche
        contexte["couche"] = couche
        zoomer(couche, QgsGeometry.unaryUnion([entite(couche, "idu", i).geometry() for i in STATION]), 60)
        for idu in STATION:
            cliquer_entite(couche, entite(couche, "idu", idu))
        isolee = parcelle_libre(couche, STATION)
        contexte["isolee"] = str(isolee["idu"])
        cliquer_entite(couche, isolee)

    @etape()
    def non_contigu() -> None:
        analyse = parcours().analyse
        controler("parcelle isolée refusée", not analyse.valide and not analyse.contigu)
        from mutafriches.carto.selection import libelle_parcelle

        nom = f"Retirer la parcelle {libelle_parcelle(str(contexte['isolee']))}"
        QTest.mouseClick(
            next(b for b in dock().findChildren(QPushButton) if b.accessibleName() == nom), Qt.MouseButton.LeftButton
        )

    @etape()
    def analyser_station() -> None:
        analyse = parcours().analyse
        controler("4 parcelles contiguës", analyse.valide and len(analyse.parcelles) == 4)
        capture("02-selection")
        cliquer("Analyser ce site")

    @etape(600)
    def attente() -> None:
        controler("attente de qualification affichée", parcours().enrichissement_en_cours)
        capture("03-qualification-en-cours")

    @etape(2200)
    def etape_1() -> None:
        site = parcours().site
        controler("étape 1 après 2 s", parcours().etape == 1 and site.enrichissement is not None)
        pollution = page(1).champs["presencePollution"]
        controler("pollution « Oui » présélectionnée", pollution.liste.currentData() == "oui")
        controler("choix vide par défaut", page(1).champs["typeProprietaire"].liste.currentText() == "Sélectionner une option")
        cliquer("Suivant")
        erreurs = [c.cle for c in page(1).champs.values() if not c.erreur.isHidden()]
        controler("champs obligatoires signalés", parcours().etape == 1 and len(erreurs) == 4, erreurs)
        capture("04-etape-1-erreurs")
        page(1).champs["etatBatiInfrastructure"].liste.setCurrentIndex(
            page(1).champs["etatBatiInfrastructure"].liste.findData("pas-de-bati")
        )
        controler("valeur patrimoniale masquée si pas de bâti", page(1).champs["valeurArchitecturaleHistorique"].isHidden())
        remplir(1, {"typeProprietaire": "prive", "etatBatiInfrastructure": "degradation-heterogene"})
        controler("valeur patrimoniale réaffichée", not page(1).champs["valeurArchitecturaleHistorique"].isHidden())
        capture("05-etape-1")
        cliquer("Suivant")

    @etape()
    def etape_2() -> None:
        controler("étape 2", parcours().etape == 2)
        remplir(2)
        capture("06-etape-2")
        cliquer("Suivant")

    @etape()
    def etape_3() -> None:
        controler("étape 3", parcours().etape == 3)
        capture("07-etape-3")
        cliquer("Suivant")

    @etape(2300)
    def resultats() -> None:
        site = parcours().site
        controler("résultats après 2 s", parcours().etape == 4)
        controler("fiabilité 7,5", site.fiabilite()["note"] == 7.5, site.fiabilite()["note"])
        controler("réponse figée exacte", site.simulation.ecarts == 0, site.simulation)
        from mutafriches.ui.resultats import CartePodium, LigneTableau

        cartes = [c for c in dock().findChildren(CartePodium) if c.isVisible()]
        lignes = [l for l in dock().findChildren(LigneTableau) if l.isVisible()]
        controler("podium de 3 cartes", len(cartes) == 3)
        controler("tableau de 7 usages avec infobulle", len(lignes) == 7 and all(l.toolTip() for l in lignes))
        capture("08-resultats")
        contexte["lignes"] = lignes

        def fermer_detail(fenetre: QWidget) -> None:
            controler("détail d'usage ouvert", fenetre is not None and "Industrie" in fenetre.windowTitle(), fenetre)
            fenetre.grab().save(str(SORTIE / f"{PHASE}-09-detail-usage.png"))
            fenetre.accept()

        modal(fermer_detail)
        ligne = next(l for l in lignes if l.usage == "industrie")
        QTest.mouseClick(ligne, Qt.MouseButton.LeftButton)

    @etape()
    def recapitulatif() -> None:
        def fermer_recap(fenetre: QWidget) -> None:
            controler("récapitulatif ouvert", fenetre is not None and fenetre.windowTitle() == "Récapitulatif du site")
            fenetre.grab().save(str(SORTIE / f"{PHASE}-10-recapitulatif.png"))
            fenetre.accept()

        modal(fermer_recap)
        cliquer("voir récapitulatif du site")

    @etape()
    def modifier_donnees() -> None:
        cliquer("‹  Modifier les données")
        controler("retour à l'étape 1", parcours().etape == 1)
        traverser_etapes({"typeProprietaire": "prive", "etatBatiInfrastructure": "degradation-heterogene", "presencePollution": "non"})

    @etape(2300)
    def approximation() -> None:
        simulation = parcours().site.simulation
        controler("réponse approchée signalée", simulation.ecarts == 1, simulation)
        capture("11-approximation")
        cliquer("Nouvelle analyse")

    @etape()
    def libre() -> None:
        controler("nouvelle analyse vierge", parcours().etape == 0 and parcours().site is None)
        couche = contexte["couche"]
        libre = parcelle_libre(couche, STATION)
        contexte["libre"] = libre.geometry().area()
        cliquer_entite(couche, libre)

    @etape()
    def libre_analyser() -> None:
        cliquer("Analyser ce site")

    @etape(2300)
    def libre_etapes() -> None:
        donnees = parcours().site.enrichissement
        # Surface de la parcelle réellement sélectionnée (le clic peut tomber sur une voisine)
        surface = parcours().site.surface_m2
        controler("profil générique : surface mesurée", abs(donnees["surfaceSite"] - surface) < 1, (donnees["surfaceSite"], surface))
        controler("profil générique : commune", donnees["commune"] == "Trélazé", donnees["commune"])
        traverser_etapes()

    @etape(2300)
    def libre_resultat() -> None:
        simulation = parcours().site.simulation
        controler("profil générique signalé", bool(simulation.note), simulation)
        capture("12-resultats-libre")


# --- Phase 2 : couche de l'utilisateur, autre SCR ---------------------------------------------

else:

    @etape(1500)
    def preparer() -> None:
        iface.mainWindow().resize(1600, 1000)
        from mutafriches.carto.exemple import FICHIER_PARCELLES
        from mutafriches.core.service_simule import charger_scenarios

        exemple = QgsVectorLayer(str(FICHIER_PARCELLES), "source", "ogr")
        # Deux parcelles libres et contiguës, recopiées en WGS84 avec un champ « id » (format Etalab)
        reserves = {i for s in charger_scenarios() for i in s.parcelles}
        paire: Optional[tuple[QgsFeature, QgsFeature]] = None
        for a in exemple.getFeatures():
            if a["idu"] in reserves or not 500 < a.geometry().area() < 3000:
                continue
            voisine = next(
                (
                    b
                    for b in exemple.getFeatures(QgsFeatureRequest().setFilterRect(a.geometry().boundingBox()))
                    if b.id() != a.id() and b["idu"] not in reserves and b.geometry().touches(a.geometry())
                ),
                None,
            )
            if voisine is not None:
                paire = (a, voisine)
                break
        assert paire is not None
        couche = QgsVectorLayer("Polygon?crs=EPSG:4326&field=id:string&field=commune:string", "Ma couche cadastrale", "memory")
        vers_wgs84 = QgsCoordinateTransform(L93, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        for source in paire:
            copie = QgsFeature(couche.fields())
            copie.setAttributes([source["idu"], "Trélazé"])
            geometrie = QgsGeometry(source.geometry())
            geometrie.transform(vers_wgs84)
            copie.setGeometry(geometrie)
            couche.dataProvider().addFeatures([copie])
        contexte["surface"] = sum(f.geometry().area() for f in paire)
        QgsProject.instance().addMapLayer(couche)
        iface.setActiveLayer(couche)
        contexte["couche"] = couche
        plugin().action.trigger()

    # QGIS applique le SCR de la première couche après coup : on impose le 3857 ensuite
    @etape(1000)
    def projet_3857() -> None:
        couche = contexte["couche"]
        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        zoomer(couche, QgsGeometry.fromRect(couche.extent()), marge=0.0005)

    @etape(1000)
    def selectionner() -> None:
        couche = contexte["couche"]
        controler("couche utilisateur suivie", parcours().couche is couche)
        scr = (QgsProject.instance().crs().authid(), iface.mapCanvas().mapSettings().destinationCrs().authid())
        controler("projet en 3857", scr == ("EPSG:3857", "EPSG:3857"), scr)
        for e in couche.getFeatures():
            cliquer_entite(couche, e)

    @etape()
    def verifier() -> None:
        analyse = parcours().analyse
        controler("2 parcelles contiguës en WGS84", analyse.valide and len(analyse.parcelles) == 2, analyse.problemes)
        controler(
            "surface en m² malgré le WGS84",
            abs(analyse.surface_m2 - float(contexte["surface"])) < 5,
            (analyse.surface_m2, contexte["surface"]),
        )
        capture("13-couche-utilisateur")
        cliquer("Analyser ce site")

    @etape(2300)
    def commune() -> None:
        donnees = parcours().site.enrichissement
        controler("commune de l'exemple reconnue", donnees["commune"] == "Trélazé", donnees.get("commune"))
        traverser_etapes()

    @etape(2300)
    def resultat() -> None:
        controler("résultats sur couche utilisateur", parcours().etape == 4)
        capture("14-resultats-couche-utilisateur")


def terminer() -> None:
    (SORTIE / f"rapport-{PHASE}.json").write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    QgsProject.instance().setDirty(False)
    iface.actionExit().trigger()


def suivante(index: int = 0) -> None:
    if index >= len(etapes):
        terminer()
        return
    delai, fonction = etapes[index]

    def executer() -> None:
        try:
            fonction()
        except Exception:  # noqa: BLE001 (tout échec doit apparaître dans le rapport)
            rapport["erreurs"].append({"etape": fonction.__name__, "trace": traceback.format_exc()})  # type: ignore[union-attr]
            capture(f"erreur-{fonction.__name__}")
            terminer()
            return
        suivante(index + 1)

    QTimer.singleShot(delai, executer)


suivante()
