"""Socle des pages du panneau, encart de chargement et champ de saisie terrain."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget

from ..core.referentiel import CHAMP_OBLIGATOIRE, CHAMPS_PAR_CLE, CHOIX_VIDE, TYPES_POLLUTION
from . import style
from .parcours import Parcours
from .widgets import entete_champ, texte

TYPES_POLLUTION_CLES = {cle for cle, _ in TYPES_POLLUTION}


def pluriel(n: int, mot: str) -> str:
    return f"{n} {mot}{'s' if n > 1 else ''}"


class Page:
    def __init__(self, parcours: Parcours) -> None:
        self.parcours = parcours
        self.contenu = QWidget()
        self.corps = QVBoxLayout(self.contenu)
        self.corps.setContentsMargins(16, 8, 16, 16)
        self.corps.setSpacing(10)
        self.pied = QFrame()
        self.pied.setObjectName("mfPied")
        self.pied_layout = QVBoxLayout(self.pied)
        self.pied_layout.setContentsMargins(16, 10, 16, 10)
        self.pied_layout.setSpacing(8)
        # Fourni par le dock pour amener un widget à l'écran
        self.defiler_vers = lambda widget: None

    def rafraichir(self) -> None:
        raise NotImplementedError


class Chargement(QFrame):
    """Encart d'attente de la qualification automatique (EnrichmentLoadingCallout)."""

    def __init__(
        self, titre: str, sous_titre: str, message: str = "", avancement: tuple[int, int] | None = None
    ) -> None:
        super().__init__()
        self.setObjectName("mfBandeauSite")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        entete = texte(titre)
        entete.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {style.BLEU_FRANCE};")
        entete.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(entete)
        sous = texte(sous_titre)
        sous.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sous)
        barre = QProgressBar()
        barre.setObjectName("mfChargement")
        # Sans total connu, barre d'attente indéterminée
        if avancement is not None and avancement[1] > 0:
            barre.setRange(0, avancement[1])
            barre.setValue(avancement[0])
        else:
            barre.setRange(0, 0)
        barre.setTextVisible(False)
        layout.addWidget(barre)
        if message:
            citation = texte(message, "mfAide")
            citation.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(citation)


class ChampSaisie(QWidget):
    """Champ obligatoire : choix vide par défaut, message d'erreur sous la liste."""

    def __init__(self, cle: str, parcours: Parcours) -> None:
        super().__init__()
        self.cle = cle
        self.parcours = parcours
        # Rebranché par la page qui l'utilise (vue de détail d'un site, hors prototype)
        self.on_change = lambda cle, valeur: None
        champ = CHAMPS_PAR_CLE[cle]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(entete_champ(champ.libelle, champ.aide))
        self.liste = self._liste(champ.libelle, champ.options)
        layout.addWidget(self.liste)
        # Pollution « Oui » : le type est demandé ensuite (PollutionField)
        self.type_pollution: QComboBox | None = None
        self.libelle_type: QLabel | None = None
        # « Oui » sans type encore choisi : à conserver entre deux rafraîchissements
        self._oui_choisi = False
        if cle == "presencePollution":
            self.libelle_type = texte("Type de pollution")
            self.libelle_type.setStyleSheet("font-weight: bold;")
            self.type_pollution = self._liste("Type de pollution", TYPES_POLLUTION)
            layout.addWidget(self.libelle_type)
            layout.addWidget(self.type_pollution)
        self.erreur = texte(CHAMP_OBLIGATOIRE, "mfErreurChamp")
        self.erreur.setVisible(False)
        layout.addWidget(self.erreur)

    def _liste(self, nom: str, options: tuple[tuple[str, str], ...]) -> QComboBox:
        liste = QComboBox()
        liste.setAccessibleName(nom)
        liste.addItem(CHOIX_VIDE, "")
        for valeur, libelle in options:
            liste.addItem(libelle, valeur)
        # Les options longues du web élargiraient sinon tout le panneau : la liste suit sa
        # largeur, le menu déroulant affiche les libellés en entier
        liste.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        liste.setMinimumContentsLength(12)
        liste.view().setMinimumWidth(liste.view().sizeHintForColumn(0) + 24)
        liste.currentIndexChanged.connect(self._modifie)
        return liste

    def valeur(self) -> str:
        choix = str(self.liste.currentData() or "")
        if self.type_pollution is not None and choix == "oui":
            return str(self.type_pollution.currentData() or "")
        return choix

    def _modifie(self, *_: object) -> None:
        self._oui_choisi = self.liste.currentData() == "oui"
        self._afficher_type()
        valeur = self.valeur()
        if valeur:
            self.montrer_erreur(False)
        self.on_change(self.cle, valeur)

    def _afficher_type(self) -> None:
        if self.type_pollution is not None and self.libelle_type is not None:
            oui = self.liste.currentData() == "oui"
            self.type_pollution.setVisible(oui)
            self.libelle_type.setVisible(oui)

    def charger(self, valeur: str, pollution_referencee: bool = False) -> None:
        for liste in (self.liste, self.type_pollution):
            if liste is not None:
                liste.blockSignals(True)
        if self.type_pollution is not None:
            if valeur in TYPES_POLLUTION_CLES:
                self.liste.setCurrentIndex(self.liste.findData("oui"))
                self.type_pollution.setCurrentIndex(self.type_pollution.findData(valeur))
            else:
                # « Oui » présélectionné si le site est référencé dans les bases de sites pollués
                defaut = "oui" if (pollution_referencee or self._oui_choisi) and not valeur else valeur
                self.liste.setCurrentIndex(max(0, self.liste.findData(defaut)))
                self.type_pollution.setCurrentIndex(0)
        else:
            self.liste.setCurrentIndex(max(0, self.liste.findData(valeur)))
        for liste in (self.liste, self.type_pollution):
            if liste is not None:
                liste.blockSignals(False)
        self._afficher_type()

    def montrer_erreur(self, visible: bool) -> None:
        self.erreur.setVisible(visible)
        for liste in (self.liste, self.type_pollution):
            if liste is not None:
                liste.setProperty("erreur", visible)
                liste.style().unpolish(liste)
                liste.style().polish(liste)
