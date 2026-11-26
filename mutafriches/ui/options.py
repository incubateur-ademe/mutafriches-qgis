"""Page « Mutafriches » de Préférences › Options : informations déclarées (en lecture seule) et carte."""

from collections.abc import Callable
from pathlib import Path

from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..core import reglages
from ..core.declaration import TYPES_STRUCTURE
from . import contenus
from .accueil import charger_utilisateur, coordonnees_verrouillees
from .parcours import NOM_PAGE_OPTIONS, Parcours
from .widgets import texte

# Largeur minimale des textes d'aide : sans elle, le formulaire les replie sur quelques mots
LARGEUR_AIDE = 520
ICONE = str(Path(__file__).resolve().parent.parent / "icons" / "mutafriches.svg")


def _groupe(titre: str) -> tuple[QGroupBox, QFormLayout]:
    groupe = QGroupBox(titre)
    formulaire = QFormLayout(groupe)
    formulaire.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    return groupe, formulaire


def _valeur(formulaire: QFormLayout, libelle: str) -> QLabel:
    """Ligne en lecture seule : la valeur se copie, elle ne se modifie pas."""
    valeur = texte("", selectionnable=True)
    # Sans largeur minimale, le formulaire replie la valeur et n'en montre que le début
    valeur.setMinimumWidth(LARGEUR_AIDE)
    valeur.setAccessibleName(libelle)
    formulaire.addRow(QLabel(libelle), valeur)
    return valeur


class PageOptions(QgsOptionsPageWidget):
    def __init__(self, parent: QWidget | None, parcours: Callable[[], Parcours | None]) -> None:
        super().__init__(parent)
        self.setObjectName(NOM_PAGE_OPTIONS)
        # Le panneau n'existe pas forcément : la page le retrouve au moment d'appliquer
        self._parcours = parcours
        page = QVBoxLayout(self)

        # Aucune saisie ici : les coordonnées se donnent une fois, à l'accueil du panneau (ADR-0006)
        informations, formulaire = _groupe("Vos informations")
        self.structure = _valeur(formulaire, contenus.LIBELLE_STRUCTURE)
        self.type_structure = _valeur(formulaire, contenus.LIBELLE_TYPE_STRUCTURE)
        self.domaine = _valeur(formulaire, contenus.LIBELLE_DOMAINE)
        self.prenom = _valeur(formulaire, contenus.LIBELLE_PRENOM)
        self.nom = _valeur(formulaire, contenus.LIBELLE_NOM)
        self.mail = _valeur(formulaire, contenus.LIBELLE_MAIL)
        # Exigé à l'accueil, il ne se retire pas ici : le retrait passe par la désinscription des e-mails
        self.accepte_contact = _valeur(formulaire, contenus.LIBELLE_ACCORD_DONNE)
        self.aide_informations = texte("", "mfAide")
        self.aide_informations.setMinimumWidth(LARGEUR_AIDE)
        formulaire.addRow("", self.aide_informations)
        page.addWidget(informations)

        carte, formulaire = _groupe("Carte")
        self.fond_osm = QCheckBox("Ajouter un fond OpenStreetMap quand le projet est vide")
        self.fond_osm.setToolTip(contenus.AIDE_OPTION_FOND)
        formulaire.addRow(self.fond_osm)
        page.addWidget(carte)
        page.addStretch(1)

        self._charger()

    def _charger(self) -> None:
        utilisateur = charger_utilisateur()
        valeurs = (
            (self.structure, utilisateur.structure),
            (self.type_structure, TYPES_STRUCTURE.get(utilisateur.type_structure, "")),
            (self.domaine, utilisateur.domaine),
            (self.prenom, utilisateur.prenom),
            (self.nom, utilisateur.nom),
            (self.mail, utilisateur.mail),
        )
        for champ, valeur in valeurs:
            champ.setText(valeur.strip() or contenus.VALEUR_ABSENTE)
        self.accepte_contact.setText(contenus.ACCORD_DONNE if utilisateur.accepte_contact else contenus.ACCORD_ABSENT)
        self.aide_informations.setText(
            contenus.AIDE_OPTION_INFORMATIONS
            if coordonnees_verrouillees(utilisateur)
            else contenus.AIDE_OPTION_INFORMATIONS_A_DECLARER
        )
        self.fond_osm.setChecked(reglages.FOND_OSM.value())

    def apply(self) -> None:
        reglages.FOND_OSM.setValue(self.fond_osm.isChecked())
        parcours = self._parcours()
        if parcours is not None:
            parcours.reglages_modifies()


class FabriqueOptions(QgsOptionsWidgetFactory):
    def __init__(self, parcours: Callable[[], Parcours | None]) -> None:
        super().__init__()
        self._parcours = parcours
        self.setTitle("Mutafriches")

    def icon(self) -> QIcon:
        return QIcon(ICONE)

    def createWidget(self, parent: QWidget | None) -> PageOptions:
        return PageOptions(parent, self._parcours)
