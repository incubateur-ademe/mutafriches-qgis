"""Graphiques natifs du panneau (QPainter) : QtCharts n'est pas embarqué par QGIS."""

from qgis.PyQt.QtCore import QRectF, Qt
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen
from qgis.PyQt.QtWidgets import QGridLayout, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from . import style
from .widgets import texte

Serie = list[tuple[str, int, str]]  # libellé, valeur, couleur


class Anneau(QWidget):
    """Anneau de répartition, total au centre, pour lire une ventilation d'un coup d'œil."""

    def __init__(self, serie: Serie, centre: str, sous_titre: str = "", diametre: int = 120) -> None:
        super().__init__()
        self.serie = [s for s in serie if s[1] > 0]
        self.centre = centre
        self.sous_titre = sous_titre
        self.setFixedSize(diametre, diametre)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(f"{centre} {sous_titre} : " + ", ".join(f"{l} {v}" for l, v, _ in self.serie))

    def paintEvent(self, evenement) -> None:  # type: ignore[no-untyped-def]
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        epaisseur = max(12, self.width() // 7)
        zone = QRectF(epaisseur / 2, epaisseur / 2, self.width() - epaisseur, self.height() - epaisseur)
        total = sum(v for _, v, _ in self.serie)
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        if not total:
            peintre.setPen(QPen(QColor(style.BORDURE), epaisseur, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            peintre.drawEllipse(zone)
        depart = 90 * 16
        for _, valeur, couleur in self.serie:
            portee = -int(360 * 16 * valeur / total)
            peintre.setPen(QPen(QColor(couleur), epaisseur, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            peintre.drawArc(zone, depart, portee)
            depart += portee
        peintre.setPen(QColor(style.TEXTE))
        police = QFont(self.font())
        police.setBold(True)
        police.setPointSize(max(14, self.width() // 6))
        peintre.setFont(police)
        interieur = zone.adjusted(epaisseur, epaisseur, -epaisseur, -epaisseur)
        if self.sous_titre:
            haut = QRectF(interieur.x(), interieur.y(), interieur.width(), interieur.height() * 0.58)
            bas = QRectF(
                interieur.x(), interieur.y() + interieur.height() * 0.5, interieur.width(), interieur.height() * 0.4
            )
            peintre.drawText(haut, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.centre)
            police.setBold(False)
            police.setPointSize(max(9, self.width() // 12))
            peintre.setFont(police)
            peintre.setPen(QColor(style.TEXTE_SECONDAIRE))
            peintre.drawText(bas, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.sous_titre)
        else:
            peintre.drawText(interieur, Qt.AlignmentFlag.AlignCenter, self.centre)
        peintre.end()


def pastille(couleur: str) -> QWidget:
    point = QWidget()
    point.setFixedSize(10, 10)
    point.setStyleSheet(f"background: {couleur}; border-radius: 5px;")
    return point


def anneau_avec_legende(serie: Serie, centre: str, sous_titre: str = "", total: int = 0) -> QWidget:
    """Anneau à gauche, légende « libellé  n (part) » à droite, dans la largeur du panneau."""
    bloc = QWidget()
    layout = QHBoxLayout(bloc)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.addWidget(Anneau(serie, centre, sous_titre), 0, Qt.AlignmentFlag.AlignTop)
    legende = QGridLayout()
    legende.setHorizontalSpacing(6)
    legende.setVerticalSpacing(4)
    total = total or sum(v for _, v, _ in serie)
    for rang, (libelle, valeur, couleur) in enumerate(s for s in serie if s[1] > 0):
        legende.addWidget(pastille(couleur), rang, 0)
        legende.addWidget(texte(libelle), rang, 1)
        part = texte(f"{valeur} ({round(100 * valeur / total) if total else 0} %)", "mfAide")
        part.setAlignment(Qt.AlignmentFlag.AlignRight)
        legende.addWidget(part, rang, 2)
    legende.setColumnStretch(1, 1)
    conteneur = QWidget()
    vertical = QVBoxLayout(conteneur)
    vertical.setContentsMargins(0, 0, 0, 0)
    vertical.addLayout(legende)
    vertical.addStretch(1)
    layout.addWidget(conteneur, 1)
    return bloc


def tableau(entetes: list[str], lignes: list[list[str]], largeurs: list[int] | None = None) -> QWidget:
    """Petit tableau en grille, lisible dans un panneau étroit."""
    bloc = QWidget()
    grille = QGridLayout(bloc)
    grille.setContentsMargins(0, 0, 0, 0)
    grille.setHorizontalSpacing(8)
    grille.setVerticalSpacing(3)
    for colonne, entete in enumerate(entetes):
        cellule = texte(entete, "mfSurTitre")
        grille.addWidget(cellule, 0, colonne)
    for rang, ligne in enumerate(lignes, start=1):
        for colonne, valeur in enumerate(ligne):
            cellule = texte(valeur, "mfAide" if colonne else "")
            grille.addWidget(cellule, rang, colonne)
    for colonne, largeur in enumerate(largeurs or []):
        grille.setColumnStretch(colonne, largeur)
    return bloc
