"""Page « Mutafriches » de Préférences › Options : service, informations, carte, développement."""

from collections.abc import Callable
from pathlib import Path

from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core import reglages
from ..core.client_api import LIBELLES_ENVIRONNEMENTS, URLS
from ..core.reglages import DEMONSTRATION, PRODUCTION, STAGING
from . import contenus
from .accueil import FORMAT_MAIL
from .parcours import NOM_PAGE_OPTIONS, Parcours
from .widgets import bouton, texte

# Largeur minimale des textes d'aide : sans elle, le formulaire les replie sur quelques mots
LARGEUR_AIDE = 520
ICONE = str(Path(__file__).resolve().parent.parent / "icons" / "mutafriches.svg")


def _groupe(titre: str) -> tuple[QGroupBox, QFormLayout]:
    groupe = QGroupBox(titre)
    formulaire = QFormLayout(groupe)
    formulaire.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    return groupe, formulaire


def _champ(formulaire: QFormLayout, libelle: str, widget: QWidget, aide: str = "") -> None:
    etiquette = QLabel(libelle)
    etiquette.setBuddy(widget)
    widget.setAccessibleName(libelle)
    if aide:
        widget.setToolTip(aide)
        etiquette.setToolTip(aide)
    formulaire.addRow(etiquette, widget)


class PageOptions(QgsOptionsPageWidget):
    def __init__(self, parent: QWidget | None, parcours: Callable[[], Parcours | None]) -> None:
        super().__init__(parent)
        self.setObjectName(NOM_PAGE_OPTIONS)
        # Le panneau n'existe pas forcément : la page le retrouve au moment d'appliquer
        self._parcours = parcours
        self._utilisateur_efface = False
        page = QVBoxLayout(self)

        service, formulaire = _groupe("Service")
        self.environnement = QComboBox()
        _champ(formulaire, "Environnement", self.environnement, contenus.AIDE_OPTION_ENVIRONNEMENT)
        self.adresse = texte("", "mfAide")
        self.adresse.setMinimumWidth(LARGEUR_AIDE)
        formulaire.addRow("", self.adresse)
        page.addWidget(service)

        informations, formulaire = _groupe("Vos informations")
        self.structure = QLineEdit()
        _champ(formulaire, "Structure", self.structure)
        self.mail = QLineEdit()
        _champ(formulaire, "Adresse mail", self.mail)
        self.consentement = QCheckBox(contenus.CONSENTEMENT_ACCUEIL)
        formulaire.addRow("", self.consentement)
        self.erreur_mail = texte("Adresse mail invalide : elle ne sera pas enregistrée.", "mfErreurChamp")
        formulaire.addRow("", self.erreur_mail)
        aide_informations = texte(contenus.AIDE_OPTION_INFORMATIONS, "mfAide")
        aide_informations.setMinimumWidth(LARGEUR_AIDE)
        formulaire.addRow("", aide_informations)
        effacer = bouton("Effacer mes informations", "secondaire", self._effacer_utilisateur)
        effacer.setToolTip("Le panneau redemandera votre structure et votre mail à sa prochaine ouverture.")
        formulaire.addRow("", effacer)
        page.addWidget(informations)

        carte, formulaire = _groupe("Carte")
        self.fond_osm = QCheckBox("Ajouter un fond OpenStreetMap quand le projet est vide")
        self.fond_osm.setToolTip(contenus.AIDE_OPTION_FOND)
        formulaire.addRow(self.fond_osm)
        page.addWidget(carte)

        developpement, formulaire = _groupe("Développement")
        self.dev = QCheckBox("Mode développeur (équipe Mutafriches)")
        self.dev.setToolTip(contenus.AIDE_OPTION_DEV)
        formulaire.addRow(self.dev)
        self.url = QLineEdit()
        self.url.setPlaceholderText("Vide : adresse de l'environnement choisi")
        _champ(
            formulaire, "Adresse d'API libre", self.url, "Serveur local ou de test, par exemple http://127.0.0.1:8799."
        )
        self.origine = QLineEdit()
        _champ(formulaire, "Origine envoyée", self.origine, "En-tête Origin, à faire autoriser côté Mutafriches.")
        self.intervalle = QSpinBox()
        self.intervalle.setRange(0, 60_000)
        self.intervalle.setSingleStep(100)
        self.intervalle.setSuffix(" ms")
        _champ(formulaire, "Délai entre deux sites", self.intervalle, contenus.AIDE_OPTION_INTERVALLE)
        self._champs_dev = [self.url, self.origine, self.intervalle]
        self._libelles_dev = [formulaire.labelForField(c) for c in self._champs_dev]
        page.addWidget(developpement)
        page.addStretch(1)

        self._charger()
        self.dev.toggled.connect(self._mode_dev_change)
        self.environnement.currentIndexChanged.connect(lambda *_: self._afficher_adresse())
        self.url.textChanged.connect(lambda *_: self._afficher_adresse())
        self.mail.textChanged.connect(lambda *_: self._controler_mail())

    # --- Chargement et affichage ----------------------------------------------------------------

    def _charger(self) -> None:
        self.dev.setChecked(reglages.DEV.value())
        self._remplir_environnements(reglages.environnement())
        self.structure.setText(reglages.STRUCTURE.value())
        self.mail.setText(reglages.MAIL.value())
        self.consentement.setChecked(reglages.CONSENTEMENT.value())
        self.fond_osm.setChecked(reglages.FOND_OSM.value())
        self.url.setText(reglages.URL.value())
        self.origine.setText(reglages.origine())
        self.intervalle.setValue(reglages.intervalle_ms())
        self._mode_dev_change(self.dev.isChecked())
        self._controler_mail()

    def _remplir_environnements(self, courant: str) -> None:
        self.environnement.blockSignals(True)
        self.environnement.clear()
        for cle, libelle in LIBELLES_ENVIRONNEMENTS.items():
            # Le staging est réservé à l'équipe
            if cle != STAGING or self.dev.isChecked():
                self.environnement.addItem(libelle, cle)
        position = self.environnement.findData(courant)
        self.environnement.setCurrentIndex(position if position >= 0 else self.environnement.findData(PRODUCTION))
        self.environnement.blockSignals(False)

    def _mode_dev_change(self, actif: bool) -> None:
        self._remplir_environnements(str(self.environnement.currentData() or PRODUCTION))
        for widget in (*self._champs_dev, *self._libelles_dev):
            widget.setVisible(actif)
        self._afficher_adresse()

    def _afficher_adresse(self) -> None:
        environnement = str(self.environnement.currentData() or PRODUCTION)
        libre = self.url.text().strip() if self.dev.isChecked() else ""
        if environnement == DEMONSTRATION:
            self.adresse.setText("Aucun appel réseau : résultats figés de Montereau-Fault-Yonne.")
        else:
            self.adresse.setText(f"API interrogée : {libre or URLS[environnement]}")

    def _controler_mail(self) -> None:
        saisie = self.mail.text().strip()
        self.erreur_mail.setVisible(bool(saisie) and not FORMAT_MAIL.match(saisie))

    def _effacer_utilisateur(self) -> None:
        self._utilisateur_efface = True
        self.structure.clear()
        self.mail.clear()
        self.consentement.setChecked(False)

    # --- Enregistrement -------------------------------------------------------------------------

    def apply(self) -> None:
        service_avant = (reglages.environnement(), reglages.url_personnalisee(), reglages.origine())
        reglages.DEV.setValue(self.dev.isChecked())
        reglages.ENVIRONNEMENT.setValue(str(self.environnement.currentData() or PRODUCTION))
        reglages.FOND_OSM.setValue(self.fond_osm.isChecked())
        # Les réglages d'API ne se modifient qu'en mode développeur ; sans lui, ils restent tels quels
        if self.dev.isChecked():
            adresse = self.url.text().strip()
            if adresse and not adresse.startswith(("http://", "https://")):
                adresse = ""
            reglages.URL.setValue(adresse)
            reglages.ORIGINE.setValue(self.origine.text().strip() or reglages.ORIGINE_DEFAUT)
            reglages.INTERVALLE_MS.setValue(self.intervalle.value())
        mail = self.mail.text().strip()
        if self._utilisateur_efface and not self.structure.text().strip() and not mail:
            reglages.effacer_utilisateur()
        elif not mail or FORMAT_MAIL.match(mail):
            reglages.STRUCTURE.setValue(self.structure.text().strip())
            reglages.MAIL.setValue(mail)
            reglages.CONSENTEMENT.setValue(self.consentement.isChecked())
        self._utilisateur_efface = False
        parcours = self._parcours()
        if parcours is not None:
            service_apres = (reglages.environnement(), reglages.url_personnalisee(), reglages.origine())
            parcours.reglages_modifies(service_change=service_apres != service_avant)


class FabriqueOptions(QgsOptionsWidgetFactory):
    def __init__(self, parcours: Callable[[], Parcours | None]) -> None:
        super().__init__()
        self._parcours = parcours
        self.setTitle("Mutafriches")

    def icon(self) -> QIcon:
        return QIcon(ICONE)

    def createWidget(self, parent: QWidget | None) -> PageOptions:
        return PageOptions(parent, self._parcours)
