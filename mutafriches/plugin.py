"""Point d'entrée QGIS : bouton de barre d'outils et panneau."""

from pathlib import Path

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from .ui.dock import DockMutafriches
from .ui.parcours import Parcours


def version_extension() -> str:
    for ligne in (Path(__file__).resolve().parent / "metadata.txt").read_text(encoding="utf-8").splitlines():
        if ligne.startswith("version="):
            return ligne.split("=", 1)[1].strip()
    return ""


ICONE = str(Path(__file__).resolve().parent / "icons" / "mutafriches.svg")
MENU = "&Mutafriches"


class MutafrichesPlugin:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.action: QAction | None = None
        self.barre: QToolBar | None = None
        self.dock: DockMutafriches | None = None
        self.parcours: Parcours | None = None

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
            self.parcours = Parcours(self.iface, version_extension())
            self.dock = DockMutafriches(self.parcours, self.iface.mainWindow())
            self.dock.visibilityChanged.connect(self._visibilite)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        return self.dock

    def _basculer(self, visible: bool) -> None:
        dock = self._assurer_panneau()
        dock.setUserVisible(visible)

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
