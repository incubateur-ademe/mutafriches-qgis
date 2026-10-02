"""Point d'entrée QGIS : bouton de barre d'outils et panneau."""

from pathlib import Path
from typing import Optional

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from .core.service_simule import ServiceSimule
from .ui.dock import DockMutafriches
from .ui.parcours import Parcours

ICONE = str(Path(__file__).resolve().parent / "icons" / "mutafriches.svg")
MENU = "&Mutafriches"


class MutafrichesPlugin:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.action: Optional[QAction] = None
        self.barre: Optional[QToolBar] = None
        self.dock: Optional[DockMutafriches] = None
        self.parcours: Optional[Parcours] = None

    def initGui(self) -> None:
        self.action = QAction(QIcon(ICONE), "Mutafriches", self.iface.mainWindow())
        self.action.setToolTip("Ouvrir le panneau Mutafriches")
        self.action.setCheckable(True)
        self.action.toggled.connect(self._basculer)
        self.barre = self.iface.addToolBar("Mutafriches")
        self.barre.setObjectName("MutafrichesToolbar")
        self.barre.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.barre.addAction(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

    def _assurer_panneau(self) -> DockMutafriches:
        if self.dock is None:
            # Attente simulée de 2 s, proche des temps de réponse de l'API
            service = ServiceSimule(delai_enrichissement_ms=2000, delai_evaluation_ms=2000)
            self.parcours = Parcours(self.iface, service)
            # Le profil générique simulé a besoin de la surface mesurée sur la sélection
            service.mesurer = self.parcours.mesurer
            self.dock = DockMutafriches(self.parcours, self.iface.mainWindow())
            self.dock.visibilityChanged.connect(self._visibilite)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        return self.dock

    def _basculer(self, visible: bool) -> None:
        dock = self._assurer_panneau()
        dock.setUserVisible(visible)
        if visible and self.parcours is not None:
            self.parcours.activer_selection(self.parcours.etape == 0)

    def _visibilite(self, visible: bool) -> None:
        if self.action is not None and self.dock is not None:
            self.action.blockSignals(True)
            self.action.setChecked(self.dock.isUserVisible())
            self.action.blockSignals(False)

    def unload(self) -> None:
        if self.parcours is not None:
            self.parcours.nettoyer()
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
        if self.action is not None:
            self.iface.removePluginMenu(MENU, self.action)
        if self.barre is not None:
            self.barre.deleteLater()
        self.dock = None
        self.parcours = None
