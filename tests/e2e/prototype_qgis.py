"""Parcours du prototype dans une vraie session QGIS (lancé par scripts/e2e.sh).

Accueil, fichier refusé, exemple de Montereau, analyse, couches et tables, tableau de bord.
Les clics passent par de vrais événements Qt ; le navigateur n'est pas ouvert (fichier vérifié).
"""

import json
import os
import traceback
from collections.abc import Callable
from pathlib import Path

import qgis.utils
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRectangle, QgsSettings
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QLabel, QLineEdit, QPushButton, QWidget

from mutafriches.ui.widgets import Encadre

SORTIE = Path(os.environ["MF_E2E_SORTIE"])
# Captures PNG dans un dossier dédié (partagées), rapport et journal dans la sortie E2E
CAPTURES = Path(os.environ.get("MF_E2E_CAPTURES", str(SORTIE)))
PHASE = os.environ.get("MF_E2E_PHASE", "prototype")
# Jeux d'essai du dépôt (tests/donnees), hors du ZIP installé dans le profil
DONNEES = Path(os.environ["MF_DONNEES"])
FICHIER_CNIG_EXEMPLE = DONNEES / "friches-cnig-montereau.csv"
FICHIER_CNIG_ERREURS = DONNEES / "friches-cnig-erreurs.csv"
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
    return [
        b
        for b in (racine or dock()).findChildren(QPushButton)
        if b.isVisible() and b.text().strip().startswith(libelle)
    ]


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
    ancre = next(
        (d for d in iface.mainWindow().findChildren(QDockWidget) if d.isVisible() and fragment in d.windowTitle()), None
    )
    if ancre is not None:
        return ancre
    # Table ouverte en fenêtre malgré le réglage : on l'ancre en bas pour la capture
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
    ancre.setObjectName("mfTableCapture")
    ancre.setWidget(fenetre)
    iface.mainWindow().addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ancre)
    QApplication.processEvents()
    return ancre


@etape(1500)
def preparer() -> None:
    """Disposition des captures : carte au centre, couches à gauche, panneau à droite, tables en bas."""
    iface.mainWindow().resize(1600, 1000)
    QgsSettings().remove("plugins/mutafriches/utilisateur")
    QgsSettings().setValue("qgis/dockAttributeTable", True)
    for nom in ("Browser", "Browser2"):
        explorateur = iface.mainWindow().findChild(QDockWidget, nom)
        if explorateur is not None:
            explorateur.hide()
    iface.messageBar().clearWidgets()
    contexte["couches_avant"] = len(QgsProject.instance().mapLayers())
    plugin().action.trigger()


@etape(1500)
def ouvrir_panneau() -> None:
    noms = [c.name() for c in QgsProject.instance().mapLayers().values()]
    controler(
        "fond de carte ajouté à l'ouverture sur un projet vide",
        contexte["couches_avant"] == 0 and noms == ["Fond de carte OpenStreetMap"],
        noms,
    )
    largeur = iface.mapCanvas().extent().width()
    controler("carte cadrée sur la France", 1_000_000 < largeur < 4_000_000, largeur)
    vers_carte = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        iface.mapCanvas().mapSettings().destinationCrs(),
        QgsProject.instance(),
    )
    iface.mapCanvas().setExtent(vers_carte.transformBoundingBox(QgsRectangle(2.93, 48.375, 2.98, 48.40)))
    iface.mapCanvas().refresh()


@etape(1500)
def accueil() -> None:
    iface.mainWindow().resizeDocks([dock()], [440], Qt.Orientation.Horizontal)
    iface.messageBar().clearWidgets()
    controler("panneau ouvert sur l'accueil", dock().isVisible() and parcours().etape == 0)
    capture("01-accueil")
    page = dock().pages[0]
    page.mail.setText("sig-sans-arobase")
    page.domaine.setText("intranet")
    cliquer("Suivant")
    QApplication.processEvents()
    visibles = sorted(cle for cle, erreur in page.erreurs.items() if erreur.isVisible())
    controler(
        "accueil refusé : chaque champ obligatoire ou invalide signalé",
        parcours().etape == 0 and visibles == ["domaine", "mail", "nom", "prenom", "structure", "type_structure"],
        visibles,
    )
    capture("01b-accueil-erreur")
    page.prenom.setText("Camille")
    page.nom.setText("Martin")
    page.structure.setText("CC du Pays de Montereau")
    page.type_structure.setCurrentIndex(page.type_structure.findData("collectivite"))
    page.domaine.setText("https://www.cc-montereau.fr/")
    page.mail.setText("sig@exemple.fr")
    case = page.accepte_contact.case
    controler("consentement : case décochée par défaut", not case.isChecked() and case.isVisible())
    # Le libellé, long, coche sa case comme le texte d'une case ordinaire
    QTest.mouseClick(page.accepte_contact.libelle, Qt.MouseButton.LeftButton)
    coche = case.isChecked()
    QTest.mouseClick(page.accepte_contact.libelle, Qt.MouseButton.LeftButton)
    controler("consentement : le libellé coche et décoche la case", coche and not case.isChecked())
    capture("02-accueil-rempli")
    # Déclaration sans accord : la case est facultative
    cliquer("Suivant")


@etape(1500)
def panneau_vide() -> None:
    from mutafriches.core import reglages
    from mutafriches.core.client_api import url_api
    from mutafriches.core.declaration import origine_declaree

    controler(
        "structure déclarée à l'API locale, utilisateur enregistré",
        parcours().etape == 1
        and parcours().utilisateur.structure == "CC du Pays de Montereau"
        and parcours().utilisateur.resume.startswith("Camille Martin · ")
        and parcours().utilisateur.domaine == "www.cc-montereau.fr"
        and not parcours().utilisateur.accepte_contact
        and origine_declaree(url_api(), parcours().utilisateur.declaration()) == "https://www.cc-montereau.fr",
        reglages.DECLARATIONS.value(),
    )
    controler("bouton Analyser inactif", not any(b.isEnabled() for b in boutons("Analyser mes")))
    controler(
        "structure déclarée : coordonnées verrouillées, plus de lien « Modifier »",
        parcours().coordonnees_verrouillees and not boutons("Modifier"),
    )
    controler("accueil : pas de pied vide", not dock().pages[0].pied.isVisible())
    # Le modèle de fichier se télécharge depuis l'infobulle du champ, ouverte au clic
    from mutafriches.ui.widgets import BoutonAide

    aide = next(b for b in dock().pages[1].contenu.findChildren(BoutonAide) if b.isVisible())
    QTest.mouseClick(aide, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    liens = [b.text() for b in aide.bulle.findChildren(QPushButton)] if aide.bulle is not None else []
    controler(
        "infobulle du fichier : lien de téléchargement du modèle vide",
        liens == ["Télécharger un modèle de fichier vide"],
        liens,
    )
    if aide.bulle is not None:
        # Fenêtre à part : absente d'une capture de la fenêtre principale
        aide.bulle.grab().save(str(CAPTURES / "03b-infobulle-fichier-exemple.png"))
        aide.bulle.close()
    capture("03-import-vide")


@etape()
def fichier_avec_erreurs() -> None:
    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))
    lecture = parcours().lecture
    controler(
        "lignes en erreur écartées, fichier envoyable",
        lecture is not None and lecture.valide and len(lecture.sites_ko) == 6,
    )


@etape(800)
def modele() -> None:
    capture("04-fichier-lignes-en-erreur")
    libelles = [b.text() for b in boutons("") if b.isVisible()]
    controler(
        "sites KO : envoi sous la liste, avec rechargement du fichier",
        "Analyser les 4 sites OK" in libelles
        and "Charger de nouveau le fichier" in libelles
        and not any(x.startswith("Analyser mes") for x in libelles),
        libelles,
    )
    titres = [e.titre.text() for e in dock().findChildren(Encadre) if e.isVisible()]
    controler(
        "contrôle : un encadré pour les sites KO, un pour les sites OK",
        titres == ["6 sites KO (comportant des erreurs)", "4 sites OK"],
        titres,
    )
    chemin = parcours().enregistrer_modele(str(SORTIE / "modele-friches-cnig.csv"))
    controler(
        "modèle CNIG copié : colonnes seules",
        chemin is not None and len(chemin.read_text(encoding="utf-8-sig").strip().splitlines()) == 1,
    )
    parcours().choisir_fichier(str(chemin))
    controler(
        "modèle vide envoyé tel quel : refusé au contrôle",
        not parcours().pret_a_envoyer and not parcours().lecture.sites and bool(parcours().lecture.bloquants),
    )
    capture("04b-modele-vide-refuse")
    refuse = parcours().enregistrer_modele(str(SORTIE / "dossier-absent" / "modele.csv"))
    controler("dossier inaccessible : message, pas d'exception", refuse is None)
    iface.messageBar().clearWidgets()


@etape()
def exemple() -> None:
    parcours().nouvelle_analyse()
    parcours().choisir_fichier(str(FICHIER_CNIG_EXEMPLE))
    lecture = parcours().lecture
    controler("28 sites lus", lecture is not None and lecture.valide and len(lecture.sites_ok) == 28)


@etape(800)
def origine_refusee() -> None:
    capture("05-fichier-valide")
    titres = [e.titre.text() for e in dock().findChildren(Encadre) if e.isVisible()]
    controler("fichier sans erreur : le seul encadré des sites OK", titres == ["28 sites OK"], titres)
    controler(
        "API locale désignée au lancement, signalée au bandeau",
        "Environnement de test" in dock().bandeau.text() and dock().bandeau.isVisible(),
        dock().bandeau.text(),
    )
    from mutafriches.core.client_api import url_api
    from mutafriches.core.declaration import memoriser

    # Origine mémorisée que l'API ne connaît pas (domaine révoqué, registre vidé)
    memoriser(url_api(), parcours().utilisateur.declaration(), "https://autre.exemple.fr")
    cliquer("Analyser mes 28 sites")


@etape(2500)
def acces_refuse() -> None:
    erreur = parcours().erreur_api
    controler(
        "accès refusé signalé, retour à l'import",
        erreur is not None and "Accès refusé" in erreur.message and parcours().etape == 1,
        erreur,
    )
    capture("05b-acces-refuse")
    from mutafriches.core.client_api import url_api
    from mutafriches.core.declaration import origine_declaree

    controler(
        "origine refusée oubliée : la prochaine analyse redéclare",
        origine_declaree(url_api(), parcours().utilisateur.declaration()) == "",
    )
    controler(
        "accès refusé : le domaine redevient modifiable par le lien « Modifier »",
        not parcours().coordonnees_verrouillees and bool(boutons("Modifier")),
    )
    cliquer("Analyser mes 28 sites")


@etape(900)
def attente() -> None:
    traites, total = parcours().avancement
    controler(
        "analyse réelle en cours avec avancement",
        parcours().analyse_en_cours and total == 28 and 0 < traites < 28,
        (traites, total),
    )
    capture("06-analyse-en-cours")


@etape(9000)
def resultats() -> None:
    p = parcours()
    controler("résultats affichés", p.etape == 2 and p.synthese is not None and p.synthese.nombre_sites == 28)
    noms = [c.name() for c in QgsProject.instance().mapLayers().values()]
    controler(
        "deux couches créées", any("Mutabilité" in n for n in noms) and any("Qualification" in n for n in noms), noms
    )
    controler("étiquettes activées", p.couche_mutabilite.labelsEnabled())
    regles = p.couche_qualification.conditionalStyles().fieldStyles("pollution")
    controler("table de qualification : critères inconnus mis en évidence", len(regles) == 1)
    libelles = [b.text() for b in boutons("")]
    controler(
        "tableau de bord : lien de fiabilité, tables au pied, autre inventaire près du logo",
        "Améliorer la fiabilité" in libelles
        and "Voir table de mutabilité" in libelles
        and "Voir table de qualification" in libelles
        and dock().autre_inventaire.isVisible(),
        libelles,
    )
    # Lien suivi : intercepté au lieu d'ouvrir le navigateur du poste
    from qgis.PyQt.QtCore import QObject, QUrl, pyqtSlot
    from qgis.PyQt.QtGui import QDesktopServices

    class Capteur(QObject):
        def __init__(self) -> None:
            super().__init__()
            self.urls: list[str] = []

        @pyqtSlot(QUrl)
        def ouvrir(self, url: QUrl) -> None:
            self.urls.append(url.toString())

    capteur = Capteur()
    contexte["capteur"] = capteur
    QDesktopServices.setUrlHandler("https", capteur, "ouvrir")
    try:
        cliquer("Comprendre les résultats")
    finally:
        QDesktopServices.unsetUrlHandler("https")
    controler(
        "comprendre les résultats : doc web de production, visite marquée qgis",
        capteur.urls == ["https://mutafriches.beta.gouv.fr/comprendre-les-analyses?source=qgis&ref=tableau-de-bord"],
        capteur.urls,
    )
    textes = [e.text() for e in dock().pages[2].contenu.findChildren(QLabel) if e.isVisible()]
    controler(
        "tableau de bord : ni commune, ni provenance, ni bloc « attention »",
        not any("77305" in t or "analyse du" in t or "attention" in t for t in textes),
    )


@etape(4000)
def table_mutabilite() -> None:
    capture("07-resultats-carte")
    barre = dock().defilement.verticalScrollBar()
    for numero, position in enumerate((0.5, 1.0), start=1):
        barre.setValue(int(barre.maximum() * position))
        capture(f"07{'abc'[numero - 1]}-tableau-de-bord-{numero}")
    barre.setValue(0)
    cliquer("Voir table de mutabilité")


@etape(1500)
def site_sur_la_carte() -> None:
    table = dock_titre("Mutabilité")
    if table is not None:
        table.close()
    premier = parcours().synthese.sites_forte_compatibilite[0]
    avant = iface.mapCanvas().scale()
    cliquer_accessible(f"Voir sur la carte : {premier.nom}")
    couche = parcours().couche_mutabilite
    controler(
        "site sélectionné sur la carte",
        couche.selectedFeatureCount() == 1 and iface.mapCanvas().scale() < avant,
        (couche.selectedFeatureCount(), avant, iface.mapCanvas().scale()),
    )


@etape(2500)
def capture_site() -> None:
    capture("07d-site-selectionne")
    parcours().couche_mutabilite.removeSelection()
    parcours().zoomer()
    cliquer("Voir table de mutabilité")


@etape(1500)
def capture_table() -> None:
    table = dock_titre("Mutabilité")
    controler(
        "table attributaire mutabilité ancrée en bas",
        table is not None,
        [d.windowTitle() for d in iface.mainWindow().findChildren(QDockWidget) if d.isVisible()],
    )
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("08-table-mutabilite")
        table.close()
    cliquer("Voir table de qualification")


@etape(1500)
def capture_table_qualification() -> None:
    table = dock_titre("Qualification")
    controler("table attributaire qualification ancrée en bas", table is not None)
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("09-table-qualification")
        table.close()
    cliquer("Améliorer la fiabilité")


@etape(1500)
def capture_ameliorer_fiabilite() -> None:
    table = dock_titre("Qualification")
    colonnes = [c.name for c in parcours().couche_qualification.attributeTableConfig().columns()]
    controler(
        "améliorer la fiabilité : table de qualification ouverte, critères de terrain en tête",
        table is not None and colonnes[:3] == ["site_id", "site_nom", "proprietaire"],
        colonnes[:4],
    )
    if table is not None:
        iface.mainWindow().resizeDocks([table], [360], Qt.Orientation.Vertical)
        capture("09b-ameliorer-la-fiabilite")
        table.close()
    iface.messageBar().clearWidgets()


@etape()
def nouvelle_analyse() -> None:
    cliquer("Analyser un autre inventaire")
    controler("retour à l'import", parcours().etape == 1 and parcours().lecture is None)


# --- Second passage : fichier avec lignes en erreur, pour l'alerte « attention » -------------


@etape()
def envoyer_fichier_erreurs() -> None:
    parcours().choisir_fichier(str(FICHIER_CNIG_ERREURS))
    cliquer("Analyser les 4 sites OK")


@etape(4000)
def resultats_avec_alertes() -> None:
    p = parcours()
    controler(
        "4 sites analysés, 6 lignes écartées",
        p.etape == 2 and p.synthese.nombre_sites == 4 and len(p.lignes_ecartees) == 6,
    )
    from qgis.core import Qgis

    alertes = [m.text() for m in iface.messageBar().items() if m.level() == Qgis.MessageLevel.Warning]
    controler(
        "sites non analysés signalés dans la barre de messages de QGIS",
        any("6 sites non analysés" in a for a in alertes),
        alertes,
    )
    iface.messageBar().clearWidgets()


@etape(2500)
def capture_alertes() -> None:
    capture("10-resultats-avec-alertes")
    barre = dock().defilement.verticalScrollBar()
    barre.setValue(barre.maximum())
    capture("10b-sites-a-reprendre")
    cliquer("Analyser un autre inventaire")


@etape()
def reglages_en_lecture_seule() -> None:
    from mutafriches.core import reglages
    from mutafriches.ui import contenus

    p = parcours()
    page = plugin().options.createWidget(None)
    contexte["page"] = page
    controler(
        "page d'options : ni environnement, ni mode développeur, ni champ de saisie",
        not hasattr(page, "environnement") and not hasattr(page, "dev") and not page.findChildren(QLineEdit),
    )
    controler(
        "page d'options : coordonnées déclarées affichées, verrou expliqué",
        page.structure.text() == "CC du Pays de Montereau"
        and page.type_structure.text() == "Collectivité territoriale"
        and page.domaine.text() == "www.cc-montereau.fr"
        and page.mail.text() == "sig@exemple.fr"
        and page.aide_informations.text() == contenus.AIDE_OPTION_INFORMATIONS,
        (page.structure.text(), page.domaine.text(), page.aide_informations.text()),
    )
    # L'accord de contact et le fond de carte restent les seuls réglages modifiables
    page.accepte_contact.case.setChecked(True)
    page.fond_osm.setChecked(False)
    page.apply()
    controler(
        "accord de contact donné après coup : enregistré, coordonnées toujours verrouillées",
        p.utilisateur.accepte_contact
        and p.utilisateur.structure == "CC du Pays de Montereau"
        and p.coordonnees_verrouillees
        and p.etape == 1
        and not boutons("Modifier")
        and not reglages.FOND_OSM.value(),
        (p.utilisateur.accepte_contact, p.coordonnees_verrouillees, p.etape),
    )
    controler("production : aucun lien de mode ni de réglages dans le panneau", not boutons("Passer en mode"))


@etape(600)
def options_dans_qgis() -> None:
    # La vraie fenêtre Options de QGIS, ouverte comme par le menu Extensions › Mutafriches
    def saisir() -> None:
        fenetre = QApplication.activeModalWidget()
        controler(
            "fenêtre Options ouverte sur la page Mutafriches",
            fenetre is not None and fenetre.findChild(QWidget, "mutafrichesOptions") is not None,
        )
        if fenetre is not None:
            fenetre.resize(1300, 900)
            QApplication.processEvents()
            fenetre.grab().save(str(CAPTURES / "11-page-options.png"))
            fenetre.reject()

    QTimer.singleShot(1500, saisir)
    parcours().ouvrir_reglages()


@etape(600)
def remise_a_zero() -> None:
    from mutafriches.core import reglages

    reglages.effacer_utilisateur()
    reglages.FOND_OSM.remove()


def terminer() -> None:
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
        except Exception:
            rapport["erreurs"].append({"etape": fonction.__name__, "trace": traceback.format_exc()})  # type: ignore[union-attr]
            capture(f"erreur-{fonction.__name__}")
            terminer()
            return
        suivante(index + 1)

    QTimer.singleShot(delai, executer)


suivante()
