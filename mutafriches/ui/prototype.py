"""Pages du prototype : envoi des sites au format CNIG, puis résultats territoriaux."""

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..carto.couches import COULEURS_USAGES
from ..core.attributaire import ORDRE_USAGES, PROFILS_ECART, Synthese, libelle_usage
from ..core.client_api import DEMONSTRATION, LIBELLES_ENVIRONNEMENTS, PRODUCTION, mode_developpeur
from ..core.cnig import SiteCnig
from ..core.referentiel import formater_note
from . import contenus, style
from .pages import Chargement, Page, pluriel
from .parcours import Parcours
from .graphiques import anneau_avec_legende, tableau
from .widgets import Encadre, badge, bouton, entete_champ, separateur, texte, vider

MAX_LIGNES_AFFICHEES = 40


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
        self.corps.addWidget(separateur())
        self.corps.addWidget(texte(contenus.AIDE_EXEMPLE_CNIG, "mfAide"))
        self.corps.addWidget(bouton(contenus.BOUTON_MODELE_CNIG, "secondaire", self._telecharger_modele))
        self.utilisateur = texte("", "mfAide")
        ligne = QHBoxLayout()
        ligne.addWidget(self.utilisateur, 1)
        ligne.addWidget(bouton("Modifier", "lien", parcours.modifier_utilisateur))
        self.pied_layout.addLayout(ligne)
        self.bouton_envoyer = bouton("Envoyer mes sites", "primaire", parcours.envoyer)
        self.pied_layout.addWidget(self.bouton_envoyer)
        self.bouton_mode = bouton(
            "", "lien", lambda: parcours.changer_environnement(DEMONSTRATION if parcours.reel else PRODUCTION)
        )
        self.pied_layout.addWidget(self.bouton_mode, 0, Qt.AlignmentFlag.AlignCenter)
        # Réservé à l'équipe (mode développeur) : production, staging ou démonstration
        self.environnements = QComboBox()
        self.environnements.setAccessibleName("Environnement de l'API")
        for cle, libelle in LIBELLES_ENVIRONNEMENTS.items():
            self.environnements.addItem(f"Environnement : {libelle}", cle)
        self.environnements.currentIndexChanged.connect(
            lambda *_: parcours.changer_environnement(str(self.environnements.currentData()))
        )
        self.pied_layout.addWidget(self.environnements)

    def _telecharger_modele(self) -> None:
        chemin, _ = QFileDialog.getSaveFileName(
            self.contenu, "Enregistrer le fichier exemple CNIG", "modele-friches-cnig.csv", "CSV (*.csv)"
        )
        if chemin:
            self.parcours.enregistrer_modele(chemin)

    def rafraichir(self) -> None:
        parcours = self.parcours
        lecture = parcours.lecture
        self.fichier.blockSignals(True)
        self.fichier.setFilePath(str(parcours.fichier) if parcours.fichier else "")
        self.fichier.blockSignals(False)
        vider(self.zone)
        if parcours.analyse_en_cours and lecture is not None:
            traites, total = parcours.avancement
            self.zone.addWidget(
                Chargement(
                    f"Analyse en cours : {traites} / {total} sites"
                    if parcours.reel
                    else f"Analyse de {pluriel(len(lecture.sites_ok), 'site')} en cours...",
                    contenus.SOUS_TITRE_ANALYSE_REELLE if parcours.reel else contenus.SOUS_TITRE_CHARGEMENT,
                    contenus.MESSAGE_ANALYSE_LOT,
                    parcours.avancement if parcours.reel else None,
                )
            )
            self.zone.addWidget(bouton("Annuler l'analyse", "secondaire", parcours.annuler_analyse))
        elif parcours.erreur_api is not None:
            self.zone.addWidget(Encadre("erreur", "Analyse impossible", parcours.erreur_api.message))
            if parcours.reel:
                self.zone.addWidget(texte(contenus.AIDE_ERREUR_API, "mfAide"))
                self.zone.addWidget(
                    bouton(
                        "Passer en mode démonstration",
                        "secondaire",
                        lambda: parcours.changer_environnement(DEMONSTRATION),
                    )
                )
        elif lecture is not None and lecture.bloquants:
            self.zone.addWidget(
                Encadre(
                    "erreur", f"Fichier refusé : {lecture.fichier}", "\n".join(p.message for p in lecture.bloquants)
                )
            )
            self.zone.addWidget(texte(contenus.AIDE_ERREUR_CNIG, "mfAide"))
        elif lecture is not None:
            ok, ko = lecture.sites_ok, lecture.sites_ko
            if ko:
                self.zone.addWidget(
                    Encadre(
                        "avertissement" if ok else "erreur",
                        f"{pluriel(len(ok), 'site')} prêt{'s' if len(ok) > 1 else ''}, {pluriel(len(ko), 'ligne')} en erreur",
                        contenus.AIDE_ERREUR_CNIG,
                    )
                )
            else:
                self.zone.addWidget(
                    Encadre(
                        "succes",
                        f"{pluriel(len(ok), 'site')} lu{'s' if len(ok) > 1 else ''} dans {lecture.fichier}",
                        "\n".join(p.message for p in lecture.problemes),
                    )
                )
            # Contrôle ligne à ligne, lignes en erreur en tête
            for site in (ko + ok)[:MAX_LIGNES_AFFICHEES]:
                self.zone.addWidget(LigneCnig(site))
            if len(lecture.sites) > MAX_LIGNES_AFFICHEES:
                self.zone.addWidget(texte(f"et {len(lecture.sites) - MAX_LIGNES_AFFICHEES} autres lignes", "mfAide"))
        utilisateur = parcours.utilisateur
        self.utilisateur.setText(f"{utilisateur.structure} · {utilisateur.mail}" if utilisateur.complet else "")
        self.utilisateur.setVisible(utilisateur.complet)
        n = len(lecture.sites_ok) if lecture is not None and lecture.valide else 0
        self.bouton_envoyer.setText(f"Envoyer mes {n} sites" if n > 1 else "Envoyer mes sites")
        self.bouton_envoyer.setEnabled(parcours.pret_a_envoyer)
        self.bouton_mode.setText(
            "Passer en mode démonstration (données figées)"
            if parcours.reel
            else "Passer en mode réel (API Mutafriches)"
        )
        developpeur = mode_developpeur()
        self.bouton_mode.setVisible(not developpeur and not parcours.analyse_en_cours)
        self.environnements.blockSignals(True)
        self.environnements.setCurrentIndex(self.environnements.findData(parcours.environnement))
        self.environnements.blockSignals(False)
        self.environnements.setVisible(developpeur and not parcours.analyse_en_cours)


class LigneCnig(QFrame):
    """Une ligne du fichier : nom, identifiant, parcelles, et OK ou la liste de ses erreurs."""

    def __init__(self, site: SiteCnig) -> None:
        super().__init__()
        self.setObjectName("mfLigneSite")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        entete = QHBoxLayout()
        entete.setSpacing(8)
        entete.addWidget(texte(site.site_nom or site.site_id or f"Ligne {site.ligne}", "mfValeur"), 1)
        entete.addWidget(
            badge("OK" if site.ok else "KO", "automatique" if site.ok else "alerte"), 0, Qt.AlignmentFlag.AlignTop
        )
        layout.addLayout(entete)
        details = [f"ligne {site.ligne}", site.site_id or "sans identifiant", pluriel(len(site.parcelles), "parcelle")]
        layout.addWidget(texte(" · ".join(details), "mfAide"))
        for erreur in site.erreurs:
            layout.addWidget(texte(erreur, "mfErreurChamp"))


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
    """Tableau de bord territorial, entièrement dans le panneau."""

    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.zone = QVBoxLayout()
        self.zone.setSpacing(10)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        ligne = QHBoxLayout()
        ligne.addWidget(bouton("Table mutabilité", "secondaire", parcours.ouvrir_table_mutabilite))
        ligne.addWidget(bouton("Table qualification", "secondaire", parcours.ouvrir_table_qualification))
        self.pied_layout.addLayout(ligne)
        self.pied_layout.addWidget(
            bouton("Analyser un autre inventaire", "lien", parcours.nouvelle_analyse), 0, Qt.AlignmentFlag.AlignCenter
        )

    def _titre(self, contenu: str, aide: str = "") -> None:
        self.zone.addWidget(separateur())
        self.zone.addWidget(texte(contenu, "mfH3"))
        if aide:
            self.zone.addWidget(texte(aide, "mfAide"))

    def rafraichir(self) -> None:
        parcours = self.parcours
        s: Synthese | None = parcours.synthese
        vider(self.zone)
        if s is None:
            return
        self.zone.addWidget(texte(f"{s.commune} ({s.code_insee})", "mfSurTitre"))
        self.zone.addWidget(texte("Tableau de bord territorial", "mfH2"))
        self.zone.addWidget(texte(s.provenance, "mfAide"))

        # 1 et 2 : nombre de sites, fiabilité
        grille = QGridLayout()
        grille.setSpacing(8)
        grille.addWidget(
            Chiffre("Sites analysés", str(s.nombre_sites), f"{len(s.sites_a_qualifier)} sans saisie terrain"), 0, 0
        )
        grille.addWidget(
            Chiffre(
                "Fiabilité moyenne",
                f"{formater_note(s.fiabilite_moyenne)} / 10",
                f"{s.par_fiabilite.get('Très fiable', 0)} très fiables sur {s.nombre_sites}",
            ),
            0,
            1,
        )
        self.zone.addLayout(grille)

        # 3 : jauges par usage le plus compatible
        self._titre("Usage le plus compatible", "Nombre de sites dont c'est l'usage prioritaire.")
        for usage in ORDRE_USAGES:
            self.zone.addWidget(
                Barre(libelle_usage(usage), s.par_usage.get(usage, 0), s.nombre_sites, COULEURS_USAGES[usage])
            )

        # 4 : répartition
        self._titre("Répartition des usages les plus compatibles")
        serie_usages = [(libelle_usage(u), s.par_usage.get(u, 0), COULEURS_USAGES[u]) for u in ORDRE_USAGES]
        self.zone.addWidget(anneau_avec_legende(serie_usages, str(s.nombre_sites), "sites"))

        # 5 : profils
        self._titre(
            "Profils de sites",
            "Écart entre le meilleur et le moins bon usage d'un même site. Grille de lecture du prototype, à valider.",
        )
        lignes = []
        for seuil, libelle, lecture in PROFILS_ECART:
            nombre = s.par_profil.get(libelle, 0)
            borne = "30 pts et plus" if seuil == float("inf") else f"< {int(seuil)} pts"
            lignes.append(
                [
                    libelle,
                    borne,
                    str(nombre),
                    f"{round(100 * nombre / s.nombre_sites) if s.nombre_sites else 0} %",
                    lecture,
                ]
            )
        self.zone.addWidget(tableau(["Profil", "Écart", "Sites", "Part", "Lecture"], lignes, [3, 2, 1, 1, 4]))

        # 6 : sites à forte compatibilité, cliquables
        self._titre(
            f"Sites à forte compatibilité ({len(s.sites_forte_compatibilite)})",
            "Indice de l'usage prioritaire supérieur ou égal à 70 %. Cliquer un site le sélectionne et cadre la carte.",
        )
        for site in s.sites_forte_compatibilite:
            ligne = QHBoxLayout()
            lien = bouton(site.nom, "lien", lambda _=False, site=site: parcours.mettre_en_avant(site))
            lien.setAccessibleName(f"Voir sur la carte : {site.nom}")
            ligne.addWidget(lien, 1)
            ligne.addWidget(
                badge(f"{libelle_usage(site.usage_prioritaire)} · {round(site.indice_max)} %", "tag"),
                0,
                Qt.AlignmentFlag.AlignTop,
            )
            self.zone.addLayout(ligne)

        # 7 : sites nécessitant une attention (lignes écartées, non retrouvés, peu fiables)
        peu_fiables = [
            x
            for x in s.sites_a_qualifier
            if x.fiabilite_niveau in ("Moyennement fiable", "Peu fiable", "Très peu fiable")
        ]
        attention = parcours.attention + [
            f"{x.nom} : {x.fiabilite_niveau.lower()}, qualification à compléter" for x in peu_fiables
        ]
        self._titre("Sites nécessitant votre attention")
        if attention:
            n = len(attention)
            self.zone.addWidget(
                Encadre(
                    "erreur",
                    f"{pluriel(n, 'site')} à reprendre",
                    "\n".join(attention[:6]) + (f"\net {n - 6} autres" if n > 6 else ""),
                )
            )
        else:
            self.zone.addWidget(
                Encadre(
                    "succes",
                    "Aucun site à reprendre",
                    "Toutes les lignes ont été analysées et aucune n'est peu fiable.",
                )
            )
        self.zone.addWidget(
            texte(parcours.avertissement if parcours.reel else f"Démonstration : {parcours.avertissement}", "mfAide")
        )
