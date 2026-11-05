"""Parcours du prototype dans une vraie session QGIS (lancé par scripts/e2e.sh).

Accueil, fichier refusé, exemple de Montereau, analyse, couches et tables, tableau de bord.
Les clics passent par de vrais événements Qt ; le navigateur n'est pas ouvert (fichier vérifié).
"""

import json
import os
import traceback
from pathlib import Path
from typing import Callable

import qgis.utils
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRectangle, QgsSettings
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QPushButton, QWidget

SORTIE = Path(os.environ["MF_E2E_SORTIE"])
# Captures PNG dans un dossier dédié (partagées), rapport et journal dans la sortie E2E
CAPTURES = Path(os.environ.get("MF_E2E_CAPTURES", str(SORTIE)))
PHASE = os.environ.get("MF_E2E_PHASE", "prototype")
iface = qgis.utils.iface
rapport: dict[str, object] = {"phase": PHASE, "controles": [], "erreurs": []}
etapes: list[tuple[int, Callable[[], None]]] = []
contexte: dict[str, object] = {}


def controler(nom: str, condition: bool, detail: object = "") -> None:
    rapport["controles"].append({"nom": nom, "ok": bool(condition), "detail": str(detail)})  # type: ignore[union-attr]


def capture(nom: str) -> None:
    QApplication.processEvents()
    iface.mainWindow().grab().save(str(CAPTURES / f"{nom}.png"))


def plugin():  # type: ignore[no-untyped-def]
    return qgis.utils.plugins["mutafriches"]


def parcours():  # type: ignore[no-untyped-def]
    return plugin().parcours


def dock() -> QWidget:
    return plugin().dock


def boutons(libelle: str, racine: QWidget | None = None) -> list[QPushButton]:
    # Les widgets ajoutés par un rafraîchissement ne sont visibles qu'après traitement des événements
    QApplication.processEvents()
    return [b for b in (racine or dock()).findChildren(QPushButton) if b.isVisible() and b.text().strip().startswith(libelle)]


def cliquer_accessible(nom: str) -> None:
    QApplication.processEvents()
    b = next((b for b in dock().findChildren(QPushButton) if b.isVisible() and b.accessibleName() == nom), None)
    if b is None:
        raise AssertionError(f"Bouton introuvable : {nom}")
    QTest.mouseClick(b, Qt.MouseButton.LeftButton)


def cliquer(libelle: str, racine: QWidget | None = None) -> None:
    candidats = [b for b in boutons(libelle, racine) if b.isEnabled()]
    if not candidats:
        raise AssertionError(f"Bouton visible et actif introuvable : {libelle}")
    QTest.mouseClick(candidats[0], Qt.MouseButton.LeftButton)


def etape(delai_ms: int = 300) -> Callable[[Callable[[], None]], Callable[[], None]]:
    def decorer(fonction: Callable[[], None]) -> Callable[[], None]:
        etapes.append((delai_ms, fonction))
        return fonction

    return decorer


def dock_titre(fragment: str) -> QDockWidget | None:
    QApplication.processEvents()
    ancre = next((d for d in iface.mainWindow().findChildren(QDockWidget) if d.isVisible() and fragment in d.windowTitle()), None)
    if ancre is not None:
        return ancre
    # Table ouverte en fenêtre malgré le réglage : on l'ancre en bas pour la capture
    fenetre = next((w for w in QApplication.topLevelWidgets() if w.isVisible() and w is not iface.mainWindow() and fragment in w.windowTitle()), None)
    if fenetre is None:
        return None
    ancre = QDockWidget(fenetre.windowTitle(), iface.mainWindow())
    ancre.setObjectName("mfTableCapture")
    ancre.setWidget(fenetre)
    iface.mainWindow().addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ancre)
    QApplication.processEvents()
    return ancre


@etape(1500)
def preparer() -> None:
    """Disposition des captures : carte au centre, couches à gauche, panneau à droite, tables en bas."""
    from mutafriches.carto.couches import ajouter_fond_osm

    iface.mainWindow().resize(1600, 1000)
    QgsSettings().remove("mutafriches/utilisateur")
    QgsSettings().setValue("qgis/dockAttributeTable", True)
    for nom in ("Browser", "Browser2"):
        explorateur = iface.mainWindow().findChild(QDockWidget, nom)
        if explorateur is not None:
            explorateur.hide()
    iface.messageBar().clearWidgets()
    ajouter_fond_osm()


@etape(1500)
def ouvrir_panneau() -> None:
    # Cadrage après que le canevas a pris le SCR du projet (3857)
    vers_carte = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), iface.mapCanvas().mapSettings().destinationCrs(), QgsProject.instance())
    iface.mapCanvas().setExtent(vers_carte.transformBoundingBox(QgsRectangle(2.93, 48.375, 2.98, 48.40)))
    iface.mapCanvas().refresh()
    plugin().action.trigger()


@etape(1500)
def accueil() -> None:
    from qgis.PyQt.QtWidgets import QCheckBox, QLineEdit

    iface.mainWindow().resizeDocks([dock()], [440], Qt.Orientation.Horizontal)
    iface.messageBar().clearWidgets()
    controler("panneau ouvert sur l'accueil", dock().isVisible() and parcours().etape == 0)
    capture("01-accueil")
    cliquer("Suivant")
    controler("accueil refusé sans structure ni mail", parcours().etape == 0)
    capture("01b-accueil-erreur")
    page = dock().pages[0]
    champs = page.contenu.findChildren(QLineEdit)
    champs[0].setText("CC du Pays de Montereau")
    champs[1].setText("sig@exemple.fr")
    page.contenu.findChild(QCheckBox).setChecked(True)
    page.erreur.setVisible(False)
    capture("02-accueil-rempli")
    cliquer("Suivant")


@etape(800)
def panneau_vide() -> None:
    controler("utilisateur enregistré", parcours().etape == 1 and parcours().utilisateur.structure == "CC du Pays de Montereau")
    controler("bouton Envoyer inactif", not any(b.isEnabled() for b in boutons("Envoyer")))
    capture("03-import-vide")


@etape()
def fichier_avec_erreurs() -> None:
    from mutafriches.core.attributaire import FICHIER_CNIG_ERREURS

    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))
    lecture = parcours().lecture
    controler("lignes en erreur écartées, fichier envoyable", lecture is not None and lecture.valide and len(lecture.sites_ko) == 6)


@etape(800)
def modele() -> None:
    capture("04-fichier-lignes-en-erreur")
    chemin = parcours().enregistrer_modele(str(SORTIE / "modele-friches-cnig.csv"))
    controler("modèle CNIG copié", chemin.exists() and "99999" in chemin.read_text(encoding="utf-8"))


@etape()
def exemple() -> None:
    from mutafriches.core.attributaire import FICHIER_CNIG_EXEMPLE

    parcours().nouvelle_analyse()
    parcours().choisir_fichier(str(FICHIER_CNIG_EXEMPLE))
    lecture = parcours().lecture
    controler("28 sites lus", lecture is not None and lecture.valide and len(lecture.sites_ok) == 28)


@etape(800)
def envoyer() -> None:
    capture("05-fichier-valide")
    cliquer("Envoyer mes 28 sites")


@etape(600)
def attente() -> None:
    controler("analyse en cours affichée", parcours().analyse_en_cours)
    capture("06-analyse-en-cours")


@etape(2600)
def resultats() -> None:
    p = parcours()
    controler("résultats affichés", p.etape == 2 and p.synthese is not None and p.synthese.nombre_sites == 28)
    noms = [c.name() for c in QgsProject.instance().mapLayers().values()]
    controler("deux couches créées", any("Mutabilité" in n for n in noms) and any("Qualification" in n for n in noms), noms)
    controler("étiquettes activées", p.couche_mutabilite.labelsEnabled())
    controler("tableau de bord écrit", p.dashboard is not None and p.dashboard.exists() and "pie-chart" in p.dashboard.read_text(encoding="utf-8"))
    copie = SORTIE / "tableau-de-bord-28-sites.html"
    copie.write_text(p.dashboard.read_text(encoding="utf-8"), encoding="utf-8")
    contexte["dashboard"] = str(copie)


@etape(4000)
def table_mutabilite() -> None:
    capture("07-resultats-carte")
    cliquer("Table mutabilité")


@etape(1500)
def site_sur_la_carte() -> None:
    table = dock_titre("Mutabilité")
    if table is not None:
        table.close()
    premier = parcours().synthese.sites_forte_compatibilite[0]
    avant = iface.mapCanvas().scale()
    cliquer_accessible(f"Voir sur la carte : {premier.nom}")
    couche = parcours().couche_mutabilite
    controler("site sélectionné sur la carte", couche.selectedFeatureCount() == 1 and iface.mapCanvas().scale() < avant, (couche.selectedFeatureCount(), avant, iface.mapCanvas().scale()))


@etape(2500)
def capture_site() -> None:
    capture("07b-site-selectionne")
    parcours().couche_mutabilite.removeSelection()
    parcours().zoomer()
    cliquer("Table mutabilité")


@etape(1500)
def capture_table() -> None:
    table = dock_titre("Mutabilité")
    controler("table attributaire mutabilité ancrée en bas", table is not None, [d.windowTitle() for d in iface.mainWindow().findChildren(QDockWidget) if d.isVisible()])
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("08-table-mutabilite")
        table.close()
    cliquer("Table qualification")


@etape(1500)
def capture_table_qualification() -> None:
    table = dock_titre("Qualification")
    controler("table attributaire qualification ancrée en bas", table is not None)
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("09-table-qualification")
        table.close()


@etape()
def nouvelle_analyse() -> None:
    cliquer("Analyser un autre inventaire")
    controler("retour à l'import", parcours().etape == 1 and parcours().lecture is None)


# --- Second passage : fichier avec lignes en erreur, pour l'alerte « attention » -------------


@etape()
def envoyer_fichier_erreurs() -> None:
    from mutafriches.core.attributaire import FICHIER_CNIG_ERREURS

    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))
    cliquer("Envoyer mes 4 sites")


@etape(3200)
def resultats_avec_alertes() -> None:
    p = parcours()
    controler("4 sites analysés, 6 lignes écartées", p.etape == 2 and p.synthese.nombre_sites == 4 and len(p.lignes_ecartees) == 6)
    controler("alerte attention dans le tableau de bord", "nécessitent votre attention" in p.dashboard.read_text(encoding="utf-8"))
    contexte["dashboard_alertes"] = str(p.dashboard)
    iface.mainWindow().findChild(QDockWidget, "mfTableCapture")


@etape(2500)
def capture_alertes() -> None:
    capture("10-resultats-avec-alertes")
    QgsSettings().remove("mutafriches/utilisateur")


def terminer() -> None:
    rapport["dashboard"] = contexte.get("dashboard", "")
    rapport["dashboard_alertes"] = contexte.get("dashboard_alertes", "")
    (SORTIE / f"rapport-{PHASE}.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    # Les couches mémoire déclenchent sinon une question à la fermeture
    QgsProject.instance().removeAllMapLayers()
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
