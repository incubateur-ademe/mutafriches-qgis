"""Écran des résultats et fenêtres de détail, calqués sur la page web /resultats."""

from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QMouseEvent, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.recapitulatif import construire_detail_usage, construire_recapitulatif, deriver_raccordement_eau
from ..core.referentiel import (
    IMAGES_USAGES,
    MESSAGE_USAGE_EXCLU,
    MESSAGE_ZONE_EXCLUSION_ENR,
    USAGES,
    badge_potentiel,
    formater_note,
    formater_surface,
)
from . import contenus, style
from .pages import Page, pluriel
from .parcours import Etape, Parcours
from .widgets import BoutonAide, Encadre, FlowLayout, badge, bouton, texte, vider

DOSSIER_IMAGES = Path(__file__).resolve().parent.parent / "icons" / "usages"
Json = dict[str, object]


def image_usage(usage: str, taille: int) -> QLabel:
    etiquette = QLabel()
    pixmap = QPixmap(str(DOSSIER_IMAGES / IMAGES_USAGES.get(usage, "")))
    if not pixmap.isNull():
        etiquette.setPixmap(
            pixmap.scaled(taille, taille, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
    etiquette.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return etiquette


def badge_resultat(resultat: Json) -> QLabel:
    config = badge_potentiel(float(resultat["indiceMutabilite"]), bool(resultat.get("exclu")))  # type: ignore[arg-type]
    etiquette = QLabel(config.libelle)
    etiquette.setStyleSheet(
        f"background: {config.fond}; color: {config.texte}; border-radius: 4px; padding: 2px 8px;"
        " font-size: 11px; font-weight: bold;"
    )
    etiquette.setSizePolicy(etiquette.sizePolicy().horizontalPolicy(), etiquette.sizePolicy().verticalPolicy())
    return etiquette


def titre_avec_aide(contenu: str, nom: str, aide: str) -> QWidget:
    ligne = QWidget()
    layout = QHBoxLayout(ligne)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    titre = texte(contenu, nom)
    # Titre court sur une ligne : avec le retour à la ligne, Qt le comprime à côté du « ? »
    titre.setWordWrap(False)
    layout.addWidget(titre)
    layout.addWidget(BoutonAide(aide, contenu), 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addStretch(1)
    return ligne


def departement(identifiant: str) -> str:
    return identifiant[:3] if identifiant.startswith("97") else identifiant[:2]


class Fenetre(QDialog):
    """Fenêtre modale défilante, avec la feuille de style du panneau."""

    def __init__(self, parent: QWidget, titre: str, largeur: int = 640) -> None:
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.resize(largeur, 640)
        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        cadre = QWidget()
        cadre.setObjectName("mfRacine")
        cadre.setStyleSheet(style.feuille_de_style())
        racine.addWidget(cadre)
        layout = QVBoxLayout(cadre)
        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenu = QWidget()
        # Même nom d'objet que les pages du panneau : fond blanc, quel que soit le thème système
        contenu.setObjectName("mfPages")
        self.corps = QVBoxLayout(contenu)
        self.corps.setSpacing(10)
        defilement.setWidget(contenu)
        layout.addWidget(defilement, 1)
        layout.addWidget(bouton("Fermer", "secondaire", self.accept))


def tableau(colonnes: list[str], largeurs: list[int]) -> QGridLayout:
    grille = QGridLayout()
    grille.setHorizontalSpacing(10)
    grille.setVerticalSpacing(6)
    for i, (colonne, largeur) in enumerate(zip(colonnes, largeurs)):
        entete = texte(colonne)
        entete.setStyleSheet("font-weight: bold;")
        grille.addWidget(entete, 0, i)
        grille.setColumnStretch(i, largeur)
    return grille


class DialogueRecapitulatif(Fenetre):
    """Récapitulatif du site (SiteRecapModal / RecapTable)."""

    def __init__(self, parent: QWidget, enrichissement: Json, complementaires: dict[str, str]) -> None:
        super().__init__(parent, "Récapitulatif du site", 720)
        self.corps.addWidget(texte("Récapitulatif du site", "mfH2"))
        grille = tableau(["Critère", "Valeur", "Saisie", "Source"], [5, 4, 2, 2])
        ligne = 1
        for section in construire_recapitulatif(enrichissement, complementaires):
            titre = texte(section.titre, "mfH3")
            titre.setStyleSheet(f"font-weight: bold; color: {style.BLEU_FRANCE}; padding-top: 6px;")
            grille.addWidget(titre, ligne, 0, 1, 4)
            ligne += 1
            for critere in section.lignes:
                libelle = critere.libelle
                if critere.informatif:
                    libelle += "\nDonnée informative, hors calcul"
                if critere.mention:
                    libelle += f"\n{critere.mention}"
                grille.addWidget(texte(libelle), ligne, 0)
                valeur = texte(critere.valeur, selectionnable=True)
                valeur.setStyleSheet("font-weight: bold;")
                grille.addWidget(valeur, ligne, 1)
                grille.addWidget(badge(critere.saisie, critere.saisie.lower()), ligne, 2, Qt.AlignmentFlag.AlignCenter)
                if critere.source:
                    grille.addWidget(badge(critere.source, "source"), ligne, 3, Qt.AlignmentFlag.AlignCenter)
                ligne += 1
        self.corps.addLayout(grille)
        self.corps.addStretch(1)


class DialogueDetailUsage(Fenetre):
    """Détail d'un usage (UsageDetailModal) : compatibilité, avantages / contraintes, critères."""

    def __init__(self, parent: QWidget, resultat: Json, enrichissement: Json, complementaires: dict[str, str]) -> None:
        usage = str(resultat["usage"])
        super().__init__(parent, USAGES.get(usage, usage), 720)
        corps = self.corps
        ligne_badge = QHBoxLayout()
        ligne_badge.addWidget(badge_resultat(resultat))
        ligne_badge.addStretch(1)
        corps.addLayout(ligne_badge)
        titre = QHBoxLayout()
        titre.addWidget(image_usage(usage, 32))
        titre.addWidget(texte(USAGES.get(usage, usage), "mfH2"), 1)
        corps.addLayout(titre)
        if resultat.get("exclu"):
            corps.addWidget(texte(f"{MESSAGE_USAGE_EXCLU}. Les critères bloquants sont signalés dans le tableau."))
        else:
            compatibilite = texte(
                f"{round(float(resultat['indiceMutabilite']))} % de compatibilité   "  # type: ignore[arg-type]
                "Indice = avantages / (avantages + contraintes)"
            )
            corps.addWidget(compatibilite)
        zaer = enrichissement.get("zaer")
        if isinstance(zaer, dict) and zaer.get("enZoneExclusion"):
            corps.addWidget(Encadre("avertissement", "", MESSAGE_ZONE_EXCLUSION_ENR))
        if not resultat.get("exclu"):
            corps.addWidget(self._barre_ratio(float(resultat.get("avantages") or 0), float(resultat.get("contraintes") or 0)))  # type: ignore[arg-type]
        grille = tableau(["Critère", "Valeur", "Pondération", "Impact"], [5, 4, 2, 2])
        ligne = 1
        for titre_section, lignes in construire_detail_usage(resultat, enrichissement, complementaires):
            entete = texte(titre_section, "mfH3")
            entete.setStyleSheet(f"font-weight: bold; color: {style.BLEU_FRANCE}; padding-top: 6px;")
            grille.addWidget(entete, ligne, 0, 1, 4)
            ligne += 1
            for detail in lignes:
                grille.addWidget(texte(detail.libelle), ligne, 0)
                valeur = texte(detail.valeur)
                valeur.setStyleSheet("font-weight: bold;")
                grille.addWidget(valeur, ligne, 1)
                grille.addWidget(texte(f"{detail.poids:.1f}"), ligne, 2, Qt.AlignmentFlag.AlignCenter)
                grille.addWidget(badge(detail.impact.libelle, detail.impact.niveau), ligne, 3, Qt.AlignmentFlag.AlignCenter)
                ligne += 1
        corps.addLayout(grille)
        corps.addStretch(1)

    @staticmethod
    def _barre_ratio(avantages: float, contraintes: float) -> QWidget:
        bloc = QWidget()
        layout = QVBoxLayout(bloc)
        layout.setContentsMargins(0, 0, 0, 0)
        barre = QHBoxLayout()
        barre.setSpacing(0)
        total = avantages + contraintes
        part = round(avantages / total * 100) if total else 0
        for couleur, poids in ((style.AVANTAGES, part), (style.CONTRAINTES, 100 - part)):
            segment = QFrame()
            segment.setFixedHeight(12)
            segment.setStyleSheet(f"background: {couleur}; border: none;")
            barre.addWidget(segment, max(poids, 1))
        layout.addLayout(barre)
        legende = QHBoxLayout()
        legende.addWidget(texte(f"Avantages : {avantages:.1f}", "mfAide"))
        legende.addStretch(1)
        legende.addWidget(texte(f"Contraintes : {contraintes:.1f}", "mfAide"))
        layout.addLayout(legende)
        return bloc


class CartePodium(QFrame):
    """Carte d'un usage du podium (PodiumCard) : badge, illustration, titre, étiquettes."""

    def __init__(self, resultat: Json) -> None:
        super().__init__()
        self.setObjectName("mfCartePodium")
        usage = str(resultat["usage"])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)
        ligne = QHBoxLayout()
        ligne.addWidget(badge_resultat(resultat))
        ligne.addStretch(1)
        layout.addLayout(ligne)
        layout.addWidget(image_usage(usage, 64))
        titre = texte(USAGES.get(usage, usage))
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titre.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(titre)
        etiquettes = QWidget()
        flux = FlowLayout(etiquettes)
        for tag in resultat.get("tags") or []:  # type: ignore[union-attr]
            flux.addWidget(badge(str(tag), "tag"))
        layout.addWidget(etiquettes)


def rang(n: int) -> str:
    return "1er" if n == 1 else f"{n}e"


class LigneTableau(QFrame):
    """Ligne du tableau « Tous les usages » : infobulle de synthèse, détail au clic."""

    detail = pyqtSignal(str)

    def __init__(self, resultat: Json) -> None:
        super().__init__()
        self.setObjectName("mfLigneTableau")
        self.usage = str(resultat["usage"])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        libelle = USAGES.get(self.usage, self.usage)
        indice = float(resultat["indiceMutabilite"])  # type: ignore[arg-type]
        exclu = bool(resultat.get("exclu"))
        config = badge_potentiel(indice, exclu)
        grille = QGridLayout(self)
        grille.setContentsMargins(4, 8, 4, 8)
        grille.setHorizontalSpacing(8)
        grille.setVerticalSpacing(4)
        position = texte(rang(int(resultat["rang"])))  # type: ignore[arg-type]
        position.setStyleSheet("font-weight: bold;")
        position.setFixedWidth(28)
        grille.addWidget(position, 0, 0)
        nom = texte(libelle)
        nom.setStyleSheet("font-weight: bold;")
        grille.addWidget(nom, 0, 1)
        grille.addWidget(badge_resultat(resultat), 0, 2, Qt.AlignmentFlag.AlignRight)
        if exclu:
            grille.addWidget(texte(MESSAGE_USAGE_EXCLU, "mfAide"), 1, 1, 1, 2)
        else:
            barre = QHBoxLayout()
            barre.setSpacing(6)
            plein = QFrame()
            plein.setFixedHeight(8)
            plein.setStyleSheet(f"background: {config.fond}; border-radius: 4px;")
            vide = QWidget()
            barre.addWidget(plein, max(round(indice), 1))
            barre.addWidget(vide, max(100 - round(indice), 1))
            pourcentage = texte(f"{round(indice)}%")
            pourcentage.setStyleSheet("font-weight: bold;")
            barre.addWidget(pourcentage)
            grille.addLayout(barre, 1, 1, 1, 2)
        grille.setColumnStretch(1, 1)
        self.setAccessibleName(f"{libelle} : {config.libelle.lower()}, voir le détail")
        self.setToolTip(self._infobulle(resultat, libelle, indice, config.libelle))

    @staticmethod
    def _infobulle(resultat: Json, libelle: str, indice: float, potentiel: str) -> str:
        lignes = [f"<b>{libelle}</b>"]
        if resultat.get("exclu"):
            lignes.append(MESSAGE_USAGE_EXCLU)
        else:
            lignes.append(f"{round(indice)} % de compatibilité · potentiel {potentiel.lower()}")
            lignes.append(
                f"Avantages : {float(resultat.get('avantages') or 0):.1f} · "  # type: ignore[arg-type]
                f"Contraintes : {float(resultat.get('contraintes') or 0):.1f}"  # type: ignore[arg-type]
            )
        tags = resultat.get("tags") or []
        if tags:
            lignes.append("Points forts : " + ", ".join(str(t) for t in tags))  # type: ignore[union-attr]
        lignes.append("<i>Cliquer pour voir le détail des critères</i>")
        return "<p style='max-width: 320px'>" + "<br>".join(lignes) + "</p>"

    def mousePressEvent(self, evenement: QMouseEvent) -> None:
        if evenement.button() == Qt.MouseButton.LeftButton:
            self.detail.emit(self.usage)

    def keyPressEvent(self, evenement) -> None:  # type: ignore[no-untyped-def]
        if evenement.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.detail.emit(self.usage)
        else:
            super().keyPressEvent(evenement)


class PageResultats(Page):
    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.corps.addWidget(bouton("‹  Modifier les données", "secondaire", lambda: parcours.aller_etape(Etape.SITE_BATI)))
        self.corps.addWidget(titre_avec_aide("Analyse de mutabilité", "mfH2", contenus.AIDE_ANALYSE))
        self.zone = QVBoxLayout()
        self.zone.setSpacing(12)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        ligne = QHBoxLayout()
        ligne.addWidget(bouton("Précédent", "secondaire", lambda: parcours.aller_etape(Etape.RISQUES)))
        ligne.addWidget(bouton("Nouvelle analyse", "primaire", parcours.nouvelle_analyse))
        self.pied_layout.addLayout(ligne)

    def _complementaires(self) -> dict[str, str]:
        site = self.parcours.site
        assert site is not None and site.enrichissement is not None
        reponses = site.reponses_completes()
        surface_bati = site.enrichissement.get("surfaceBati")
        reponses["raccordementEau"] = deriver_raccordement_eau(
            float(surface_bati) if isinstance(surface_bati, (int, float)) else None
        )
        return reponses

    def _resultat(self, usage: str) -> Optional[Json]:
        site = self.parcours.site
        resultats = site.evaluation["resultats"] if site and site.evaluation else []
        return next((r for r in resultats if r["usage"] == usage), None)  # type: ignore[union-attr]

    def _detail(self, usage: str) -> None:
        site = self.parcours.site
        resultat = self._resultat(usage)
        if site is not None and site.enrichissement is not None and resultat is not None:
            DialogueDetailUsage(self.contenu, resultat, site.enrichissement, self._complementaires()).exec()

    def _recapitulatif(self) -> None:
        site = self.parcours.site
        if site is not None and site.enrichissement is not None:
            DialogueRecapitulatif(self.contenu, site.enrichissement, self._complementaires()).exec()

    def rafraichir(self) -> None:
        parcours = self.parcours
        site = parcours.site
        vider(self.zone)
        if site is None or site.evaluation is None or site.enrichissement is None:
            return
        fiabilite = site.fiabilite() or {}
        note = float(fiabilite.get("note", 0))  # type: ignore[arg-type]
        self.zone.addWidget(titre_avec_aide(f"Indice de fiabilité : {formater_note(note)}/10", "mfH3", contenus.AIDE_FIABILITE))
        self.zone.addWidget(self._bandeau_site(site.enrichissement, len(site.parcelles), site.surface_m2))

        self.zone.addWidget(titre_avec_aide("Usages les plus compatibles", "mfH3", contenus.AIDE_USAGES))
        resultats = sorted(site.evaluation["resultats"], key=lambda r: r["rang"])  # type: ignore[arg-type, index]
        # Le podium ne propose jamais un usage exclu (getUsagesPodium)
        for resultat in [r for r in resultats if not r.get("exclu")][:3]:
            self.zone.addWidget(CartePodium(resultat))

        self.zone.addWidget(texte("Tous les usages", "mfH3"))
        self.zone.addWidget(texte("Survolez une ligne pour un aperçu, cliquez pour le détail.", "mfAide"))
        table = QWidget()
        lignes = QVBoxLayout(table)
        lignes.setContentsMargins(0, 0, 0, 0)
        lignes.setSpacing(0)
        for resultat in resultats:
            ligne = LigneTableau(resultat)
            ligne.detail.connect(self._detail)
            lignes.addWidget(ligne)
        self.zone.addWidget(table)

        simulation = site.simulation
        if parcours.version_algorithme and simulation is not None:
            notes = [f"Démonstration : indices figés (algorithme {parcours.version_algorithme}) sur données fictives."]
            if simulation.note:
                notes.append(simulation.note)
            if simulation.ecarts:
                notes.append(
                    f"Réponse figée la plus proche de votre saisie ({pluriel(simulation.ecarts, 'réponse')} "
                    f"différente{'s' if simulation.ecarts > 1 else ''})."
                )
            self.zone.addWidget(texte(" ".join(notes), "mfAide"))

    def _bandeau_site(self, enrichissement: Json, nombre: int, surface: float) -> QFrame:
        cadre = QFrame()
        cadre.setObjectName("mfBandeauSite")
        layout = QVBoxLayout(cadre)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        commune = str(enrichissement.get("commune") or "")
        code = departement(str(enrichissement.get("identifiantParcelle") or ""))
        titre = f"Site de {commune} ({code})" if commune and code.isalnum() else "Récapitulatif du site"
        entete = texte(titre)
        entete.setStyleSheet("font-weight: bold;")
        layout.addWidget(entete)
        layout.addWidget(texte(f"{pluriel(nombre, 'parcelle')}  |  {formater_surface(surface)}"))
        layout.addWidget(bouton("voir récapitulatif du site", "lien", self._recapitulatif))
        return cadre
