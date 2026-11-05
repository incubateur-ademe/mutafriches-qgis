"""État du parcours prototype : utilisateur, envoi des sites CNIG, résultats figés."""

import shutil
from pathlib import Path
from typing import Optional

from qgis.core import QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

from ..carto.couches import creer_couches, emprise_carte
from ..core.attributaire import (
    FICHIER_MODELE_CNIG,
    SiteAttributaire,
    Synthese,
    apparier,
    charger_table,
    synthese,
)
from ..core.cnig import LectureCnig, lire_cnig
from .accueil import Utilisateur, charger_utilisateur, enregistrer_utilisateur

# Attente simulée de l'analyse par lot, proche d'un appel réel pour quelques dizaines de sites
DELAI_ANALYSE_MS = 2500


class Etape:
    ACCUEIL = 0
    IMPORT = 1
    RESULTATS = 2


class Parcours(QObject):
    change = pyqtSignal()

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()
        self.iface = iface
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

    def envoyer(self) -> None:
        if not self.pret_a_envoyer or self.lecture is None:
            return
        self.analyse_en_cours = True
        self.change.emit()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._resultats_recus)
        self._timer.start(DELAI_ANALYSE_MS)

    def _resultats_recus(self) -> None:
        self.analyse_en_cours = False
        if self.lecture is None:
            return
        # Prototype : les résultats viennent de la table attributaire figée de Montereau
        table, meta = charger_table()
        envoyes = self.lecture.sites_ok
        apparies = apparier(table, {s.site_id: s.parcelles for s in envoyes})
        retrouves = {s.site_id for s in apparies}
        self.non_retrouves = [s.site_nom for s in envoyes if s.site_id not in retrouves]
        self.lignes_ecartees = [f"ligne {s.ligne} : {s.site_nom or s.site_id or 'sans nom'}" for s in self.lecture.sites_ko]
        self.sites = apparies or table
        self.avertissement = str(meta.get("avertissement", ""))
        self.synthese = synthese(self.sites, meta)
        self.couche_mutabilite, self.couche_qualification = creer_couches(self.sites, self.synthese.code_insee)
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
        """Sites non analysés : lignes écartées et sites absents de la table figée."""
        return self.lignes_ecartees + [f"non retrouvé dans la table : {n}" for n in self.non_retrouves]

    def nouvelle_analyse(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.analyse_en_cours = False
        self.fichier = None
        self.lecture = None
        self.sites = []
        self.non_retrouves = []
        self.lignes_ecartees = []
        self.synthese = None
        self.etape = Etape.IMPORT
        self.change.emit()

    def nettoyer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
