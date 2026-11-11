"""Utilisateur de l'extension : structure, mail, consentement, mémorisés dans les réglages QGIS."""

import re
from dataclasses import dataclass

from ..core import reglages

FORMAT_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Utilisateur:
    structure: str = ""
    mail: str = ""
    consentement: bool = False

    @property
    def complet(self) -> bool:
        return bool(self.structure.strip()) and bool(FORMAT_MAIL.match(self.mail.strip()))


def charger_utilisateur() -> Utilisateur:
    return Utilisateur(
        structure=reglages.STRUCTURE.value(),
        mail=reglages.MAIL.value(),
        consentement=reglages.CONSENTEMENT.value(),
    )


def enregistrer_utilisateur(utilisateur: Utilisateur) -> None:
    reglages.STRUCTURE.setValue(utilisateur.structure.strip())
    reglages.MAIL.setValue(utilisateur.mail.strip())
    reglages.CONSENTEMENT.setValue(utilisateur.consentement)
