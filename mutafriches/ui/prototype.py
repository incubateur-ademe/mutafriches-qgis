"""Pages du prototype : envoi des sites au format CNIG, puis résultats territoriaux."""

from functools import partial
from pathlib import Path

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtGui import QResizeEvent
from qgis.PyQt.QtWidgets import (
    QCheckBox,
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
from ..core.cnig import SiteCnig
from ..core.referentiel import formater_note
from . import contenus, style
from .graphiques import tableau
from .pages import Chargement, Page, pluriel
from .parcours import Parcours
from .widgets import ActionAide, Encadre, badge, bouton, entete_champ, lien, separateur, texte, texte_riche, vider

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
        self.corps.addSpacing(6)
        # Sous le formulaire, et non au pied du panneau : la suite se lit dans la continuité des champs
        self.corps.addWidget(bouton("Suivant", "primaire", self._valider))
        self.corps.addStretch(1)

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
        self.corps.addWidget(
            texte_riche(
                contenus.INTRO_IMPORT.format(standard=lien(contenus.LIBELLE_STANDARD_CNIG, contenus.URL_STANDARD_CNIG))
            )
        )
        self.corps.addWidget(
            entete_champ(
                "Fichier de sites (CSV ou GeoJSON)",
                contenus.AIDE_FICHIER,
                action=(contenus.LIEN_MODELE_CNIG, self._telecharger_modele),
                aide_accolee=True,
            )
        )
        self.fichier = QgsFileWidget()
        self.fichier.setFilter("Fichiers CNIG Friches (*.csv *.geojson *.json)")
        self.fichier.setDialogTitle("Choisir le fichier de sites au format CNIG")
        self.fichier.fileChanged.connect(parcours.choisir_fichier)
        self.corps.addWidget(self.fichier)
        # Juste sous le champ : l'envoi est la suite immédiate du choix du fichier
        self.bouton_envoyer = bouton("Analyser mes sites", "primaire", parcours.envoyer)
        self.corps.addWidget(self.bouton_envoyer)
        self.zone = QVBoxLayout()
        self.zone.setSpacing(8)
        self.corps.addLayout(self.zone)
        self.corps.addStretch(1)
        self.utilisateur = texte("", "mfAide")
        ligne = QHBoxLayout()
        ligne.addWidget(self.utilisateur, 1)
        ligne.addWidget(bouton("Modifier", "lien", parcours.modifier_utilisateur))
        self.pied_layout.addLayout(ligne)
        # Démonstration, staging et autres réglages : page « Mutafriches » des options de QGIS.
        # Sans bandeau ni lien, ce rappel est le seul signe que l'envoi ne part pas vers l'API.
        self.rappel_demonstration = texte(contenus.RAPPEL_DEMONSTRATION, "mfAide")
        self.pied_layout.addWidget(self.rappel_demonstration)

    def _telecharger_modele(self) -> None:
        # Dossier de départ explicite : sans lui la fenêtre s'ouvre à la racine du disque, en lecture seule
        dossier = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(Path.home())
        chemin, _ = QFileDialog.getSaveFileName(
            self.contenu,
            "Enregistrer le modèle de fichier CNIG",
            str(Path(dossier) / "modele-friches-cnig.csv"),
            "CSV (*.csv)",
        )
        if chemin:
            self.parcours.enregistrer_modele(chemin)

    def _recharger(self) -> None:
        # Même fichier, relu sur le disque après correction
        if self.parcours.fichier is not None:
            self.parcours.choisir_fichier(str(self.parcours.fichier))

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
                    contenus.SOUS_TITRE_ANALYSE,
                    avancement=parcours.avancement if parcours.reel else None,
                )
            )
            self.zone.addWidget(bouton("Annuler l'analyse", "secondaire", parcours.annuler_analyse))
        elif parcours.erreur_api is not None:
            self.zone.addWidget(Encadre("erreur", "Analyse impossible", parcours.erreur_api.message))
            if parcours.reel:
                # L'aide dépend de la cause : accès à l'API, ou sites que l'API n'a pas su traiter
                aide = contenus.AIDE_ERREUR_API if parcours.erreur_api.bloquante else contenus.AIDE_AUCUN_SITE
                self.zone.addWidget(texte(aide, "mfAide"))
        elif lecture is not None and lecture.bloquants:
            self.zone.addWidget(
                Encadre(
                    "erreur", f"Fichier refusé : {lecture.fichier}", "\n".join(p.message for p in lecture.bloquants)
                )
            )
            self.zone.addWidget(texte(contenus.AIDE_ERREUR_CNIG, "mfAide"))
            self.zone.addWidget(bouton("Charger de nouveau le fichier", "secondaire", self._recharger))
        elif lecture is not None:
            ok, ko = lecture.sites_ok, lecture.sites_ko
            if ko:
                self.zone.addWidget(
                    Encadre(
                        "avertissement" if ok else "erreur",
                        f"{pluriel(len(ok), 'site')} OK, {pluriel(len(ko), 'site')} KO (comportant des erreurs)",
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
            if ko:
                # Sous la liste des erreurs : poursuivre avec les sites valides, ou corriger et recharger
                analyser = bouton(
                    f"Analyser {'les ' + str(len(ok)) + ' sites' if len(ok) > 1 else 'le site'} OK",
                    "primaire",
                    parcours.envoyer,
                )
                analyser.setEnabled(parcours.pret_a_envoyer)
                self.zone.addWidget(analyser)
                self.zone.addWidget(bouton("Charger de nouveau le fichier", "secondaire", self._recharger))
        utilisateur = parcours.utilisateur
        self.utilisateur.setText(f"{utilisateur.structure} · {utilisateur.mail}" if utilisateur.complet else "")
        self.utilisateur.setVisible(utilisateur.complet)
        n = len(lecture.sites_ok) if lecture is not None and lecture.valide else 0
        self.bouton_envoyer.setText(f"Analyser mes {n} sites" if n > 1 else "Analyser mes sites")
        self.bouton_envoyer.setEnabled(parcours.pret_a_envoyer)
        # Avec des sites KO, l'envoi se décide sous la liste des erreurs ; pendant l'analyse, seul « Annuler » reste
        avec_ko = lecture is not None and not lecture.bloquants and bool(lecture.sites_ko)
        self.bouton_envoyer.setVisible(not parcours.analyse_en_cours and not avec_ko)
        self.rappel_demonstration.setVisible(not parcours.reel)


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
    """Chiffre clé du tableau de bord, avec au besoin un lien d'action sous la valeur."""

    def __init__(self, libelle: str, valeur: str, action: ActionAide | None = None) -> None:
        super().__init__()
        self.setObjectName("mfChiffre")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        layout.addWidget(texte(libelle, "mfAide"))
        layout.addWidget(texte(valeur, "mfNomSite"))
        if action is not None:
            layout.addWidget(bouton(action[0], "lien", action[1]), 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)


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

    def resizeEvent(self, evenement: QResizeEvent) -> None:
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
        # Pied fixe : les tables restent à portée quel que soit le défilement
        self.pied_layout.addWidget(bouton("Voir table de mutabilité", "primaire", parcours.ouvrir_table_mutabilite))
        self.pied_layout.addWidget(
            bouton("Voir table de qualification", "secondaire", parcours.ouvrir_table_qualification)
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
        self.zone.addWidget(texte("Tableau de bord territorial", "mfH2"))

        # Nombre de sites, fiabilité et son levier d'amélioration
        grille = QGridLayout()
        grille.setSpacing(8)
        grille.addWidget(Chiffre("Sites analysés", str(s.nombre_sites)), 0, 0)
        grille.addWidget(
            Chiffre(
                "Fiabilité moyenne",
                f"{formater_note(s.fiabilite_moyenne)} / 10",
                (contenus.LIEN_AMELIORER_FIABILITE, parcours.ameliorer_fiabilite),
            ),
            0,
            1,
        )
        self.zone.addLayout(grille)

        # Jauges par usage le plus compatible
        self._titre(contenus.TITRE_REPARTITION, contenus.AIDE_REPARTITION)
        for usage in ORDRE_USAGES:
            self.zone.addWidget(
                Barre(libelle_usage(usage), s.par_usage.get(usage, 0), s.nombre_sites, COULEURS_USAGES[usage])
            )

        # Sites à forte compatibilité, cliquables
        self._titre(
            f"{contenus.TITRE_FORTE_COMPATIBILITE} ({len(s.sites_forte_compatibilite)})",
            contenus.AIDE_FORTE_COMPATIBILITE,
        )
        for site in s.sites_forte_compatibilite:
            ligne = QHBoxLayout()
            lien_site = bouton(site.nom, "lien", partial(parcours.mettre_en_avant, site))
            lien_site.setAccessibleName(f"Voir sur la carte : {site.nom}")
            ligne.addWidget(lien_site, 1)
            ligne.addWidget(
                badge(f"{libelle_usage(site.usage_prioritaire)} · {round(site.indice_max)} %", "tag"),
                0,
                Qt.AlignmentFlag.AlignTop,
            )
            self.zone.addLayout(ligne)

        # Profils, du plus contrasté au plus plat
        self._titre(contenus.TITRE_PROFILS, contenus.AIDE_PROFILS)
        lignes = []
        for seuil, libelle, lecture in reversed(PROFILS_ECART):
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
        self.zone.addWidget(
            texte(parcours.avertissement if parcours.reel else f"Démonstration : {parcours.avertissement}", "mfAide")
        )
