"""État du parcours, calqué sur l'application web : sélection, 3 étapes, résultats."""

from typing import Optional

from qgis.core import (
    QgsCoordinateTransform,
    QgsGeometry,
    QgsMapLayer,
    QgsProject,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..carto.exemple import ajouter_parcelles_exemple
from ..carto.selection import (
    LAMBERT_93,
    AnalysePerimetre,
    OutilParcelles,
    Surbrillance,
    analyser,
    couche_polygones,
)
from ..core.modele import InfoSimulation, Site
from ..core.service import ErreurService, ResultatEvaluation, ServiceMutafriches, Tache
from ..core.service_simule import ServiceSimule


class Etape:
    SELECTION = 0
    SITE_BATI = 1
    ENVIRONNEMENT = 2
    RISQUES = 3
    RESULTATS = 4


class Parcours(QObject):
    change = pyqtSignal()

    def __init__(self, iface: QgisInterface, service: ServiceMutafriches) -> None:
        super().__init__()
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.service = service
        self.etape = Etape.SELECTION
        self.site: Optional[Site] = None
        self.couche: Optional[QgsVectorLayer] = None
        self.analyse = AnalysePerimetre()
        self.enrichissement_en_cours = False
        self.erreur_enrichissement: Optional[ErreurService] = None
        self.evaluation_en_cours = False
        self.erreur_evaluation: Optional[ErreurService] = None
        self._tache: Optional[Tache] = None
        self.outil = OutilParcelles(self.canvas)
        self.surbrillance = Surbrillance(self.canvas)
        self.canvas.mapToolSet.connect(lambda *_: self.change.emit())
        iface.currentLayerChanged.connect(self._couche_active_changee)
        self._couche_active_changee(iface.activeLayer())

    @property
    def version_algorithme(self) -> str:
        return self.service.version_algorithme if isinstance(self.service, ServiceSimule) else ""

    def mesurer(self, identifiants: list[str]) -> Optional[float]:
        """Surface du site analysé, pour le profil générique du service simulé."""
        if self.site is None or self.site.identifiants != sorted(identifiants):
            return None
        return self.site.surface_m2

    # --- Couche et sélection ---------------------------------------------------------------

    def _couche_active_changee(self, couche: Optional[QgsMapLayer]) -> None:
        polygones = couche_polygones(couche)
        if polygones is None or polygones is self.couche:
            return
        if self.couche is not None:
            self.couche.selectionChanged.disconnect(self._selection_changee)
            self.couche.willBeDeleted.disconnect(self._couche_supprimee)
        self.couche = polygones
        polygones.selectionChanged.connect(self._selection_changee)
        polygones.willBeDeleted.connect(self._couche_supprimee)
        self.outil.couche = polygones
        self._selection_changee()

    def _couche_supprimee(self) -> None:
        self.couche = None
        self.outil.couche = None
        self.analyse = AnalysePerimetre()
        self.activer_selection(False)
        self.change.emit()

    def ajouter_exemple(self) -> None:
        couche = ajouter_parcelles_exemple()
        self.iface.setActiveLayer(couche)
        self._couche_active_changee(couche)
        self._zoomer(QgsGeometry.fromRect(couche.extent()), couche=couche, marge=-0.35)
        self.activer_selection(True)

    def selection_active(self) -> bool:
        return self.canvas.mapTool() is self.outil

    def activer_selection(self, active: bool) -> None:
        if active and self.couche is not None:
            self.canvas.setMapTool(self.outil)
        elif not active and self.selection_active():
            self.canvas.unsetMapTool(self.outil)
        self.change.emit()

    def _selection_changee(self, *_: object) -> None:
        if self.etape != Etape.SELECTION:
            return
        self.analyse = analyser(self.couche, self.couche.selectedFeatures()) if self.couche else AnalysePerimetre()
        self.change.emit()

    def retirer_parcelle(self, idu: str) -> None:
        fid = self.analyse.entites.get(idu)
        if self.couche is not None and fid is not None:
            self.couche.deselect(fid)

    def nouvelle_analyse(self) -> None:
        self._annuler_tache()
        self.site = None
        self.erreur_enrichissement = None
        self.erreur_evaluation = None
        self.surbrillance.effacer()
        if self.couche is not None:
            self.couche.removeSelection()
        self.etape = Etape.SELECTION
        self._selection_changee()
        self.activer_selection(True)

    def analyser_selection(self) -> None:
        """Fige le périmètre et lance la récupération des données (bouton « Analyser »)."""
        if not self.analyse.valide or self.analyse.geometrie is None:
            return
        wkt = self.analyse.geometrie.asWkt(2)
        if self.site is None:
            self.site = Site(parcelles=self.analyse.parcelles, geometrie_wkt=wkt)
        else:
            self.site.changer_perimetre(self.analyse.parcelles, wkt)
        # Le périmètre est figé : la sélection QGIS peut ensuite changer librement
        if self.couche is not None:
            self.couche.removeSelection()
        self.activer_selection(False)
        self.surbrillance.afficher(wkt)
        self.etape = Etape.SITE_BATI
        if self.site.enrichissement is None:
            self.lancer_enrichissement()
        else:
            self.change.emit()

    def modifier_selection(self) -> None:
        self._annuler_tache()
        self.surbrillance.effacer()
        self.etape = Etape.SELECTION
        self._selection_changee()
        self.activer_selection(True)

    # --- Qualification et résultats --------------------------------------------------------

    def lancer_enrichissement(self) -> None:
        if self.site is None:
            return
        self._annuler_tache()
        self.erreur_enrichissement = None
        self.enrichissement_en_cours = True
        self.change.emit()
        self._tache = self.service.enrichir(
            self.site.identifiants, self._enrichissement_recu, self._enrichissement_echoue
        )

    def _enrichissement_recu(self, donnees: dict[str, object]) -> None:
        self.enrichissement_en_cours = False
        if self.site is not None:
            self.site.enrichissement = donnees
        self.change.emit()

    def _enrichissement_echoue(self, erreur: ErreurService) -> None:
        self.enrichissement_en_cours = False
        self.erreur_enrichissement = erreur
        self.change.emit()

    def aller_etape(self, etape: int) -> None:
        self.etape = etape
        self.change.emit()

    def definir_reponse(self, cle: str, valeur: str) -> None:
        if self.site is not None:
            self.site.definir_reponse(cle, valeur)

    def evaluer(self) -> None:
        if self.site is None or self.site.enrichissement is None:
            return
        self._annuler_tache()
        self.erreur_evaluation = None
        self.evaluation_en_cours = True
        self.change.emit()
        self._tache = self.service.evaluer(
            self.site.enrichissement,
            self.site.reponses_completes(),
            self._evaluation_recue,
            self._evaluation_echouee,
        )

    def _evaluation_recue(self, resultat: ResultatEvaluation) -> None:
        self.evaluation_en_cours = False
        if self.site is None:
            return
        self.site.evaluation = resultat.resultat
        self.site.simulation = InfoSimulation(
            variante_titre=resultat.variante_titre,
            ecarts=resultat.ecarts,
            note=resultat.note_simulation,
        )
        self.etape = Etape.RESULTATS
        self.change.emit()

    def _evaluation_echouee(self, erreur: ErreurService) -> None:
        self.evaluation_en_cours = False
        self.erreur_evaluation = erreur
        self.change.emit()

    # --- Outils ----------------------------------------------------------------------------

    def _annuler_tache(self) -> None:
        if self._tache is not None:
            self._tache.annuler()
            self._tache = None
        self.enrichissement_en_cours = False
        self.evaluation_en_cours = False

    def _zoomer(self, geometrie: QgsGeometry, couche: Optional[QgsVectorLayer] = None, marge: float = 0.6) -> None:
        if geometrie.isEmpty():
            return
        etendue = geometrie.boundingBox()
        etendue.grow(max(etendue.width(), etendue.height()) * marge + 20)
        source = couche.crs() if couche is not None else LAMBERT_93
        transformation = QgsCoordinateTransform(
            source, self.canvas.mapSettings().destinationCrs(), QgsProject.instance()
        )
        self.canvas.setExtent(transformation.transformBoundingBox(etendue))
        self.canvas.refresh()

    def nettoyer(self) -> None:
        self._annuler_tache()
        self.activer_selection(False)
        self.surbrillance.supprimer()
        try:
            self.iface.currentLayerChanged.disconnect(self._couche_active_changee)
        except TypeError:
            pass
