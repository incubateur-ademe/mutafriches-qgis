"""Pages du prototype : envoi des sites au format CNIG, puis résultats territoriaux."""

from functools import partial
from pathlib import Path

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import QStandardPaths, Qt
from qgis.PyQt.QtGui import QResizeEvent
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..carto.couches import COULEURS_USAGES
from ..core.attributaire import ORDRE_USAGES, PROFILS_ECART, Synthese, libelle_usage
from ..core.cnig import SiteCnig
from ..core.declaration import TYPES_STRUCTURE
from ..core.referentiel import formater_note
from . import contenus, style
from .accueil import Utilisateur
from .graphiques import tableau
from .pages import Chargement, Page, pluriel
from .parcours import Parcours
from .widgets import (
    ActionAide,
    CaseACocher,
    Encadre,
    badge,
    bouton,
    entete_champ,
    lien,
    separateur,
    texte,
    texte_riche,
    vider,
)

MAX_LIGNES_AFFICHEES = 40


class PageAccueil(Page):
    """Déclaration de la structure : demandée une fois, dans le panneau, avant l'envoi des sites."""

    def __init__(self, parcours: Parcours) -> None:
        super().__init__(parcours)
        self.corps.addWidget(texte(contenus.TITRE_ACCUEIL, "mfTitre"))
        self.corps.addWidget(texte(contenus.INTRO_ACCUEIL))
        self.corps.addSpacing(6)
        self.erreurs: dict[str, QLabel] = {}
        # Ordre et libellés du formulaire de déclaration web
        self.structure = self._champ("structure", contenus.LIBELLE_STRUCTURE)
        self.type_structure = QComboBox()
        self.type_structure.addItem(contenus.CHOIX_VIDE, "")
        for cle, libelle in TYPES_STRUCTURE.items():
            self.type_structure.addItem(libelle, cle)
        self._ajouter("type_structure", contenus.LIBELLE_TYPE_STRUCTURE, self.type_structure)
        self.domaine = self._champ("domaine", contenus.LIBELLE_DOMAINE, contenus.AIDE_DOMAINE)
        # Prénom et nom côte à côte : deux champs courts, une ligne de moins dans un panneau étroit
        identite = QHBoxLayout()
        identite.setSpacing(8)
        self.prenom = self._champ("prenom", contenus.LIBELLE_PRENOM, ligne=identite)
        self.nom = self._champ("nom", contenus.LIBELLE_NOM, ligne=identite)
        self.corps.addLayout(identite)
        self.mail = self._champ("mail", contenus.LIBELLE_MAIL, contenus.AIDE_MAIL)
        # Sous l'e-mail, décochée par défaut et obligatoire : l'accueil ne se valide pas sans elle
        self.accepte_contact = CaseACocher(contenus.LIBELLE_ACCEPTE_CONTACT, contenus.AIDE_ACCEPTE_CONTACT)
        self.corps.addWidget(self.accepte_contact)
        erreur_accord = texte("", "mfErreurChamp")
        erreur_accord.setVisible(False)
        self.corps.addWidget(erreur_accord)
        self.erreurs["accepte_contact"] = erreur_accord
        self.accepte_contact.case.toggled.connect(lambda *_: erreur_accord.setVisible(False))
        self.erreur = Encadre("erreur")
        self.erreur.setVisible(False)
        self.corps.addWidget(self.erreur)
        self.corps.addSpacing(6)
        # Sous le formulaire, et non au pied du panneau : la suite se lit dans la continuité des champs
        self.corps.addWidget(texte(contenus.ACCUEIL_NON_MODIFIABLE, "mfAide"))
        self.suivant = bouton("Suivant", "primaire", self._valider)
        self.corps.addWidget(self.suivant)
        self.corps.addWidget(
            texte_riche(
                contenus.MENTION_ACCUEIL.format(
                    lien=lien(contenus.LIBELLE_CONFIDENTIALITE, contenus.URL_CONFIDENTIALITE)
                ),
                "mfAide",
            )
        )
        self.corps.addStretch(1)

    def _champ(self, cle: str, libelle: str, aide: str = "", ligne: QHBoxLayout | None = None) -> QLineEdit:
        champ = QLineEdit()
        self._ajouter(cle, libelle, champ, aide, ligne)
        champ.returnPressed.connect(self._valider)
        return champ

    def _ajouter(
        self, cle: str, libelle: str, champ: QWidget, aide: str = "", ligne: QHBoxLayout | None = None
    ) -> None:
        etiquette = texte(libelle)
        etiquette.setStyleSheet("font-weight: bold;")
        champ.setAccessibleName(libelle)
        etiquette.setBuddy(champ)
        colonne = QVBoxLayout()
        colonne.setSpacing(4)
        colonne.addWidget(etiquette)
        if aide:
            colonne.addWidget(texte(aide, "mfAide"))
        colonne.addWidget(champ)
        erreur = texte("", "mfErreurChamp")
        erreur.setVisible(False)
        colonne.addWidget(erreur)
        self.erreurs[cle] = erreur
        # Le champ corrigé perd son erreur tout de suite ; « Suivant » refait le contrôle complet
        signal = champ.currentIndexChanged if isinstance(champ, QComboBox) else champ.textChanged
        signal.connect(lambda *_: erreur.setVisible(False))
        # « ligne or self.corps » ne convient pas : une mise en page encore vide est fausse en Python
        if ligne is None:
            self.corps.addLayout(colonne)
        else:
            ligne.addLayout(colonne, 1)

    def saisie(self) -> Utilisateur:
        return Utilisateur(
            prenom=self.prenom.text(),
            nom=self.nom.text(),
            structure=self.structure.text(),
            type_structure=str(self.type_structure.currentData() or ""),
            domaine=self.domaine.text(),
            mail=self.mail.text(),
            accepte_contact=self.accepte_contact.case.isChecked(),
        )

    def _valider(self) -> None:
        if not self.parcours.declaration_en_cours:
            self.parcours.valider_accueil(self.saisie())

    def rafraichir(self) -> None:
        parcours = self.parcours
        utilisateur = parcours.utilisateur
        # Structure déjà déclarée, accord encore à donner : seules la case et la validation restent
        verrou = parcours.coordonnees_verrouillees
        # Pendant la déclaration ou après un refus, la saisie en cours reste affichée
        saisie_en_cours = bool(parcours.declaration_en_cours or parcours.erreurs_accueil or parcours.erreur_declaration)
        if verrou or not saisie_en_cours:
            self.prenom.setText(utilisateur.prenom)
            self.nom.setText(utilisateur.nom)
            self.structure.setText(utilisateur.structure)
            position = self.type_structure.findData(utilisateur.type_structure)
            self.type_structure.setCurrentIndex(max(position, 0))
            self.domaine.setText(utilisateur.domaine)
            self.mail.setText(utilisateur.mail)
        if not saisie_en_cours or parcours.erreur_declaration == contenus.ACCORD_A_DONNER:
            self.accepte_contact.case.setChecked(utilisateur.accepte_contact)
        for champ in (self.structure, self.type_structure, self.domaine, self.prenom, self.nom, self.mail):
            champ.setEnabled(not verrou)
        for cle, etiquette in self.erreurs.items():
            message = parcours.erreurs_accueil.get(cle, "")
            etiquette.setText(message)
            etiquette.setVisible(bool(message))
        self.erreur.definir("erreur", "", parcours.erreur_declaration)
        self.erreur.setVisible(bool(parcours.erreur_declaration))
        self.suivant.setText(contenus.ENVOI_DECLARATION if parcours.declaration_en_cours else "Suivant")
        self.suivant.setEnabled(not parcours.declaration_en_cours)


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
        self.lien_utilisateur = bouton("Modifier", "lien", parcours.modifier_utilisateur)
        ligne.addWidget(self.lien_utilisateur)
        self.pied_layout.addLayout(ligne)

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
        if parcours.declaration_en_cours:
            self.zone.addWidget(Chargement("Déclaration de votre structure en cours...", ""))
        elif parcours.analyse_en_cours and lecture is not None:
            traites, total = parcours.avancement
            self.zone.addWidget(
                Chargement(
                    f"Analyse en cours : {traites} / {total} sites",
                    contenus.SOUS_TITRE_ANALYSE,
                    avancement=parcours.avancement,
                )
            )
            self.zone.addWidget(bouton("Annuler l'analyse", "secondaire", parcours.annuler_analyse))
        elif parcours.erreur_api is not None:
            self.zone.addWidget(Encadre("erreur", "Analyse impossible", parcours.erreur_api.message))
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
            # Un encadré par cas, chacun seulement s'il a des sites : les KO d'abord, à corriger
            if ko:
                self.zone.addWidget(
                    Encadre(
                        "erreur", f"{pluriel(len(ko), 'site')} KO (comportant des erreurs)", contenus.AIDE_ERREUR_CNIG
                    )
                )
            if ok:
                remarques = "\n".join(p.message for p in lecture.problemes)
                self.zone.addWidget(
                    Encadre("succes", f"{pluriel(len(ok), 'site')} OK", remarques or contenus.AIDE_SITES_OK)
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
        self.utilisateur.setText(utilisateur.resume)
        # Structure déclarée : ses coordonnées ne se modifient plus, le lien disparaît (ADR-0006)
        self.lien_utilisateur.setVisible(not parcours.coordonnees_verrouillees)
        n = len(lecture.sites_ok) if lecture is not None and lecture.valide else 0
        self.bouton_envoyer.setText(f"Analyser mes {n} sites" if n > 1 else "Analyser mes sites")
        self.bouton_envoyer.setEnabled(parcours.pret_a_envoyer)
        # Avec des sites KO, l'envoi se décide sous la liste des erreurs ; pendant l'analyse, seul « Annuler » reste
        avec_ko = lecture is not None and not lecture.bloquants and bool(lecture.sites_ko)
        self.bouton_envoyer.setVisible(not parcours.analyse_en_cours and not avec_ko)


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
        # Dès le haut du tableau de bord : la démarche de l'algorithme se lit avant les chiffres
        comprendre = bouton(contenus.LIEN_COMPRENDRE_RESULTATS, "secondaire", parcours.comprendre_resultats)
        comprendre.setToolTip(contenus.AIDE_COMPRENDRE_RESULTATS)
        self.zone.addWidget(comprendre)

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
        self.zone.addWidget(texte(parcours.avertissement, "mfAide"))
