"""Utilisateur du prototype : structure, mail, consentement, mémorisés dans les réglages QGIS."""

import re
from dataclasses import dataclass

from qgis.core import QgsSettings

CLE_REGLAGES = "mutafriches/utilisateur"
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
    reglages = QgsSettings()
    return Utilisateur(
        structure=str(reglages.value(f"{CLE_REGLAGES}/structure", "")),
        mail=str(reglages.value(f"{CLE_REGLAGES}/mail", "")),
        consentement=str(reglages.value(f"{CLE_REGLAGES}/consentement", "false")).lower() == "true",
    )


def enregistrer_utilisateur(utilisateur: Utilisateur) -> None:
    reglages = QgsSettings()
    reglages.setValue(f"{CLE_REGLAGES}/structure", utilisateur.structure.strip())
    reglages.setValue(f"{CLE_REGLAGES}/mail", utilisateur.mail.strip())
    reglages.setValue(f"{CLE_REGLAGES}/consentement", "true" if utilisateur.consentement else "false")
