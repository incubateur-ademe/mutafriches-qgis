"""Utilisateur de l'extension : déclarant de sa structure (ADR-0055 de Mutafriches), mémorisé dans QGIS."""

import re
from dataclasses import dataclass

from ..core import reglages
from ..core.declaration import TYPES_STRUCTURE, Declaration, hote_de_domaine

# Miroir de FORMAT_EMAIL (formulaire de déclaration web)
FORMAT_MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Utilisateur:
    prenom: str = ""
    nom: str = ""
    structure: str = ""
    type_structure: str = ""
    domaine: str = ""
    mail: str = ""

    def erreurs(self) -> dict[str, str]:
        """Miroir de validerDeclaration (formulaire web) : tout est obligatoire pour l'API."""
        erreurs: dict[str, str] = {}
        if len(self.structure.strip()) < 2:
            erreurs["structure"] = "Indiquez le nom de votre structure."
        if self.type_structure not in TYPES_STRUCTURE:
            erreurs["type_structure"] = "Choisissez un type de structure."
        if not hote_de_domaine(self.domaine):
            erreurs["domaine"] = (
                "Indiquez un nom de domaine complet, avec son extension, par exemple ma-collectivite.fr."
            )
        if not self.prenom.strip():
            erreurs["prenom"] = "Indiquez votre prénom."
        if not self.nom.strip():
            erreurs["nom"] = "Indiquez votre nom."
        if not FORMAT_MAIL.match(self.mail.strip()):
            erreurs["mail"] = "Indiquez une adresse e-mail valide, par exemple nom@domaine.fr."
        return erreurs

    @property
    def valide(self) -> bool:
        return not self.erreurs()

    @property
    def resume(self) -> str:
        identite = " ".join(valeur.strip() for valeur in (self.prenom, self.nom) if valeur.strip())
        return " · ".join(valeur.strip() for valeur in (identite, self.structure, self.domaine) if valeur.strip())

    def declaration(self) -> Declaration:
        return Declaration(
            structure=self.structure,
            type_structure=self.type_structure,
            domaine=self.domaine,
            prenom=self.prenom,
            nom=self.nom,
            email=self.mail,
        )


def charger_utilisateur() -> Utilisateur:
    return Utilisateur(
        prenom=reglages.PRENOM.value(),
        nom=reglages.NOM.value(),
        structure=reglages.STRUCTURE.value(),
        type_structure=reglages.TYPE_STRUCTURE.value(),
        domaine=reglages.DOMAINE.value(),
        mail=reglages.MAIL.value(),
    )


def enregistrer_utilisateur(utilisateur: Utilisateur) -> None:
    reglages.PRENOM.setValue(utilisateur.prenom.strip())
    reglages.NOM.setValue(utilisateur.nom.strip())
    reglages.STRUCTURE.setValue(utilisateur.structure.strip())
    reglages.TYPE_STRUCTURE.setValue(utilisateur.type_structure)
    # Une adresse collée (https://www.exemple.fr/outil) est ramenée à son hôte, celui qui est déclaré
    reglages.DOMAINE.setValue(hote_de_domaine(utilisateur.domaine) or utilisateur.domaine.strip())
    reglages.MAIL.setValue(utilisateur.mail.strip())
