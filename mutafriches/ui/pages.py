"""Écrans de sélection et de qualification, calqués sur l'application web."""

import random
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.recapitulatif import valeur_etape
from ..core.referentiel import (
    CHAMP_OBLIGATOIRE,
    CHAMPS_PAR_CLE,
    CHOIX_VIDE,
    DONNEE_NON_ACCESSIBLE,
    NE_SAIT_PAS,
    PAS_DE_BATI,
    TYPES_POLLUTION,
    formater_surface,
)
from . import contenus, style
from .contenus import SEPARATEUR, Info, Saisie
from .parcours import Etape, Parcours
from .widgets import Encadre, Stepper, badge, badges, bouton, entete_champ, separateur, texte, vider

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

    def __init__(self, titre: str, sous_titre: str, message: str = "") -> None:
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
        barre.setRange(0, 0)
        barre.setTextVisible(False)
        layout.addWidget(barre)
        if message:
            citation = texte(message, "mfAide")
            citation.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(citation)


class PageSelection(Page):
    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.corps.addWidget(texte(contenus.TITRE_SELECTION, "mfH2"))
        self.corps.addWidget(texte(contenus.INTRO_SELECTION))
        self.zone = QVBoxLayout()
        self.zone.setSpacing(8)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        self.compteur = texte("", "mfH3")
        self.compteur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compteur.setStyleSheet(f"color: {style.BLEU_FRANCE}; font-weight: bold;")
        self.bouton_analyser = bouton("Analyser ce site", "primaire", parcours.analyser_selection)
        self.pied_layout.addWidget(self.compteur)
        self.pied_layout.addWidget(self.bouton_analyser)

    def rafraichir(self) -> None:
        parcours = self.parcours
        analyse = parcours.analyse
        vider(self.zone)
        n = len(analyse.parcelles)
        if parcours.couche is None:
            self.zone.addWidget(texte(contenus.TUTORIEL))
            self.zone.addWidget(
                Encadre("info", "Aucune couche de parcelles", "Sélectionnez une couche de polygones dans le panneau Couches.")
            )
        else:
            self.zone.addWidget(texte(f"Couche : {parcours.couche.name()}", "mfAide"))
            self.zone.addWidget(texte(contenus.TUTORIEL if n == 0 else contenus.AIDE_ADJACENTE, "mfAide"))
        if n == 0:
            self.zone.addWidget(texte("Pas de couche sous la main ?", "mfAide"))
            self.zone.addWidget(bouton("Ajouter des parcelles d'exemple", "lien", parcours.ajouter_exemple))
        else:
            for parcelle in analyse.parcelles:
                ligne = QHBoxLayout()
                ligne.addWidget(texte(parcelle.libelle, "mfValeur"), 1)
                ligne.addWidget(texte(formater_surface(parcelle.surface_m2), "mfAide"))
                retirer = QPushButton("✕")
                retirer.setObjectName("mfRetirer")
                retirer.setToolTip(f"Retirer la parcelle {parcelle.libelle}")
                retirer.setAccessibleName(f"Retirer la parcelle {parcelle.libelle}")
                retirer.setCursor(Qt.CursorShape.PointingHandCursor)
                retirer.clicked.connect(lambda _=False, idu=parcelle.idu: parcours.retirer_parcelle(idu))
                ligne.addWidget(retirer)
                self.zone.addLayout(ligne)
            if analyse.problemes:
                self.zone.addWidget(Encadre("erreur", "", "\n".join(analyse.problemes)))
        self.compteur.setText(f"{pluriel(n, 'parcelle')} ajoutée{'s' if n > 1 else ''}" if n else "")
        self.compteur.setVisible(n > 0)
        self.bouton_analyser.setEnabled(analyse.valide)


class ChampSaisie(QWidget):
    """Champ obligatoire : choix vide par défaut, message d'erreur sous la liste."""

    def __init__(self, cle: str, parcours: Parcours) -> None:
        super().__init__()
        self.cle = cle
        self.parcours = parcours
        champ = CHAMPS_PAR_CLE[cle]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(entete_champ(champ.libelle, champ.aide))
        self.liste = self._liste(champ.libelle, champ.options)
        layout.addWidget(self.liste)
        # Pollution « Oui » : le type est demandé ensuite (PollutionField)
        self.type_pollution: Optional[QComboBox] = None
        self.libelle_type: Optional[QLabel] = None
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
        self.parcours.definir_reponse(self.cle, valeur)

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


class PageEtape(Page):
    """Une étape de qualification, dans l'ordre et avec les libellés de la page web."""

    def __init__(self, parcours: Parcours, etape: int) -> None:
        super().__init__(parcours)
        self.etape = etape
        titre, suivante, elements = contenus.ETAPES[etape]
        self.elements = elements
        self.stepper = Stepper()
        self.stepper.definir(etape, titre, suivante)
        self.corps.addWidget(self.stepper)
        self.zone_attente = QVBoxLayout()
        self.corps.addLayout(self.zone_attente)

        self.formulaire = QWidget()
        formulaire = QVBoxLayout(self.formulaire)
        formulaire.setContentsMargins(0, 4, 0, 0)
        formulaire.setSpacing(12)
        self.infos: dict[str, QVBoxLayout] = {}
        self.entetes_infos: dict[str, QLabel] = {}
        self.champs: dict[str, ChampSaisie] = {}
        for element in elements:
            if element == SEPARATEUR:
                formulaire.addWidget(separateur())
            elif isinstance(element, Info):
                bloc = QWidget()
                layout = QVBoxLayout(bloc)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(4)
                entete = entete_champ(element.libelle, element.aide + (f" {element.lien}" if element.lien else ""))
                layout.addWidget(entete)
                valeurs = QVBoxLayout()
                layout.addLayout(valeurs)
                self.infos[element.cle] = valeurs
                self.entetes_infos[element.cle] = entete.findChild(QLabel)
                formulaire.addWidget(bloc)
            elif isinstance(element, Saisie):
                champ = ChampSaisie(element.cle, parcours)
                champ.liste.currentIndexChanged.connect(lambda *_: self._masquer_bati())
                self.champs[element.cle] = champ
                formulaire.addWidget(champ)
        self.corps.addWidget(self.formulaire)
        self.corps.addStretch(1)

        self.zone_pied = QVBoxLayout()
        self.pied_layout.addLayout(self.zone_pied)
        ligne = QHBoxLayout()
        ligne.addWidget(bouton("Précédent", "secondaire", self._precedent))
        self.bouton_suivant = bouton("Suivant", "primaire", self._suivant)
        ligne.addWidget(self.bouton_suivant)
        self.pied_layout.addLayout(ligne)
        self._message_attente = random.choice(contenus.MESSAGES_CHARGEMENT)

    def _precedent(self) -> None:
        if self.etape == Etape.SITE_BATI:
            self.parcours.modifier_selection()
        else:
            self.parcours.aller_etape(self.etape - 1)

    def _champs_visibles(self) -> list[ChampSaisie]:
        return [c for c in self.champs.values() if not c.isHidden()]

    def _suivant(self) -> None:
        manquants = [c for c in self._champs_visibles() if not c.valeur()]
        for champ in self.champs.values():
            champ.montrer_erreur(champ in manquants)
        if manquants:
            self.defiler_vers(manquants[0])
            return
        if self.etape == Etape.SITE_BATI:
            self._normaliser_bati()
        if self.etape == Etape.RISQUES:
            self.parcours.evaluer()
        else:
            self.parcours.aller_etape(self.etape + 1)

    def _normaliser_bati(self) -> None:
        # « Pas de bâti » rend l'autre champ sans objet : aligné à l'envoi (normaliserBati)
        site = self.parcours.site
        if site is None:
            return
        cles = ("valeurArchitecturaleHistorique", "etatBatiInfrastructure")
        if any(site.reponses.get(c) == PAS_DE_BATI for c in cles):
            for cle in cles:
                site.definir_reponse(cle, PAS_DE_BATI)

    def _masquer_bati(self) -> None:
        site = self.parcours.site
        if site is None or "etatBatiInfrastructure" not in self.champs:
            return
        architecture = site.reponses.get("valeurArchitecturaleHistorique")
        etat = site.reponses.get("etatBatiInfrastructure")
        self.champs["etatBatiInfrastructure"].setVisible(architecture != PAS_DE_BATI)
        self.champs["valeurArchitecturaleHistorique"].setVisible(etat != PAS_DE_BATI or architecture == PAS_DE_BATI)

    def rafraichir(self) -> None:
        parcours = self.parcours
        site = parcours.site
        if site is None:
            return
        vider(self.zone_attente)
        donnees = site.enrichissement
        self.formulaire.setVisible(donnees is not None)
        if parcours.enrichissement_en_cours:
            self.zone_attente.addWidget(
                Chargement(contenus.TITRE_CHARGEMENT, contenus.SOUS_TITRE_CHARGEMENT, self._message_attente)
            )
        elif donnees is None and parcours.erreur_enrichissement is not None:
            erreur = parcours.erreur_enrichissement
            self.zone_attente.addWidget(Encadre("erreur", "Données non récupérées", erreur.message))
            if erreur.recuperable:
                self.zone_attente.addWidget(bouton("Réessayer", "secondaire", parcours.lancer_enrichissement))
        if donnees is not None:
            for cle, valeurs in self.infos.items():
                vider(valeurs)
                valeur = valeur_etape(cle, donnees, site.reponses)
                if cle == "parcelles":
                    multi = isinstance(valeur, list)
                    self.entetes_infos[cle].setText("Parcelles du site" if multi else "Identifiant parcelle")
                liste = valeur if isinstance(valeur, list) else [valeur]
                if not any(liste) or liste == [DONNEE_NON_ACCESSIBLE]:
                    valeurs.addWidget(badges([DONNEE_NON_ACCESSIBLE], "non-accessible"))
                else:
                    valeurs.addWidget(badges([v for v in liste if v]))
            for cle, champ in self.champs.items():
                champ.charger(site.reponses.get(cle, ""), donnees.get("siteReferencePollue") is True)
            self._masquer_bati()

        vider(self.zone_pied)
        if parcours.erreur_evaluation is not None:
            self.zone_pied.addWidget(Encadre("erreur", "Analyse impossible", parcours.erreur_evaluation.message))
        if parcours.evaluation_en_cours:
            self.zone_pied.addWidget(texte("Calcul en cours : analyse de la mutabilité de votre friche...", "mfAide"))
        self.bouton_suivant.setEnabled(donnees is not None and not parcours.evaluation_en_cours)
