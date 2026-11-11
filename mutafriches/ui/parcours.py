"""État du parcours : utilisateur, envoi des sites CNIG, analyse par l'API ou table figée."""

import shutil
from datetime import date
from pathlib import Path
from typing import Optional

from qgis.core import QgsProject, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

from ..carto.couches import creer_couches, emprise_carte
from ..core.attributaire import (
    FICHIER_MODELE_CNIG,
    SiteAttributaire,
    Synthese,
    apparier,
    charger_table,
    site_depuis_api,
    synthese,
)
from ..core.client_api import (
    DEMONSTRATION,
    LIBELLES_ENVIRONNEMENTS,
    PRODUCTION,
    AnalyseInventaire,
    ErreurApi,
    ResultatSite,
    definir_environnement_api,
    environnement_api,
)
from ..core.cnig import LectureCnig, lire_cnig
from .accueil import Utilisateur, charger_utilisateur, enregistrer_utilisateur

# Attente simulée en mode démonstration
DELAI_ANALYSE_MS = 2500
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
        self.environnement = environnement_api()
        self._couches: list[str] = []
        self.avancement: tuple[int, int] = (0, 0)
        self.erreur_api: Optional[ErreurApi] = None
        self.echecs: list[str] = []
        self._analyse: Optional[AnalyseInventaire] = None
        self.canvas = iface.mapCanvas()
        self.utilisateur: Utilisateur = charger_utilisateur()
        # L'accueil n'est demandé qu'une fois : ensuite le panneau s'ouvre sur l'envoi des sites
        self.etape = Etape.IMPORT if self.utilisateur.complet else Etape.ACCUEIL
        self.fichier: Optional[Path] = None
        self.lecture: Optional[LectureCnig] = None
        self.analyse_en_cours = False
        self.sites: list[SiteAttributaire] = []
        self.non_retrouves: list[str] = []
        self.lignes_ecartees: list[str] = []
        self.synthese: Optional[Synthese] = None
        self.avertissement = ""
        self.couche_mutabilite: Optional[QgsVectorLayer] = None
        self.couche_qualification: Optional[QgsVectorLayer] = None
        self._timer: Optional[QTimer] = None

    # --- Accueil ------------------------------------------------------------------------------

    def valider_accueil(self, structure: str, mail: str, consentement: bool) -> bool:
        utilisateur = Utilisateur(structure, mail, consentement)
        if not utilisateur.complet:
            return False
        self.utilisateur = utilisateur
        enregistrer_utilisateur(utilisateur)
        self.etape = Etape.IMPORT
        self.change.emit()
        return True

    def modifier_utilisateur(self) -> None:
        self.etape = Etape.ACCUEIL
        self.change.emit()

    # --- Étape 1 : fichier CNIG -------------------------------------------------------------

    def choisir_fichier(self, chemin: str) -> None:
        self.fichier = Path(chemin) if chemin else None
        self.lecture = lire_cnig(self.fichier) if self.fichier else None
        self.change.emit()

    def enregistrer_modele(self, chemin: str) -> Path:
        """Copie du modèle CNIG à remplir, là où l'utilisateur le demande."""
        cible = Path(chemin)
        shutil.copyfile(FICHIER_MODELE_CNIG, cible)
        return cible

    @property
    def pret_a_envoyer(self) -> bool:
        return self.lecture is not None and self.lecture.valide and not self.analyse_en_cours

    @property
    def reel(self) -> bool:
        return self.environnement != DEMONSTRATION

    def changer_environnement(self, environnement: str) -> None:
        """Bascule production, staging ou démonstration, en repartant d'un panneau vide."""
        if environnement not in LIBELLES_ENVIRONNEMENTS or environnement == self.environnement:
            return
        self.annuler_analyse()
        self.environnement = environnement
        definir_environnement_api(environnement)
        # Jamais de résultats d'un environnement affichés sous le bandeau d'un autre
        self._retirer_couches()
        self.sites = []
        self.synthese = None
        self.non_retrouves = []
        self.lignes_ecartees = []
        self.echecs = []
        self.erreur_api = None
        if self.etape == Etape.RESULTATS:
            self.etape = Etape.IMPORT
        self.change.emit()

    def changer_mode(self, mode: str) -> None:
        self.changer_environnement(DEMONSTRATION if mode == "demo" else PRODUCTION)

    def _retirer_couches(self) -> None:
        projet = QgsProject.instance()
        for identifiant in self._couches:
            if projet.mapLayer(identifiant) is not None:
                projet.removeMapLayer(identifiant)
        self._couches = []
        self.couche_mutabilite = None
        self.couche_qualification = None
        # Sans cela, la carte garde le dernier rendu des couches retirées
        self.canvas.refreshAllLayers()

    def envoyer(self) -> None:
        if not self.pret_a_envoyer or self.lecture is None:
            return
        self.analyse_en_cours = True
        self.erreur_api = None
        self.echecs = []
        self.avancement = (0, len(self.lecture.sites_ok))
        self.change.emit()
        if self.reel:
            self._analyse = AnalyseInventaire(
                self.lecture.sites_ok, self._progression, self._analyse_terminee, self.version, environnement=self.environnement
            )
            self._analyse.demarrer()
            return
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._resultats_recus)
        self._timer.start(DELAI_ANALYSE_MS)

    def annuler_analyse(self) -> None:
        if self._analyse is not None:
            self._analyse.annuler()
            self._analyse = None
        if self._timer is not None:
            self._timer.stop()
        if self.analyse_en_cours:
            self.analyse_en_cours = False
            self.change.emit()

    def _progression(self, traites: int, total: int) -> None:
        self.avancement = (traites, total)
        self.change.emit()

    def _analyse_terminee(self, resultats: list[ResultatSite], erreur: Optional[ErreurApi]) -> None:
        self._analyse = None
        self.analyse_en_cours = False
        if self.lecture is None:
            return
        reussis = [r for r in resultats if r.ok]
        # Accès refusé ou API injoignable sans aucun résultat : on reste sur l'import, avec le motif
        if erreur is not None and not reussis:
            self.erreur_api = erreur
            self.change.emit()
            return
        self.echecs = [f"{r.site.site_nom or r.site.site_id} : {r.erreur}" for r in resultats if not r.ok]
        if erreur is not None:
            self.echecs.append(f"Analyse interrompue : {erreur.message}")
        self.sites = [
            site_depuis_api(r.site.site_id, r.site.site_nom, r.site.parcelles, r.enrichissement or {}, r.mutabilite or {}, r.complementaires)
            for r in reussis
        ]
        self.non_retrouves = []
        source = "API Mutafriches" + (" (staging)" if self.environnement != PRODUCTION else "")
        self._afficher_resultats({"provenance": f"{source} · analyse du {date.today().strftime('%d/%m/%Y')}"}, AVERTISSEMENT_API)

    def _resultats_recus(self) -> None:
        self.analyse_en_cours = False
        if self.lecture is None:
            return
        # Démonstration : les résultats viennent de la table attributaire figée de Montereau
        table, meta = charger_table()
        envoyes = self.lecture.sites_ok
        apparies = apparier(table, {s.site_id: s.parcelles for s in envoyes})
        retrouves = {s.site_id for s in apparies}
        self.non_retrouves = [s.site_nom for s in envoyes if s.site_id not in retrouves]
        self.sites = apparies or table
        self._afficher_resultats(meta, str(meta.get("avertissement", "")))

    def _afficher_resultats(self, meta: dict[str, object], avertissement: str) -> None:
        if self.lecture is None:
            return
        self.lignes_ecartees = [f"ligne {s.ligne} : {s.site_nom or s.site_id or 'sans nom'}" for s in self.lecture.sites_ko]
        self.avertissement = avertissement
        self.synthese = synthese(self.sites, meta)
        if not self.sites:
            self.erreur_api = ErreurApi("Aucun site n'a pu être analysé : " + " ; ".join(self.echecs[:3]))
            self.change.emit()
            return
        self.couche_mutabilite, self.couche_qualification = creer_couches(self.sites, self.synthese.code_insee or "inventaire")
        self._couches = [self.couche_mutabilite.id(), self.couche_qualification.id()]
        self.etape = Etape.RESULTATS
        self.change.emit()
        self.zoomer()

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

    @property
    def attention(self) -> list[str]:
        """Sites non analysés : lignes écartées, échecs de l'API, sites absents de la table figée."""
        return self.lignes_ecartees + self.echecs + [f"non retrouvé dans la table : {n}" for n in self.non_retrouves]

    def nouvelle_analyse(self) -> None:
        self.annuler_analyse()
        self.erreur_api = None
        self.echecs = []
        self.fichier = None
        self.lecture = None
        self.sites = []
        self.non_retrouves = []
        self.lignes_ecartees = []
        self.synthese = None
        self.etape = Etape.IMPORT
        self.change.emit()

    def nettoyer(self) -> None:
        self.annuler_analyse()
