"""Interface du service Mutafriches : l'interface ne dépend que de ce contrat."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

# Réponse JSON de l'API : structure libre, vérifiée à l'usage
Json = dict[str, Any]


class ErreurService(Exception):
    def __init__(self, message: str, recuperable: bool, code: str = "ERREUR") -> None:
        super().__init__(message)
        self.message = message
        self.recuperable = recuperable
        self.code = code


@dataclass
class ResultatEvaluation:
    # Forme de MutabiliteOutputDto (mode détaillé)
    resultat: Json
    # Informations propres à la simulation, None pour un vrai service
    variante_id: str | None = None
    variante_titre: str | None = None
    ecarts: int = 0
    note_simulation: str | None = None


class Tache(Protocol):
    def annuler(self) -> None: ...


class ServiceMutafriches(Protocol):
    est_simule: bool

    def enrichir(
        self,
        identifiants: list[str],
        succes: Callable[[Json], None],
        echec: Callable[[ErreurService], None],
    ) -> Tache: ...

    def evaluer(
        self,
        enrichissement: Json,
        reponses: dict[str, str],
        succes: Callable[[ResultatEvaluation], None],
        echec: Callable[[ErreurService], None],
    ) -> Tache: ...
