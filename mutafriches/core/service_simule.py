"""Service simulé : rejoue des réponses figées, sans aucun calcul de mutabilité."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from qgis.PyQt.QtCore import QTimer

from .referentiel import CLES_TERRAIN, NE_SAIT_PAS, formater_surface
from .service import ErreurService, Json, ResultatEvaluation

DOSSIER_SCENARIOS = Path(__file__).resolve().parent.parent / "demo" / "scenarios"
FICHIER_GENERIQUE = DOSSIER_SCENARIOS.parent / "generique.json"

# Surface (m²) de la sélection, mesurée sur la couche QGIS ; None si inconnue
Mesureur = Callable[[list[str]], Optional[float]]
# Part bâtie fictive du profil générique : un point de la grille figée y correspond exactement
PART_BATIE_FICTIVE = 0.2


@dataclass
class Scenario:
    id: str
    titre: str
    description: str
    nom_suggere: str
    parcelles: list[str]
    echecs_avant_succes: int
    enrichissement: Json
    evaluations: list[Json]
    version_algorithme: str


def charger_scenarios(dossier: Path = DOSSIER_SCENARIOS) -> list[Scenario]:
    scenarios = []
    for chemin in sorted(dossier.glob("*.json")):
        d = json.loads(chemin.read_text(encoding="utf-8"))
        scenarios.append(
            Scenario(
                id=d["id"],
                titre=d["titre"],
                description=d["description"],
                nom_suggere=d["nomSuggere"],
                parcelles=sorted(d["parcelles"]),
                echecs_avant_succes=int(d["echecsAvantSucces"]),
                enrichissement=d["enrichissement"],
                evaluations=d["evaluations"],
                version_algorithme=d["versionAlgorithme"],
            )
        )
    # Ordre de présentation : parcours principal d'abord
    ordre = {"station-service": 0, "pierre-timbaud": 1, "pont-malembert": 2}
    return sorted(scenarios, key=lambda s: ordre.get(s.id, 99))


class TacheSimulee:
    def __init__(self, delai_ms: Optional[int], action: Callable[[], None]) -> None:
        self._timer: Optional[QTimer] = None
        if delai_ms is None:
            action()
            return
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(action)
        self._timer.start(delai_ms)

    def annuler(self) -> None:
        if self._timer is not None:
            self._timer.stop()


class ServiceSimule:
    est_simule = True

    def __init__(
        self,
        scenarios: Optional[list[Scenario]] = None,
        delai_enrichissement_ms: Optional[int] = 1400,
        delai_evaluation_ms: Optional[int] = 900,
        mesurer: Optional[Mesureur] = None,
    ) -> None:
        self.scenarios = scenarios if scenarios is not None else charger_scenarios()
        self.delai_enrichissement_ms = delai_enrichissement_ms
        self.delai_evaluation_ms = delai_evaluation_ms
        self.mesurer = mesurer
        self._tentatives: dict[str, int] = {}
        self._generique: Optional[Json] = None

    @property
    def generique(self) -> Json:
        if self._generique is None:
            self._generique = json.loads(FICHIER_GENERIQUE.read_text(encoding="utf-8"))
        return self._generique

    @property
    def version_algorithme(self) -> str:
        return self.scenarios[0].version_algorithme if self.scenarios else ""

    def variantes_generiques(self) -> list[Json]:
        points = self.generique["points"]
        assert isinstance(points, list)
        return points[0]["evaluations"]  # type: ignore[no-any-return]

    def _enrichissement_generique(self, identifiants: list[str]) -> Optional[Json]:
        surface_site = self.mesurer(identifiants) if self.mesurer else None
        if surface_site is None:
            return None
        ids = sorted(identifiants)
        gabarit = self.generique["gabarit"]
        assert isinstance(gabarit, dict)
        enrichissement: Json = json.loads(json.dumps(gabarit))
        # Commune du profil générique : code INSEE de l'identifiant cadastral s'il y en a un
        code = ids[0][:5] if len(ids[0]) == 14 else None
        # Nom connu seulement pour la commune des parcelles d'exemple
        commune = gabarit["commune"] if code == gabarit["codeInsee"] else f"Code INSEE {code}"
        enrichissement.update(
            {
                "identifiantParcelle": ids[0],
                "codeInsee": code or "",
                "commune": commune if code else "Non disponible",
                "surfaceSite": round(surface_site),
                "surfaceBati": round(surface_site * PART_BATIE_FICTIVE),
            }
        )
        if len(ids) > 1:
            enrichissement.update({"identifiantsParcelles": ids, "nombreParcelles": len(ids)})
        return enrichissement

    def reinitialiser(self) -> None:
        self._tentatives.clear()

    def scenario_pour(self, identifiants: list[str]) -> Optional[Scenario]:
        cible = sorted(identifiants)
        return next((s for s in self.scenarios if s.parcelles == cible), None)

    def enrichir(
        self,
        identifiants: list[str],
        succes: Callable[[Json], None],
        echec: Callable[[ErreurService], None],
    ) -> TacheSimulee:
        def repondre() -> None:
            scenario = self.scenario_pour(identifiants)
            if scenario is None:
                generique = self._enrichissement_generique(identifiants)
                if generique is None:
                    echec(
                        ErreurService(
                            "Surface de la sélection impossible à mesurer.",
                            recuperable=False,
                            code="SURFACE_INCONNUE",
                        )
                    )
                else:
                    succes(generique)
                return
            tentative = self._tentatives.get(scenario.id, 0) + 1
            self._tentatives[scenario.id] = tentative
            if tentative <= scenario.echecs_avant_succes:
                echec(
                    ErreurService(
                        "Le service d'enrichissement n'a pas répondu à temps. "
                        "Vous pouvez relancer la récupération.",
                        recuperable=True,
                        code="DELAI_DEPASSE",
                    )
                )
                return
            succes(json.loads(json.dumps(scenario.enrichissement)))

        return TacheSimulee(self.delai_enrichissement_ms, repondre)

    def evaluer(
        self,
        enrichissement: Json,
        reponses: dict[str, str],
        succes: Callable[[ResultatEvaluation], None],
        echec: Callable[[ErreurService], None],
    ) -> TacheSimulee:
        def repondre() -> None:
            ids = enrichissement.get("identifiantsParcelles") or [
                enrichissement.get("identifiantParcelle")
            ]
            scenario = self.scenario_pour([str(i) for i in ids])  # type: ignore[union-attr]
            note = None
            if scenario is not None:
                evaluations = scenario.evaluations
            else:
                point = choisir_point(self.generique["points"], enrichissement)  # type: ignore[arg-type]
                evaluations = point["evaluations"]  # type: ignore[assignment]
                note = (
                    "Profil générique (données fictives) : indices figés pour "
                    f"un site d'environ {formater_surface(float(point['surfaceSite']))} dont "
                    f"{formater_surface(float(point['surfaceBati']))} bâtis."
                )
            evaluation, ecarts = choisir_variante(evaluations, reponses)
            succes(
                ResultatEvaluation(
                    resultat=json.loads(json.dumps(evaluation["resultat"])),
                    variante_id=str(evaluation["id"]),
                    variante_titre=str(evaluation["titre"]),
                    ecarts=ecarts,
                    note_simulation=note,
                )
            )

        return TacheSimulee(self.delai_evaluation_ms, repondre)


def choisir_variante(evaluations: list[Json], reponses: dict[str, str]) -> tuple[Json, int]:
    """Réponse figée la plus proche de la saisie, et nombre de réponses qui diffèrent."""
    saisie = {cle: reponses.get(cle, NE_SAIT_PAS) for cle in CLES_TERRAIN}

    def ecarts(evaluation: Json) -> int:
        prevues = evaluation["reponses"]
        assert isinstance(prevues, dict)
        return sum(1 for cle in CLES_TERRAIN if prevues.get(cle, NE_SAIT_PAS) != saisie[cle])

    meilleure = min(evaluations, key=ecarts)
    return meilleure, ecarts(meilleure)


def choisir_point(points: list[Json], enrichissement: Json) -> Json:
    """Point de grille le plus proche : surface du site (échelle log), puis part bâtie."""
    surface = max(float(enrichissement.get("surfaceSite") or 1), 1.0)  # type: ignore[arg-type]
    part = float(enrichissement.get("surfaceBati") or 0) / surface  # type: ignore[arg-type]

    def distance(point: Json) -> tuple[float, float]:
        site = float(point["surfaceSite"])  # type: ignore[arg-type]
        return (
            round(abs(math.log(site / surface)), 6),
            abs(float(point["surfaceBati"]) / site - part),  # type: ignore[arg-type]
        )

    return min(points, key=distance)
