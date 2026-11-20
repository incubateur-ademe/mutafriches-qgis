"""Utilisateur de l'extension : identité, structure, mail, consentement, tous facultatifs, mémorisés dans QGIS."""

import re
from dataclasses import dataclass

from ..core import reglages

FORMAT_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Utilisateur:
    structure: str = ""
    mail: str = ""
    consentement: bool = False
    prenom: str = ""
    nom: str = ""

    @property
    def valide(self) -> bool:
        """Tout est facultatif ; seul un mail saisi doit avoir la forme d'une adresse."""
        return not self.mail.strip() or bool(FORMAT_MAIL.match(self.mail.strip()))

    @property
    def renseigne(self) -> bool:
        return bool(self.resume)

    @property
    def resume(self) -> str:
        identite = " ".join(valeur.strip() for valeur in (self.prenom, self.nom) if valeur.strip())
        return " · ".join(valeur.strip() for valeur in (identite, self.structure, self.mail) if valeur.strip())


def charger_utilisateur() -> Utilisateur:
    return Utilisateur(
        structure=reglages.STRUCTURE.value(),
        mail=reglages.MAIL.value(),
        consentement=reglages.CONSENTEMENT.value(),
        prenom=reglages.PRENOM.value(),
        nom=reglages.NOM.value(),
    )


def enregistrer_utilisateur(utilisateur: Utilisateur) -> None:
    reglages.PRENOM.setValue(utilisateur.prenom.strip())
    reglages.NOM.setValue(utilisateur.nom.strip())
    reglages.STRUCTURE.setValue(utilisateur.structure.strip())
    reglages.MAIL.setValue(utilisateur.mail.strip())
    # Un accord pour être contacté n'a de sens qu'avec une adresse
    reglages.CONSENTEMENT.setValue(utilisateur.consentement and bool(utilisateur.mail.strip()))
    reglages.ACCUEIL_VU.setValue(True)
