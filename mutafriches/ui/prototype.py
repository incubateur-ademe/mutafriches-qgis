"""Pages du prototype : envoi des sites au format CNIG, puis résultats territoriaux."""

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ..carto.couches import COULEURS_USAGES
from ..core.attributaire import NIVEAUX_FIABILITE, ORDRE_USAGES, Synthese, libelle_usage
from ..core.referentiel import formater_note
from . import contenus, style
from .pages import Chargement, Page, pluriel
from .parcours import Parcours
from .widgets import Encadre, badge, bouton, entete_champ, separateur, texte, vider


class PageAccueil(Page):
    """Qui est l'utilisateur : demandé une fois, dans le panneau, avant l'envoi des sites."""

    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.corps.addWidget(texte(contenus.TITRE_ACCUEIL, "mfTitre"))
        self.corps.addWidget(texte(contenus.INTRO_ACCUEIL))
        self.corps.addSpacing(6)
        self.structure = self._champ("Votre structure", "Collectivité, agence, bureau d'études…")
        self.mail = self._champ("Votre mail", "prenom.nom@exemple.fr")
        self.erreur = texte("Renseignez votre structure et une adresse mail valide.", "mfErreurChamp")
        self.erreur.setVisible(False)
        self.corps.addWidget(self.erreur)
        # Une case sans texte et un libellé à part : QCheckBox ne sait pas passer à la ligne
        self.consentement = QCheckBox()
        self.consentement.setAccessibleName(contenus.CONSENTEMENT_ACCUEIL)
        ligne = QHBoxLayout()
        ligne.setSpacing(8)
        ligne.addWidget(self.consentement, 0, Qt.AlignmentFlag.AlignTop)
        libelle = texte(contenus.CONSENTEMENT_ACCUEIL)
        libelle.setBuddy(self.consentement)
        ligne.addWidget(libelle, 1)
        self.corps.addLayout(ligne)
        self.corps.addStretch(1)
        self.pied_layout.addWidget(bouton("Suivant", "primaire", self._valider))

    def _champ(self, libelle: str, aide: str) -> QLineEdit:
        etiquette = texte(libelle)
        etiquette.setStyleSheet("font-weight: bold;")
        champ = QLineEdit()
        champ.setPlaceholderText(aide)
        champ.setAccessibleName(libelle)
        etiquette.setBuddy(champ)
        self.corps.addWidget(etiquette)
        self.corps.addWidget(champ)
        return champ

    def _valider(self) -> None:
        ok = self.parcours.valider_accueil(self.structure.text(), self.mail.text(), self.consentement.isChecked())
        self.erreur.setVisible(not ok)

    def rafraichir(self) -> None:
        utilisateur = self.parcours.utilisateur
        self.structure.setText(utilisateur.structure)
        self.mail.setText(utilisateur.mail)
        self.consentement.setChecked(utilisateur.consentement)
        self.erreur.setVisible(False)


class PageImport(Page):
    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.corps.addWidget(texte(contenus.TITRE_IMPORT, "mfH2"))
        self.corps.addWidget(texte(contenus.INTRO_IMPORT))
        self.corps.addWidget(entete_champ("Fichier de sites (CSV ou GeoJSON)", contenus.AIDE_FICHIER))
        self.fichier = QgsFileWidget()
        self.fichier.setFilter("Fichiers CNIG Friches (*.csv *.geojson *.json)")
        self.fichier.setDialogTitle("Choisir le fichier de sites au format CNIG")
        self.fichier.fileChanged.connect(parcours.choisir_fichier)
        self.corps.addWidget(self.fichier)
        self.zone = QVBoxLayout()
        self.zone.setSpacing(8)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        self.utilisateur = texte("", "mfAide")
        ligne = QHBoxLayout()
        ligne.addWidget(self.utilisateur, 1)
        ligne.addWidget(bouton("Modifier", "lien", parcours.modifier_utilisateur))
        self.pied_layout.addLayout(ligne)
        self.bouton_envoyer = bouton("Envoyer mes sites", "primaire", parcours.envoyer)
        self.pied_layout.addWidget(self.bouton_envoyer)

    def rafraichir(self) -> None:
        parcours = self.parcours
        lecture = parcours.lecture
        self.fichier.blockSignals(True)
        self.fichier.setFilePath(str(parcours.fichier) if parcours.fichier else "")
        self.fichier.blockSignals(False)
        vider(self.zone)
        if parcours.analyse_en_cours and lecture is not None:
            self.zone.addWidget(
                Chargement(
                    f"Analyse de {pluriel(len(lecture.sites), 'site')} en cours...",
                    contenus.SOUS_TITRE_CHARGEMENT,
                    contenus.MESSAGE_ANALYSE_LOT,
                )
            )
        elif lecture is None:
            self.zone.addWidget(texte(contenus.AIDE_EXEMPLE_CNIG, "mfAide"))
            self.zone.addWidget(bouton(contenus.LIEN_EXEMPLE_CNIG, "lien", parcours.utiliser_exemple))
            self.zone.addWidget(bouton(contenus.LIEN_EXEMPLE_ERRONE, "lien", parcours.utiliser_exemple_errone))
        elif lecture.valide:
            self.zone.addWidget(
                Encadre(
                    "succes",
                    f"{pluriel(len(lecture.sites), 'site')} lu{'s' if len(lecture.sites) > 1 else ''} dans {lecture.fichier}",
                    "\n".join(p.message for p in lecture.problemes),
                )
            )
        else:
            bloquants = lecture.bloquants
            self.zone.addWidget(
                Encadre(
                    "erreur",
                    f"Fichier refusé : {pluriel(len(bloquants), 'erreur')}",
                    "\n".join((f"Ligne {p.ligne} : " if p.ligne else "") + p.message for p in bloquants[:12])
                    + ("\n…" if len(bloquants) > 12 else ""),
                )
            )
            self.zone.addWidget(texte(contenus.AIDE_ERREUR_CNIG, "mfAide"))
        utilisateur = parcours.utilisateur
        self.utilisateur.setText(f"{utilisateur.structure} · {utilisateur.mail}" if utilisateur.complet else "")
        self.utilisateur.setVisible(utilisateur.complet)
        n = len(lecture.sites) if lecture is not None and lecture.valide else 0
        self.bouton_envoyer.setText(f"Envoyer mes {n} sites" if n > 1 else "Envoyer mes sites")
        self.bouton_envoyer.setEnabled(parcours.pret_a_envoyer)


class Chiffre(QFrame):
    def __init__(self, libelle: str, valeur: str, detail: str = "") -> None:
        super().__init__()
        self.setObjectName("mfChiffre")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        layout.addWidget(texte(libelle, "mfAide"))
        layout.addWidget(texte(valeur, "mfNomSite"))
        if detail:
            layout.addWidget(texte(detail, "mfAide"))


class Barre(QWidget):
    """Barre horizontale proportionnelle, pour une répartition lisible sans graphique."""

    def __init__(self, libelle: str, nombre: int, total: int, couleur: str) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(2)
        layout.addWidget(texte(libelle), 0, 0, 1, 2)
        piste = QFrame()
        piste.setFixedHeight(10)
        piste.setStyleSheet(f"background: {style.FOND_GRIS}; border: none;")
        remplissage = QFrame(piste)
        remplissage.setStyleSheet(f"background: {couleur}; border: none;")
        self._piste, self._remplissage, self._part = piste, remplissage, (nombre / total if total else 0)
        layout.addWidget(piste, 1, 0)
        valeur = texte(f"{nombre} ({round(100 * self._part)} %)", "mfAide")
        valeur.setMinimumWidth(64)
        layout.addWidget(valeur, 1, 1)

    def resizeEvent(self, evenement) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(evenement)
        self._remplissage.setGeometry(0, 0, int(self._piste.width() * self._part), self._piste.height())


class PageResultats(Page):
    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.zone = QVBoxLayout()
        self.zone.setSpacing(10)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        self.pied_layout.addWidget(bouton("Ouvrir le tableau de bord territorial", "primaire", parcours.ouvrir_dashboard))
        ligne = QHBoxLayout()
        ligne.addWidget(bouton("Table mutabilité", "secondaire", parcours.ouvrir_table_mutabilite))
        ligne.addWidget(bouton("Table qualification", "secondaire", parcours.ouvrir_table_qualification))
        self.pied_layout.addLayout(ligne)
        ligne2 = QHBoxLayout()
        ligne2.addWidget(bouton("Zoomer sur les sites", "secondaire", parcours.zoomer))
        ligne2.addWidget(bouton("Nouvelle analyse", "secondaire", parcours.nouvelle_analyse))
        self.pied_layout.addLayout(ligne2)

    def rafraichir(self) -> None:
        parcours = self.parcours
        s: Synthese | None = parcours.synthese
        vider(self.zone)
        if s is None:
            return
        self.zone.addWidget(texte(f"{s.commune} ({s.code_insee})", "mfSurTitre"))
        self.zone.addWidget(texte(f"{pluriel(s.nombre_sites, 'site')} analysé{'s' if s.nombre_sites > 1 else ''}", "mfH2"))
        if parcours.non_retrouves:
            n = len(parcours.non_retrouves)
            self.zone.addWidget(
                Encadre(
                    "avertissement",
                    f"{pluriel(n, 'site')} du fichier non retrouvé{'s' if n > 1 else ''} dans la table",
                    "Prototype : seuls les sites déjà présents dans la table attributaire de Montereau-Fault-Yonne ont des résultats. "
                    + ", ".join(parcours.non_retrouves[:5])
                    + ("…" if n > 5 else ""),
                )
            )
        dominant = max(s.par_usage.items(), key=lambda kv: kv[1])[0] if s.nombre_sites else None
        grille = QGridLayout()
        grille.setSpacing(8)
        grille.addWidget(Chiffre("Usage qui ressort le plus", libelle_usage(dominant), f"{s.par_usage.get(dominant or '', 0)} sites"), 0, 0)
        grille.addWidget(Chiffre("Fiabilité moyenne", f"{formater_note(s.fiabilite_moyenne)} / 10", f"{s.par_fiabilite.get('Très fiable', 0)} très fiables"), 0, 1)
        grille.addWidget(Chiffre("Forte compatibilité", str(len(s.sites_forte_compatibilite)), "indice ≥ 70 %"), 1, 0)
        grille.addWidget(Chiffre("À qualifier", str(len(s.sites_a_qualifier)), "sans saisie terrain"), 1, 1)
        self.zone.addLayout(grille)

        self.zone.addWidget(texte("Usage le plus compatible", "mfH3"))
        for usage in ORDRE_USAGES:
            nombre = s.par_usage.get(usage, 0)
            if nombre:
                self.zone.addWidget(Barre(libelle_usage(usage), nombre, s.nombre_sites, COULEURS_USAGES[usage]))
        self.zone.addWidget(separateur())
        self.zone.addWidget(texte("Fiabilité des résultats", "mfH3"))
        couleurs = {"Très fiable": style.SUCCES, "Fiable": "#27a658", "Moyennement fiable": "#c3992a", "Peu fiable": style.AVERTISSEMENT, "Très peu fiable": style.ERREUR}
        for niveau in NIVEAUX_FIABILITE:
            nombre = s.par_fiabilite.get(niveau, 0)
            if nombre:
                self.zone.addWidget(Barre(niveau, nombre, s.nombre_sites, couleurs[niveau]))
        self.zone.addWidget(separateur())
        self.zone.addWidget(texte("Sites à forte compatibilité", "mfH3"))
        for site in s.sites_forte_compatibilite[:8]:
            ligne = QHBoxLayout()
            ligne.addWidget(texte(site.nom, "mfValeur"), 1)
            ligne.addWidget(badge(f"{libelle_usage(site.usage_prioritaire)} · {round(site.indice_max)} %", "tag"), 0, Qt.AlignmentFlag.AlignTop)
            self.zone.addLayout(ligne)
        if len(s.sites_forte_compatibilite) > 8:
            self.zone.addWidget(texte(f"et {len(s.sites_forte_compatibilite) - 8} autres sites, voir le tableau de bord", "mfAide"))
        self.zone.addWidget(texte(f"Démonstration : table attributaire figée le {s.date_table}, algorithme {s.version_algorithme}. {parcours.avertissement}", "mfAide"))
