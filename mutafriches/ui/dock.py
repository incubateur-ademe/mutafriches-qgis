"""Panneau latéral : bandeau, en-tête, page courante et pied fixe."""

from pathlib import Path

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtCore import QPoint, Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from . import style
from .pages import Page
from .parcours import Etape, Parcours
from .prototype import PageAccueil, PageImport, PageResultats

LOGO = Path(__file__).resolve().parent.parent / "icons" / "logo-mutafriches.png"


class DockMutafriches(QgsDockWidget):
    def __init__(self, parcours: Parcours, parent: QWidget) -> None:
        super().__init__("Mutafriches", parent)
        self.setObjectName("MutafrichesDock")
        self.parcours = parcours
        self.setMinimumWidth(320)

        racine = QWidget()
        racine.setObjectName("mfRacine")
        racine.setStyleSheet(style.feuille_de_style())
        layout = QVBoxLayout(racine)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if True:  # Prototype : résultats figés, jamais calculés en direct
            bandeau = QLabel("Mode démonstration — prototype sur données figées")
            bandeau.setObjectName("mfDemo")
            bandeau.setAccessibleName("Mode démonstration, données fictives")
            layout.addWidget(bandeau)

        entete = QWidget()
        entete.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        entete_layout = QVBoxLayout(entete)
        entete_layout.setContentsMargins(16, 12, 16, 4)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)))
        logo.setAccessibleName("Mutafriches")
        logo.setToolTip("Mutafriches")
        entete_layout.addWidget(logo)
        layout.addWidget(entete)

        self.pages: dict[int, Page] = {
            Etape.ACCUEIL: PageAccueil(parcours),
            Etape.IMPORT: PageImport(parcours),
            Etape.RESULTATS: PageResultats(parcours),
        }
        # Pages masquées plutôt qu'empilées : une page cachée ne réserve pas de hauteur
        conteneur = QWidget()
        conteneur.setObjectName("mfPages")
        pages_layout = QVBoxLayout(conteneur)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        self.defilement = QScrollArea()
        self.defilement.setWidgetResizable(True)
        self.defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.defilement.setWidget(conteneur)
        layout.addWidget(self.defilement, 1)
        for page in self.pages.values():
            page.defiler_vers = self._defiler_vers
            pages_layout.addWidget(page.contenu)
            layout.addWidget(page.pied)
        self.setWidget(racine)

        self._etape_affichee: int = -99
        parcours.change.connect(self.rafraichir)
        self.rafraichir()

    def _defiler_vers(self, widget: QWidget) -> None:
        y = widget.mapTo(self.defilement.widget(), QPoint(0, 0)).y()
        self.defilement.verticalScrollBar().setValue(max(0, y - 12))

    def rafraichir(self) -> None:
        etape = self.parcours.etape
        for numero, page in self.pages.items():
            visible = numero == etape
            page.contenu.setVisible(visible)
            page.pied.setVisible(visible)
        self.pages[etape].rafraichir()
        if etape != self._etape_affichee:
            self._etape_affichee = etape
            self.defilement.verticalScrollBar().setValue(0)
