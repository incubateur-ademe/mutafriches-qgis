"""Déclaration de la structure au registre des intégrateurs de Mutafriches (ADR-0055 de Mutafriches).

L'extension déclare une fois, par environnement, le domaine de la structure sur le canal `qgis` ;
l'origine renvoyée part ensuite dans l'en-tête `Origin` des appels d'analyse.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QObject, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from . import reglages

CHEMIN_DECLARATION = "/api/integrateurs/declarations"
CANAL_QGIS = "qgis"
# Miroir de EN_TETE_CLIENT_MUTAFRICHES et PREFIXE_CLIENT_QGIS (shared-types)
EN_TETE_CLIENT = "x-mutafriches-client"
PREFIXE_CLIENT_QGIS = "qgis"
CONTACT_MUTAFRICHES = "contact@mutafriches.beta.gouv.fr"
DELAI_DECLARATION_MS = 30_000

# Miroir de TYPE_STRUCTURE_LABELS (shared-types)
TYPES_STRUCTURE: dict[str, str] = {
    "collectivite": "Collectivité territoriale",
    "etablissement_public": "Établissement public (EPF, EPA, agence d'urbanisme…)",
    "etat": "Service de l'État",
    "bureau_etudes": "Bureau d'études",
    "entreprise": "Entreprise",
    "association": "Association",
    "autre": "Autre",
}

# Miroir de SCHEMA_URL et FORMAT_NOM_DOMAINE (shared-types) : même règle que le formulaire web
SCHEMA_URL = re.compile(r"^([a-z][a-z0-9+.-]*):\/\/")
FORMAT_NOM_DOMAINE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$"
)

Json = dict[str, Any]


def hote_de_domaine(saisie: str) -> str | None:
    """Portage de hoteDeDomaineDeclare (shared-types) : l'hôte d'une saisie libre, ou None."""
    brut = saisie.strip().lower()
    if not brut or re.search(r"\s", brut):
        return None
    schema = SCHEMA_URL.match(brut)
    if schema and schema.group(1) != "https":
        return None
    autorite = re.split(r"[/?#]", brut[schema.end() :] if schema else brut)[0]
    if "@" in autorite or ":" in autorite:
        return None
    return autorite if FORMAT_NOM_DOMAINE.match(autorite) else None


def en_tete_client(version: str) -> str:
    return f"{PREFIXE_CLIENT_QGIS}/{version or 'dev'}"


@dataclass(frozen=True)
class Declaration:
    structure: str
    type_structure: str
    domaine: str
    prenom: str
    nom: str
    email: str

    def corps(self) -> Json:
        return {
            "canal": CANAL_QGIS,
            "structure": self.structure.strip(),
            "typeStructure": self.type_structure,
            "domaine": self.domaine.strip(),
            "prenom": self.prenom.strip(),
            "nom": self.nom.strip(),
            "email": self.email.strip(),
        }

    @property
    def empreinte(self) -> str:
        # Une déclaration identique n'est pas renvoyée : 5 déclarations par heure et par IP
        return hashlib.sha256(json.dumps(self.corps(), sort_keys=True).encode("utf-8")).hexdigest()[:16]


# --- Déclarations connues, par adresse d'API (staging et production ont chacun leur registre) ---


def _connues() -> dict[str, dict[str, str]]:
    try:
        valeur = json.loads(reglages.DECLARATIONS.value() or "{}")
    except ValueError:
        return {}
    return valeur if isinstance(valeur, dict) else {}


def origine_declaree(url: str, declaration: Declaration) -> str:
    """Origine déjà obtenue pour cette API et cette saisie, sinon chaîne vide."""
    connue = _connues().get(url) or {}
    return str(connue.get("origine", "")) if connue.get("empreinte") == declaration.empreinte else ""


def memoriser(url: str, declaration: Declaration, origine: str) -> None:
    connues = _connues()
    connues[url] = {"empreinte": declaration.empreinte, "origine": origine}
    reglages.DECLARATIONS.setValue(json.dumps(connues, sort_keys=True))


def oublier(url: str) -> None:
    """Après un refus d'accès : la prochaine analyse redéclare plutôt que de reprendre l'origine refusée."""
    connues = _connues()
    if connues.pop(url, None) is not None:
        reglages.DECLARATIONS.setValue(json.dumps(connues, sort_keys=True))


# --- Appel ----------------------------------------------------------------------------------------


class ErreurDeclaration(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def message_erreur(statut: int, corps: bytes, erreur_reseau: str) -> str:
    # Miroir de messageErreurDeclaration (formulaire web)
    if statut == 0:
        return f"API Mutafriches injoignable ({erreur_reseau})."
    if statut == 429:
        return "Trop de déclarations depuis votre connexion. Réessayez dans une heure."
    if statut == 400:
        try:
            contenu = json.loads(corps.decode("utf-8"))
            message = contenu.get("message") if isinstance(contenu, dict) else None
            if isinstance(message, list):
                return " ; ".join(str(m) for m in message)
            if message:
                return str(message)
        except (ValueError, UnicodeDecodeError):
            pass
    return f"La déclaration n'a pas pu être enregistrée. Réessayez, ou écrivez-nous à {CONTACT_MUTAFRICHES}."


class DeclarationIntegrateur(QObject):
    """POST /api/integrateurs/declarations ; rend l'origine à envoyer, ou une erreur expliquée.

    Une API sans registre (404 : production pas encore déployée) rend l'origine historique de
    l'extension, que l'API accepte toujours ; rien n'est alors mémorisé.
    """

    def __init__(
        self,
        url: str,
        declaration: Declaration,
        version_extension: str,
        termine: Callable[[str, ErreurDeclaration | None], None],
    ) -> None:
        super().__init__()
        self.url = url
        self.declaration = declaration
        self.version = version_extension
        self.termine = termine
        self._reponse: QNetworkReply | None = None
        self._annulee = False

    def demarrer(self) -> None:
        requete = QNetworkRequest(QUrl(self.url + CHEMIN_DECLARATION))
        requete.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        requete.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"mutafriches-qgis/{self.version or 'dev'}")
        requete.setRawHeader(EN_TETE_CLIENT.encode("ascii"), en_tete_client(self.version).encode("utf-8"))
        requete.setTransferTimeout(DELAI_DECLARATION_MS)
        corps = json.dumps(self.declaration.corps()).encode("utf-8")
        self._reponse = QgsNetworkAccessManager.instance().post(requete, corps)
        self._reponse.finished.connect(self._recu)

    def annuler(self) -> None:
        self._annulee = True
        if self._reponse is not None:
            self._reponse.abort()

    def _recu(self) -> None:
        reponse = self._reponse
        self._reponse = None
        if reponse is None:
            return
        statut = int(reponse.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0)
        contenu = bytes(reponse.readAll()) if reponse.isOpen() else b""
        erreur_reseau = reponse.errorString()
        reponse.deleteLater()
        if self._annulee:
            return
        if statut == 404:
            self.termine(reglages.ORIGINE_HISTORIQUE, None)
            return
        if not 200 <= statut < 300:
            self.termine("", ErreurDeclaration(message_erreur(statut, contenu, erreur_reseau)))
            return
        try:
            donnees = json.loads(contenu.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            donnees = None
        if not isinstance(donnees, dict):
            self.termine("", ErreurDeclaration(message_erreur(500, b"", "")))
            return
        if donnees.get("statut") == "revoque":
            self.termine(
                "",
                ErreurDeclaration(
                    f"L'accès de ce domaine a été suspendu. Écrivez-nous à {CONTACT_MUTAFRICHES} pour en parler."
                ),
            )
            return
        origine = str(donnees.get("origine") or "")
        if donnees.get("statut") != "actif" or not origine:
            self.termine("", ErreurDeclaration(message_erreur(500, b"", "")))
            return
        memoriser(self.url, self.declaration, origine)
        self.termine(origine, None)
