"""Panneau latéral : bandeau, en-tête, page courante et pied fixe."""

from pathlib import Path

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtCore import QPoint, Qt, QTimer
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ..core.reglages import STAGING, url_personnalisee
from . import style
from .pages import Page
from .parcours import Etape, Parcours
from .prototype import PageAccueil, PageImport, PageResultats
from .widgets import bouton

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

        # Réservé à l'équipe : rappel que le service interrogé n'est pas la production
        self.bandeau = QLabel()
        self.bandeau.setObjectName("mfStaging")
        layout.addWidget(self.bandeau)

        entete = QWidget()
        entete.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        entete_layout = QHBoxLayout(entete)
        entete_layout.setContentsMargins(16, 12, 16, 4)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)))
        logo.setAccessibleName("Mutafriches")
        logo.setToolTip("Mutafriches")
        entete_layout.addWidget(logo)
        entete_layout.addStretch(1)
        # À côté du logo plutôt qu'au pied : repartir d'un autre fichier n'est pas l'action principale
        self.autre_inventaire = bouton("Analyser un autre inventaire", "lien", parcours.nouvelle_analyse)
        entete_layout.addWidget(self.autre_inventaire, 0, Qt.AlignmentFlag.AlignVCenter)
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

    def _bandeau(self) -> None:
        """Rien en production ni en démonstration ; un rappel permanent sur le staging ou une API libre."""
        personnalisee = url_personnalisee() if self.parcours.reel else ""
        if personnalisee:
            texte = f"API personnalisée — {personnalisee}"
        elif self.parcours.environnement == STAGING:
            texte = "Environnement de test (staging)"
        else:
            texte = ""
        self.bandeau.setText(texte)
        self.bandeau.setAccessibleName(texte)
        self.bandeau.setVisible(bool(texte))

    def rafraichir(self) -> None:
        self._bandeau()
        etape = self.parcours.etape
        self.autre_inventaire.setVisible(etape == Etape.RESULTATS)
        for numero, page in self.pages.items():
            visible = numero == etape
            page.contenu.setVisible(visible)
            # Un pied sans contenu laisserait un liseré vide en bas du panneau
            page.pied.setVisible(visible and page.pied_layout.count() > 0)
        self.pages[etape].rafraichir()
        if etape != self._etape_affichee:
            self._etape_affichee = etape
            # Après la mise en page : le focus d'un bouton ferait sinon défiler la page au milieu
            QTimer.singleShot(0, lambda: self.defilement.verticalScrollBar().setValue(0))
