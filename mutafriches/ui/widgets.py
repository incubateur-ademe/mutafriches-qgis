"""Composants réutilisables du panneau."""

from typing import Callable, Optional

from qgis.PyQt.QtCore import QPoint, QRect, QSize, Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QToolButton,
    QToolTip,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import style


def texte(contenu: str, nom: str = "", selectionnable: bool = False) -> QLabel:
    label = QLabel(contenu)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    if nom:
        label.setObjectName(nom)
    if selectionnable:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def bouton(
    libelle: str, variante: str = "primaire", action: Optional[Callable[[], None]] = None
) -> QPushButton:
    noms = {"primaire": "mfPrimaire", "secondaire": "mfSecondaire", "lien": "mfLien"}
    b = QPushButton(libelle)
    b.setObjectName(noms[variante])
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if variante != "lien":
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    if action is not None:
        b.clicked.connect(action)
    return b


def separateur() -> QFrame:
    ligne = QFrame()
    ligne.setObjectName("mfSeparateur")
    return ligne


def vider(layout: QLayout) -> None:
    while layout.count():
        element = layout.takeAt(0)
        widget = element.widget()
        if widget is not None:
            # Masqué tout de suite : la destruction différée laisserait des restes à l'écran
            widget.hide()
            widget.deleteLater()
        elif element.layout() is not None:
            vider(element.layout())
            element.layout().deleteLater()


class Encadre(QFrame):
    """Alerte à bordure gauche colorée (info, succès, avertissement, erreur)."""

    def __init__(self, niveau: str = "info", titre: str = "", contenu: str = "") -> None:
        super().__init__()
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(12, 8, 10, 8)
        self.layout_.setSpacing(4)
        self.titre = texte(titre)
        self.titre.setStyleSheet("font-weight: bold;")
        self.contenu = texte(contenu)
        self.layout_.addWidget(self.titre)
        self.layout_.addWidget(self.contenu)
        self.definir(niveau, titre, contenu)

    def definir(self, niveau: str, titre: str, contenu: str = "") -> None:
        couleur, fond = style.NIVEAUX[niveau]
        self.setStyleSheet(
            f"Encadre {{ background: {fond}; border: none; border-left: 4px solid {couleur}; }}"
        )
        self.titre.setText(titre)
        self.titre.setStyleSheet(f"font-weight: bold; color: {couleur};")
        self.titre.setVisible(bool(titre))
        self.contenu.setText(contenu)
        self.contenu.setVisible(bool(contenu))
        self.setAccessibleName(f"{titre} {contenu}".strip())


class Stepper(QWidget):
    """Indicateur d'étapes du formulaire, comme sur l'application web."""

    def __init__(self, total: int = 3) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.numero = texte("", "mfAide")
        self.titre = texte("", "mfH2")
        layout.addWidget(self.numero)
        layout.addWidget(self.titre)
        barre = QHBoxLayout()
        barre.setSpacing(4)
        self.segments: list[QFrame] = []
        for _ in range(total):
            segment = QFrame()
            segment.setFixedHeight(6)
            self.segments.append(segment)
            barre.addWidget(segment)
        layout.addLayout(barre)
        self.suivante = texte("", "mfAide")
        layout.addWidget(self.suivante)

    def definir(self, courante: int, titre: str, suivante: str) -> None:
        self.numero.setText(f"Étape {courante} sur {len(self.segments)}")
        self.titre.setText(titre)
        self.suivante.setText(f"Étape suivante : {suivante}")
        for i, segment in enumerate(self.segments):
            couleur = style.BLEU_FRANCE if i < courante else "#dddddd"
            segment.setStyleSheet(f"background: {couleur}; border: none;")
        self.setAccessibleName(f"Étape {courante} sur {len(self.segments)} : {titre}")


class FlowLayout(QLayout):
    """Disposition en flux : les éléments passent à la ligne (badges, étiquettes)."""

    def __init__(self, parent: Optional[QWidget] = None, espacement: int = 6) -> None:
        super().__init__(parent)
        self._elements: list[QLayoutItem] = []
        self._espacement = espacement
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, element: QLayoutItem) -> None:
        self._elements.append(element)

    def count(self) -> int:
        return len(self._elements)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        return self._elements[index] if 0 <= index < len(self._elements) else None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        return self._elements.pop(index) if 0 <= index < len(self._elements) else None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, largeur: int) -> int:
        return self._placer(QRect(0, 0, largeur, 0), simuler=True)

    def setGeometry(self, zone: QRect) -> None:
        super().setGeometry(zone)
        self._placer(zone, simuler=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        taille = QSize()
        for element in self._elements:
            taille = taille.expandedTo(element.minimumSize())
        return taille

    def _placer(self, zone: QRect, simuler: bool) -> int:
        x, y, hauteur_ligne = zone.x(), zone.y(), 0
        for element in self._elements:
            taille = element.sizeHint()
            if x + taille.width() > zone.right() + 1 and hauteur_ligne > 0:
                x = zone.x()
                y += hauteur_ligne + self._espacement
                hauteur_ligne = 0
            if not simuler:
                element.setGeometry(QRect(QPoint(x, y), taille))
            x += taille.width() + self._espacement
            hauteur_ligne = max(hauteur_ligne, taille.height())
        return y + hauteur_ligne - zone.y()


def badge(contenu: str, nature: str = "enrichi", majuscules: bool = False) -> QLabel:
    couleur, fond = style.BADGES[nature]
    etiquette = QLabel(contenu.upper() if majuscules else contenu)
    etiquette.setWordWrap(False)
    etiquette.setStyleSheet(
        f"background: {fond}; color: {couleur}; border-radius: 4px; padding: 2px 6px;"
        f" font-size: 12px; font-weight: bold;"
    )
    return etiquette


def badges(valeurs: list[str], nature: str = "enrichi") -> QWidget:
    conteneur = QWidget()
    flux = FlowLayout(conteneur)
    for valeur in valeurs:
        flux.addWidget(badge(valeur, nature))
    return conteneur


class BoutonAide(QToolButton):
    """Bouton « ? » : infobulle au survol et au clic, comme les infobulles DSFR du web."""

    def __init__(self, aide: str, nom_accessible: str = "") -> None:
        super().__init__()
        self.setObjectName("mfAide")
        self.setText("?")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"<p style='max-width: 320px'>{aide}</p>")
        self.setAccessibleName(f"Infobulle {nom_accessible}".strip())
        self.setAccessibleDescription(aide)
        self.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), self.toolTip(), self))


def entete_champ(libelle: str, aide: str = "", gras: bool = True) -> QWidget:
    ligne = QWidget()
    layout = QHBoxLayout(ligne)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    etiquette = texte(libelle)
    if gras:
        etiquette.setStyleSheet("font-weight: bold;")
    layout.addWidget(etiquette, 1)
    if aide:
        layout.addWidget(BoutonAide(aide, libelle), 0, Qt.AlignmentFlag.AlignTop)
    return ligne
