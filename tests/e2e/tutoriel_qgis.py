"""Captures du tutoriel web, jouées dans une vraie session QGIS contre l'API réelle.

Lancé par scripts/captures-tutoriel.sh. Parcours nominal seulement : installation, accueil,
fichier exemple, contrôle, analyse, carte, tables, site sur la carte, sites à reprendre.
Images en WebP, 1600 px de large, noms stables repris par la page web.
"""

import json
import os
import traceback
from collections.abc import Callable
from pathlib import Path

import qgis.utils
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRectangle, QgsSettings
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QCheckBox, QDockWidget, QLineEdit, QPushButton, QWidget

SORTIE = Path(os.environ["MF_TUTORIEL_SORTIE"])
RAPPORT = Path(os.environ["MF_TUTORIEL_RAPPORT"])
LARGEUR = 1600
DELAI_ANALYSE_S = 600
iface = qgis.utils.iface
rapport: dict[str, object] = {"captures": [], "erreurs": [], "notes": []}
etapes: list[tuple[int, Callable[[], None]]] = []


def plugin():  # type: ignore[no-untyped-def]
    return qgis.utils.plugins["mutafriches"]


def parcours():  # type: ignore[no-untyped-def]
    return plugin().parcours


def dock() -> QWidget:
    return plugin().dock


def enregistrer(image: QPixmap, nom: str) -> None:
    reduite = image.scaledToWidth(LARGEUR, Qt.TransformationMode.SmoothTransformation)
    reduite.setDevicePixelRatio(1)
    chemin = SORTIE / f"{nom}.webp"
    if not reduite.save(str(chemin), "webp", 82):
        raise RuntimeError(f"Capture non enregistrée : {chemin}")
    rapport["captures"].append(chemin.name)  # type: ignore[union-attr]


def capture(nom: str) -> None:
    taille = iface.mainWindow().size()
    if (taille.width(), taille.height()) != (1600, 1000):
        raise AssertionError(f"Fenêtre QGIS en {taille.width()}x{taille.height()}, 1600x1000 attendu")
    # Le tutoriel montre l'extension telle qu'en production : pas de bandeau d'environnement
    dock().bandeau.hide()
    QApplication.processEvents()
    enregistrer(iface.mainWindow().grab(), nom)


def cliquer(libelle: str) -> None:
    QApplication.processEvents()
    bouton = next(
        (
            b
            for b in dock().findChildren(QPushButton)
            if b.isVisible() and b.isEnabled() and b.text().strip().startswith(libelle)
        ),
        None,
    )
    if bouton is None:
        raise AssertionError(f"Bouton introuvable : {libelle}")
    QTest.mouseClick(bouton, Qt.MouseButton.LeftButton)


def cliquer_accessible(nom: str) -> None:
    QApplication.processEvents()
    bouton = next((b for b in dock().findChildren(QPushButton) if b.isVisible() and b.accessibleName() == nom), None)
    if bouton is None:
        raise AssertionError(f"Bouton introuvable : {nom}")
    QTest.mouseClick(bouton, Qt.MouseButton.LeftButton)


def table_ancree(fragment: str) -> QDockWidget | None:
    QApplication.processEvents()
    ancre = next(
        (d for d in iface.mainWindow().findChildren(QDockWidget) if d.isVisible() and fragment in d.windowTitle()), None
    )
    if ancre is not None:
        return ancre
    # Table ouverte en fenêtre malgré le réglage du profil : on l'ancre en bas pour la capture
    fenetre = next(
        (
            w
            for w in QApplication.topLevelWidgets()
            if w.isVisible() and w is not iface.mainWindow() and fragment in w.windowTitle()
        ),
        None,
    )
    if fenetre is None:
        return None
    ancre = QDockWidget(fenetre.windowTitle(), iface.mainWindow())
    ancre.setWidget(fenetre)
    iface.mainWindow().addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ancre)
    QApplication.processEvents()
    return ancre


def etape(delai_ms: int = 600) -> Callable[[Callable[[], None]], Callable[[], None]]:
    def decorer(fonction: Callable[[], None]) -> Callable[[], None]:
        etapes.append((delai_ms, fonction))
        return fonction

    return decorer


@etape(1500)
def preparer() -> None:
    from mutafriches.carto.couches import ajouter_fond_osm

    # Taille fixe, même si QGIS s'ouvre maximisé ou en plein écran : sinon le texte des captures rétrécit
    fenetre = iface.mainWindow()
    fenetre.showNormal()
    fenetre.setFixedSize(1600, 1000)
    QgsSettings().remove("mutafriches/utilisateur")
    QgsSettings().setValue("qgis/dockAttributeTable", True)
    for nom in ("Browser", "Browser2"):
        explorateur = iface.mainWindow().findChild(QDockWidget, nom)
        if explorateur is not None:
            explorateur.hide()
    iface.messageBar().clearWidgets()
    ajouter_fond_osm()


@etape(1500)
def installation() -> None:
    # Fenêtre modale du gestionnaire d'extensions, onglet « Installer depuis un ZIP »
    def saisir() -> None:
        fenetre = QApplication.activeModalWidget()
        try:
            if fenetre is None:
                rapport["notes"].append("Gestionnaire d'extensions non capturé (fenêtre absente).")  # type: ignore[union-attr]
                return
            fenetre.resize(1100, 700)
            QApplication.processEvents()
            enregistrer(fenetre.grab(), "01-installer-depuis-un-zip")
        finally:
            if fenetre is not None:
                fenetre.close()

    QTimer.singleShot(2500, saisir)
    try:
        # Onglets : toutes, installées, non installées, à mettre à jour, nouvelles, invalides, ZIP
        iface.pluginManagerInterface().showPluginManager(6)
    except Exception:
        rapport["notes"].append("Gestionnaire d'extensions non capturé : " + traceback.format_exc(limit=1))  # type: ignore[union-attr]


@etape(1500)
def ouvrir() -> None:
    vers_carte = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        iface.mapCanvas().mapSettings().destinationCrs(),
        QgsProject.instance(),
    )
    iface.mapCanvas().setExtent(vers_carte.transformBoundingBox(QgsRectangle(2.93, 48.375, 2.98, 48.40)))
    iface.mapCanvas().refresh()
    plugin().action.trigger()


@etape(2500)
def accueil() -> None:
    iface.mainWindow().resizeDocks([dock()], [440], Qt.Orientation.Horizontal)
    iface.messageBar().clearWidgets()
    page = dock().pages[0]
    champs = page.contenu.findChildren(QLineEdit)
    champs[0].setText("CC du Pays de Montereau")
    champs[1].setText("sig@exemple.fr")
    page.contenu.findChild(QCheckBox).setChecked(True)
    capture("02-se-presenter")
    cliquer("Suivant")


@etape(1000)
def fichier_exemple() -> None:
    capture("03-fichier-exemple")


@etape()
def fichier_avec_erreurs() -> None:
    from mutafriches.core.attributaire import FICHIER_CNIG_ERREURS

    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))


@etape(1000)
def controle() -> None:
    capture("04-controle-ligne-a-ligne")
    from mutafriches.core.attributaire import FICHIER_CNIG_EXEMPLE

    parcours().choisir_fichier(str(FICHIER_CNIG_EXEMPLE))


@etape(1000)
def envoyer() -> None:
    capture("05-fichier-pret")
    cliquer("Envoyer mes 28 sites")
    contexte["captures_analyse"] = 0
    contexte["depart"] = 0


contexte: dict[str, int] = {}


def attendre_resultats() -> None:
    """Patiente jusqu'aux résultats de l'API, en capturant l'avancement une fois vers le tiers."""
    p = parcours()
    contexte["depart"] += 1
    traites, total = p.avancement
    if p.analyse_en_cours and not contexte["captures_analyse"] and total and traites >= max(1, total // 3):
        capture("06-analyse-en-cours")
        contexte["captures_analyse"] = 1
    if p.etape == 2:
        suivante(contexte["index"] + 1)
    elif p.erreur_api is not None or not p.analyse_en_cours or contexte["depart"] > DELAI_ANALYSE_S:
        raise AssertionError(f"Analyse non aboutie : {p.erreur_api.message if p.erreur_api else 'délai dépassé'}")
    else:
        QTimer.singleShot(1000, lambda: garder(attendre_resultats))


etapes.append((1000, attendre_resultats))


@etape(5000)
def resultats() -> None:
    p = parcours()
    rapport["notes"].append(f"{p.synthese.nombre_sites} sites analysés, {len(p.echecs)} en échec : {p.echecs[:3]}")  # type: ignore[union-attr]
    capture("07-carte-et-tableau-de-bord")
    barre = dock().defilement.verticalScrollBar()
    barre.setValue(int(barre.maximum() * 0.55))
    capture("08-tableau-de-bord-profils")
    barre.setValue(barre.maximum())
    capture("09-tableau-de-bord-sites")
    barre.setValue(0)
    cliquer("Table mutabilité")


@etape(2000)
def table_mutabilite() -> None:
    table = table_ancree("Mutabilité")
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("10-table-mutabilite")
        table.close()
    cliquer("Table qualification")


@etape(2000)
def table_qualification() -> None:
    table = table_ancree("Qualification")
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("11-table-qualification")
        table.close()
    barre = dock().defilement.verticalScrollBar()
    barre.setValue(barre.maximum())
    premier = parcours().synthese.sites_forte_compatibilite
    if premier:
        cliquer_accessible(f"Voir sur la carte : {premier[0].nom}")


@etape(3500)
def site_sur_la_carte() -> None:
    capture("12-site-sur-la-carte")
    parcours().couche_mutabilite.removeSelection()
    cliquer("Analyser un autre inventaire")


@etape()
def envoyer_erreurs() -> None:
    from mutafriches.core.attributaire import FICHIER_CNIG_ERREURS

    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))
    cliquer("Envoyer mes 4 sites")
    contexte["captures_analyse"] = 1
    contexte["depart"] = 0


etapes.append((1000, attendre_resultats))


@etape(4000)
def sites_a_reprendre() -> None:
    barre = dock().defilement.verticalScrollBar()
    barre.setValue(barre.maximum())
    capture("13-sites-a-reprendre")
    QgsSettings().remove("mutafriches/utilisateur")


def terminer() -> None:
    RAPPORT.write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.actionExit().trigger()


def garder(fonction: Callable[[], None]) -> None:
    try:
        fonction()
    except Exception:
        rapport["erreurs"].append({"etape": fonction.__name__, "trace": traceback.format_exc()})  # type: ignore[union-attr]
        terminer()


def suivante(index: int = 0) -> None:
    if index >= len(etapes):
        terminer()
        return
    delai, fonction = etapes[index]
    contexte["index"] = index

    def executer() -> None:
        try:
            fonction()
        except Exception:
            rapport["erreurs"].append({"etape": fonction.__name__, "trace": traceback.format_exc()})  # type: ignore[union-attr]
            terminer()
            return
        # L'attente des résultats enchaîne elle-même quand l'analyse est finie
        if fonction is not attendre_resultats:
            suivante(index + 1)

    QTimer.singleShot(delai, executer)


# Reprise d'une seule capture sans rejouer l'analyse : MF_TUTORIEL_ETAPES=2 s'arrête après l'installation
if os.environ.get("MF_TUTORIEL_ETAPES"):
    del etapes[int(os.environ["MF_TUTORIEL_ETAPES"]) :]
suivante()
