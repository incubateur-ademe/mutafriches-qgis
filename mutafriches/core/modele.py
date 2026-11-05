"""Modèle d'un site : une ou plusieurs parcelles analysées ensemble."""

from dataclasses import dataclass, field
from typing import Optional

from .referentiel import CLES_TERRAIN, NE_SAIT_PAS

Json = dict[str, object]


@dataclass
class ParcelleSite:
    idu: str
    libelle: str
    surface_m2: float


@dataclass
class InfoSimulation:
    """Écart entre la réponse simulée affichée et la saisie (service simulé uniquement)."""

    variante_titre: Optional[str] = None
    ecarts: int = 0
    note: Optional[str] = None


@dataclass
class Site:
    parcelles: list[ParcelleSite]
    # Union des parcelles en Lambert 93
    geometrie_wkt: str
    enrichissement: Optional[Json] = None
    reponses: dict[str, str] = field(default_factory=dict)
    evaluation: Optional[Json] = None
    simulation: Optional[InfoSimulation] = None

    @property
    def identifiants(self) -> list[str]:
        return sorted(p.idu for p in self.parcelles)

    @property
    def surface_m2(self) -> float:
        return sum(p.surface_m2 for p in self.parcelles)

    def reponses_completes(self) -> dict[str, str]:
        return {cle: self.reponses.get(cle, NE_SAIT_PAS) for cle in CLES_TERRAIN}

    @property
    def nombre_reponses(self) -> int:
        return sum(1 for v in self.reponses_completes().values() if v != NE_SAIT_PAS)

    def changer_perimetre(self, parcelles: list[ParcelleSite], geometrie_wkt: str) -> None:
        # Les réponses terrain sont conservées ; l'enrichissement ne vaut que pour l'ancien périmètre.
        if sorted(p.idu for p in parcelles) != self.identifiants:
            self.enrichissement = None
        self.parcelles = parcelles
        self.geometrie_wkt = geometrie_wkt
        self.evaluation = None

    def definir_reponse(self, cle: str, valeur: str) -> None:
        # « Ne sait pas » est une réponse ; seule une valeur vide retire la réponse
        if valeur:
            self.reponses[cle] = valeur
        else:
            self.reponses.pop(cle, None)

    def fiabilite(self) -> Optional[Json]:
        if not self.evaluation:
            return None
        return self.evaluation.get("fiabilite")  # type: ignore[return-value]
