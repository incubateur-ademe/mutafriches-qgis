"""État du parcours : utilisateur, envoi des sites CNIG, analyse par l'API Mutafriches."""

import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QDesktopServices

from ..carto.couches import (
    EMPRISE_FRANCE,
    ajouter_fond_osm,
    avancer_criteres_de_terrain,
    creer_couches,
    emprise_carte,
)
from ..core import reglages
from ..core.attributaire import (
    FICHIER_MODELE_CNIG,
    SiteAttributaire,
    Synthese,
    site_depuis_api,
    synthese,
)
from ..core.client_api import (
    URL_PRODUCTION,
    AnalyseInventaire,
    ErreurApi,
    ResultatSite,
    url_api,
)
from ..core.cnig import LectureCnig, lire_cnig
from ..core.declaration import DeclarationIntegrateur, ErreurDeclaration, origine_declaree, oublier
from . import contenus
from .accueil import Utilisateur, charger_utilisateur, coordonnees_verrouillees, enregistrer_utilisateur

# Page de l'interface web qui explique critères et sources. `source` et `ref` sont lus par son suivi
# d'événements (source_campagne, ADR-0012 de Mutafriches) : ses consultations depuis QGIS s'y comptent
CHEMIN_COMPRENDRE = "/comprendre-les-analyses?source=qgis&ref=tableau-de-bord"
# Nom d'objet de la page « Mutafriches » des options de QGIS (ui/options.py)
NOM_PAGE_OPTIONS = "mutafrichesOptions"
AVERTISSEMENT_API = (
    "Résultats calculés par l'API Mutafriches. Les critères tirés du fichier CNIG sont déclaratifs ; "
    "sans saisie, la mutabilité est calculée avec « Je ne sais pas » pour chaque critère manuel."
)


class Etape:
    ACCUEIL = 0
    IMPORT = 1
    RESULTATS = 2


class Parcours(QObject):
    change = pyqtSignal()

    def __init__(self, iface: QgisInterface, version: str = "") -> None:
        super().__init__()
        self.iface = iface
        self.version = version
        reglages.migrer_anciens_reglages()
        self.avancement: tuple[int, int] = (0, 0)
        self.erreur_api: ErreurApi | None = None
        self.echecs: list[str] = []
        self._analyse: AnalyseInventaire | None = None
        self._declaration: DeclarationIntegrateur | None = None
        self.declaration_en_cours = False
        self.erreurs_accueil: dict[str, str] = {}
        self.erreur_declaration = ""
        self.canvas = iface.mapCanvas()
        self.utilisateur: Utilisateur = charger_utilisateur()
        # L'accueil n'est proposé que tant que la déclaration est incomplète
        self.etape = Etape.IMPORT if self.utilisateur.valide else Etape.ACCUEIL
        if not self.utilisateur.valide and not self.utilisateur.erreurs_coordonnees():
            # Coordonnées d'une version où l'accord était facultatif : dire pourquoi l'accueil revient
            self.erreur_declaration = contenus.ACCORD_A_DONNER
        self.fichier: Path | None = None
        self.lecture: LectureCnig | None = None
        self.analyse_en_cours = False
        self.sites: list[SiteAttributaire] = []
        self.lignes_ecartees: list[str] = []
        self.synthese: Synthese | None = None
        self.avertissement = ""
        self.couche_mutabilite: QgsVectorLayer | None = None
        self.couche_qualification: QgsVectorLayer | None = None

    # --- Accueil ------------------------------------------------------------------------------

    def valider_accueil(self, utilisateur: Utilisateur) -> bool:
        """Enregistre la saisie et déclare aussitôt la structure à l'API."""
        self.erreurs_accueil = utilisateur.erreurs()
        self.erreur_declaration = ""
        if self.erreurs_accueil:
            self.change.emit()
            return False
        enregistrer_utilisateur(utilisateur)
        # Relu tel qu'enregistré (domaine ramené à son hôte) : même empreinte au prochain lancement
        self.utilisateur = charger_utilisateur()
        self._declarer(lambda _origine: self._aller_a_l_import(), self._declaration_refusee_a_l_accueil)
        return True

    def _aller_a_l_import(self) -> None:
        self.etape = Etape.IMPORT
        self.change.emit()

    def _declaration_refusee_a_l_accueil(self, erreur: ErreurDeclaration) -> None:
        self.erreur_declaration = erreur.message
        self.change.emit()

    @property
    def coordonnees_verrouillees(self) -> bool:
        return coordonnees_verrouillees(self.utilisateur)

    def modifier_utilisateur(self) -> None:
        # Possible tant que la structure n'est pas déclarée, ou après un refus d'accès de l'API
        if self.coordonnees_verrouillees:
            return
        self.erreurs_accueil = {}
        self.erreur_declaration = ""
        self.etape = Etape.ACCUEIL
        self.change.emit()

    def _declarer(self, suite: Callable[[str], None], echec: Callable[[ErreurDeclaration], None]) -> None:
        """Origine de la structure pour l'API courante : mémorisée, ou obtenue en la déclarant."""
        url = url_api()
        declaration = self.utilisateur.declaration()
        connue = origine_declaree(url, declaration)
        if connue:
            suite(connue)
            return

        def termine(origine: str, erreur: ErreurDeclaration | None) -> None:
            self._declaration = None
            self.declaration_en_cours = False
            if erreur is not None:
                echec(erreur)
            else:
                suite(origine)

        self.declaration_en_cours = True
        self._declaration = DeclarationIntegrateur(url, declaration, self.version, termine)
        self.change.emit()
        self._declaration.demarrer()

    # --- Étape 1 : fichier CNIG -------------------------------------------------------------

    def choisir_fichier(self, chemin: str) -> None:
        self.fichier = Path(chemin) if chemin else None
        self.lecture = lire_cnig(self.fichier) if self.fichier else None
        self.change.emit()

    def enregistrer_modele(self, chemin: str) -> Path | None:
        """Copie du modèle CNIG vide (colonnes seules), là où l'utilisateur le demande."""
        cible = Path(chemin)
        try:
            shutil.copyfile(FICHIER_MODELE_CNIG, cible)
        except OSError as erreur:
            # Dossier protégé ou disparu : un message, pas une trace Python
            self.iface.messageBar().pushCritical(
                "Mutafriches", f"Modèle de fichier non enregistré dans {cible.parent} : {erreur.strerror or erreur}."
            )
            return None
        self.iface.messageBar().pushSuccess("Mutafriches", f"Modèle de fichier enregistré : {cible}")
        return cible

    def preparer_carte(self) -> None:
        """À l'ouverture du panneau sur un projet vide : fond de carte, cadré sur la France."""
        if not reglages.FOND_OSM.value() or not ajouter_fond_osm():
            return
        # La carte ne prend la projection du projet qu'au tour d'événements suivant : cadrer après
        QTimer.singleShot(300, self._cadrer_france)

    def _cadrer_france(self) -> None:
        # Entre-temps l'utilisateur a pu obtenir des résultats : ne pas défaire leur cadrage
        if self.couche_mutabilite is not None:
            return
        vers_carte = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().crs(), QgsProject.instance()
        )
        self.canvas.setExtent(vers_carte.transformBoundingBox(QgsRectangle(*EMPRISE_FRANCE)))
        self.canvas.refresh()

    @property
    def pret_a_envoyer(self) -> bool:
        return self.lecture is not None and self.lecture.valide and not self.analyse_en_cours

    def reglages_modifies(self) -> None:
        """Appelé par la page d'options : rien n'y change les coordonnées, le panneau se redessine."""
        self.change.emit()

    def ouvrir_reglages(self) -> None:
        self.iface.showOptionsDialog(self.iface.mainWindow(), NOM_PAGE_OPTIONS)

    def envoyer(self) -> None:
        if not self.pret_a_envoyer or self.lecture is None:
            return
        # Informations d'une version où elles étaient facultatives : à compléter avant d'appeler l'API
        if not self.utilisateur.valide:
            self.erreurs_accueil = self.utilisateur.erreurs()
            # Coordonnées complètes d'une version où l'accord était facultatif : seule la case manque
            self.erreur_declaration = (
                contenus.ACCUEIL_A_COMPLETER if self.utilisateur.erreurs_coordonnees() else contenus.ACCORD_A_DONNER
            )
            self.etape = Etape.ACCUEIL
            self.change.emit()
            return
        self.analyse_en_cours = True
        self.erreur_api = None
        self.echecs = []
        self.avancement = (0, len(self.lecture.sites_ok))
        self.change.emit()
        self._declarer(self._analyser, self._declaration_refusee_a_l_envoi)

    def _analyser(self, origine: str) -> None:
        if not self.analyse_en_cours or self.lecture is None:
            return
        self._analyse = AnalyseInventaire(
            self.lecture.sites_ok,
            self._progression,
            self._analyse_terminee,
            origine,
            self.version,
        )
        self._analyse.demarrer()

    def _declaration_refusee_a_l_envoi(self, erreur: ErreurDeclaration) -> None:
        self.analyse_en_cours = False
        self.erreur_api = ErreurApi(f"{contenus.DECLARATION_REFUSEE} {erreur.message}", bloquante=True)
        self.change.emit()

    def annuler_analyse(self) -> None:
        if self._declaration is not None:
            self._declaration.annuler()
            self._declaration = None
            self.declaration_en_cours = False
        if self._analyse is not None:
            self._analyse.annuler()
            self._analyse = None
        if self.analyse_en_cours:
            self.analyse_en_cours = False
            self.change.emit()

    def _progression(self, traites: int, total: int) -> None:
        self.avancement = (traites, total)
        self.change.emit()

    def _analyse_terminee(self, resultats: list[ResultatSite], erreur: ErreurApi | None) -> None:
        self._analyse = None
        self.analyse_en_cours = False
        if self.lecture is None:
            return
        reussis = [r for r in resultats if r.ok]
        # Accès refusé ou API injoignable sans aucun résultat : on reste sur l'import, avec le motif
        if erreur is not None and not reussis:
            if erreur.acces_refuse:
                # Domaine révoqué ou registre vidé : la prochaine analyse redéclare
                oublier(url_api())
            self.erreur_api = erreur
            self.change.emit()
            return
        self.echecs = [f"{r.site.site_nom or r.site.site_id} : {r.erreur}" for r in resultats if not r.ok]
        if erreur is not None:
            self.echecs.append(f"Analyse interrompue : {erreur.message}")
        self.sites = [
            site_depuis_api(
                r.site.site_id,
                r.site.site_nom,
                r.site.parcelles,
                r.enrichissement or {},
                r.mutabilite or {},
                r.complementaires,
            )
            for r in reussis
        ]
        source = "API Mutafriches" + (" (environnement de test)" if reglages.url_de_test() else "")
        self._afficher_resultats(
            {"provenance": f"{source} · analyse du {date.today().strftime('%d/%m/%Y')}"}, AVERTISSEMENT_API
        )

    def _afficher_resultats(self, meta: dict[str, object], avertissement: str) -> None:
        if self.lecture is None:
            return
        self.lignes_ecartees = [
            f"ligne {s.ligne} : {s.site_nom or s.site_id or 'sans nom'}" for s in self.lecture.sites_ko
        ]
        self.avertissement = avertissement
        self.synthese = synthese(self.sites, meta)
        if not self.sites:
            # Un seul exemplaire de chaque motif : trois sites en échec ont souvent la même cause
            motifs = list(dict.fromkeys(echec.split(" : ", 1)[-1] for echec in self.echecs))
            self.erreur_api = ErreurApi(
                f"Aucun des {len(self.echecs)} sites n'a pu être analysé. " + " ".join(motifs[:2])
            )
            self.change.emit()
            return
        self.couche_mutabilite, self.couche_qualification = creer_couches(
            self.sites, self.synthese.code_insee or "inventaire"
        )
        self.etape = Etape.RESULTATS
        self.change.emit()
        self.zoomer()
        if self.attention:
            # Le tableau de bord ne liste plus ces sites : l'utilisateur doit savoir qu'il en manque
            n = len(self.attention)
            self.iface.messageBar().pushWarning(
                "Mutafriches",
                f"{n} site{'s' if n > 1 else ''} non analysé{'s' if n > 1 else ''} : "
                + " ; ".join(self.attention[:3])
                + (f" ; et {n - 3} autres" if n > 3 else ""),
            )

    # --- Étape 2 : résultats ------------------------------------------------------------------

    def zoomer(self) -> None:
        if self.couche_mutabilite is None:
            return
        self.canvas.setExtent(emprise_carte(self.couche_mutabilite, self.canvas.mapSettings().destinationCrs()))
        self.canvas.refresh()

    def mettre_en_avant(self, site: SiteAttributaire) -> None:
        """Sélectionne le site dans la couche de mutabilité et cadre la carte dessus."""
        couche = self.couche_mutabilite
        if couche is None:
            return
        identifiant = (site.site_id or site.cle).replace("'", "''")
        couche.selectByExpression(f"\"site_id\" = '{identifiant}'")
        if couche.selectedFeatureCount():
            self.canvas.zoomToSelected(couche)
            self.canvas.zoomScale(max(self.canvas.scale() * 1.6, 2000))
        self.iface.setActiveLayer(couche)

    def ouvrir_table_mutabilite(self) -> None:
        if self.couche_mutabilite is not None:
            self.iface.showAttributeTable(self.couche_mutabilite)

    def ouvrir_table_qualification(self) -> None:
        if self.couche_qualification is not None:
            self.iface.showAttributeTable(self.couche_qualification)

    def url_comprendre_resultats(self) -> str:
        # Une API de test publique a sa propre interface ; un serveur local renvoie à la production
        test = reglages.url_de_test()
        return (test if test.startswith("https://") else URL_PRODUCTION) + CHEMIN_COMPRENDRE

    def comprendre_resultats(self) -> None:
        QDesktopServices.openUrl(QUrl(self.url_comprendre_resultats()))

    def ameliorer_fiabilite(self) -> None:
        """Ouvre la table de qualification, où les critères de terrain à renseigner sont colorés."""
        if self.couche_qualification is None:
            return
        # Sans cela, les critères à renseigner sont hors champ, à droite d'une quarantaine de colonnes
        avancer_criteres_de_terrain(self.couche_qualification)
        self.iface.showAttributeTable(self.couche_qualification)
        self.iface.messageBar().pushInfo("Mutafriches", contenus.AIDE_AMELIORER_FIABILITE)

    @property
    def attention(self) -> list[str]:
        """Sites non analysés : lignes écartées du fichier et échecs de l'API."""
        return self.lignes_ecartees + self.echecs

    def nouvelle_analyse(self) -> None:
        self.annuler_analyse()
        self.erreur_api = None
        self.echecs = []
        self.fichier = None
        self.lecture = None
        self.sites = []
        self.lignes_ecartees = []
        self.synthese = None
        self.etape = Etape.IMPORT
        self.change.emit()

    def nettoyer(self) -> None:
        self.annuler_analyse()
