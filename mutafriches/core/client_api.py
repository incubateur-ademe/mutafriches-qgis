"""Client de l'API Mutafriches existante : un site = enrichissement puis calcul de mutabilité.

Aucune route par lot ni import d'inventaire côté API : l'extension enchaîne elle-même les
appels, site par site, sous la limite de 100 requêtes par minute (ADR-0003).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QObject, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from . import reglages
from .cnig import SiteCnig, complementaires_depuis_cnig
from .reglages import DEMONSTRATION, PRODUCTION, STAGING

__all__ = [
    "DEMONSTRATION",
    "LIBELLES_ENVIRONNEMENTS",
    "PRODUCTION",
    "STAGING",
    "URLS",
    "AnalyseInventaire",
    "ErreurApi",
    "ResultatSite",
    "url_api",
]

# Réponse JSON de l'API : structure libre, vérifiée à l'usage
Json = dict[str, Any]

# Adresse de l'API par environnement ; la démonstration n'appelle rien (table figée)
URLS: dict[str, str] = {
    PRODUCTION: "https://mutafriches.beta.gouv.fr",
    STAGING: "https://mutafriches.incubateur.ademe.dev",
}
LIBELLES_ENVIRONNEMENTS: dict[str, str] = {
    PRODUCTION: "Production",
    STAGING: "Staging (environnement de test)",
    DEMONSTRATION: "Démonstration (données figées)",
}

DELAI_REQUETE_MS = 90_000
ATTENTE_DEBIT_MS = 20_000
ESSAIS_DEBIT = 2
MESSAGE_ERREUR_SERVEUR = (
    "L'API n'a pas pu enrichir ce site : parcelles introuvables au cadastre, ou service momentanément indisponible."
)
MESSAGE_DELAI = "Délai dépassé : l'API n'a pas répondu à temps pour ce site."
# Un second essai aboutit souvent : l'API a mis en cache ce qu'elle avait déjà récupéré
ESSAIS_DELAI = 1
ERREURS_DELAI = (QNetworkReply.NetworkError.OperationCanceledError, QNetworkReply.NetworkError.TimeoutError)


def url_api(environnement: str = "") -> str:
    """Adresse libre du mode développeur si elle est renseignée, sinon celle de l'environnement."""
    return reglages.url_personnalisee() or URLS.get(environnement or reglages.environnement(), URLS[PRODUCTION])


@dataclass
class ResultatSite:
    site: SiteCnig
    complementaires: dict[str, str]
    enrichissement: Json | None = None
    mutabilite: Json | None = None
    erreur: str = ""

    @property
    def ok(self) -> bool:
        return self.mutabilite is not None and not self.erreur


class ErreurApi(Exception):
    def __init__(self, message: str, bloquante: bool = False) -> None:
        super().__init__(message)
        self.message = message
        # Une erreur bloquante (accès refusé, API injoignable) arrête tout l'inventaire
        self.bloquante = bloquante


def message_http(statut: int, corps: bytes, erreur_reseau: str, delai_depasse: bool = False) -> ErreurApi:
    # QGIS interrompt lui-même une requête trop longue (réglage réseau, 60 s par défaut) : le
    # site est en cause, pas l'API, et les suivants doivent être tentés
    if delai_depasse:
        return ErreurApi(MESSAGE_DELAI)
    if statut == 403:
        return ErreurApi(
            "Accès refusé par l'API Mutafriches : l'origine de l'extension n'y est pas encore autorisée.",
            bloquante=True,
        )
    if statut == 0:
        return ErreurApi(f"API Mutafriches injoignable ({erreur_reseau}).", bloquante=True)
    # L'API répond 500 quand elle ne retrouve aucune parcelle du site au cadastre
    if statut >= 500:
        return ErreurApi(MESSAGE_ERREUR_SERVEUR)
    detail = ""
    try:
        contenu = json.loads(corps.decode("utf-8"))
        message = contenu.get("message") if isinstance(contenu, dict) else None
        detail = "; ".join(message) if isinstance(message, list) else str(message or "")
    except (ValueError, UnicodeDecodeError):
        pass
    return ErreurApi(f"Erreur {statut} de l'API" + (f" : {detail}" if detail else "."))


class AnalyseInventaire(QObject):
    """Analyse séquentielle d'un inventaire : progression, annulation, erreurs site par site."""

    def __init__(
        self,
        sites: list[SiteCnig],
        progression: Callable[[int, int], None],
        termine: Callable[[list[ResultatSite], ErreurApi | None], None],
        version_extension: str = "",
        intervalle_ms: int | None = None,
        environnement: str = "",
    ) -> None:
        super().__init__()
        self.sites = sites
        self.progression = progression
        self.termine = termine
        self.url = url_api(environnement)
        self.origine = reglages.origine()
        self.agent = f"mutafriches-qgis/{version_extension or 'dev'}"
        self.intervalle_ms = reglages.intervalle_ms() if intervalle_ms is None else intervalle_ms
        self.resultats: list[ResultatSite] = []
        self._reponse: QNetworkReply | None = None
        self._annulee = False
        self._essais = 0

    def demarrer(self) -> None:
        self.progression(0, len(self.sites))
        self._suivant()

    def annuler(self) -> None:
        self._annulee = True
        if self._reponse is not None:
            self._reponse.abort()

    # --- Enchaînement ---------------------------------------------------------------------------

    def _suivant(self) -> None:
        if self._annulee:
            return
        if len(self.resultats) >= len(self.sites):
            self.termine(self.resultats, None)
            return
        site = self.sites[len(self.resultats)]
        self._essais = 0
        self._enrichir(ResultatSite(site, complementaires_depuis_cnig(site)))

    def _enrichir(self, resultat: ResultatSite) -> None:
        self._poster(
            "/enrichissement",
            {"identifiants": resultat.site.parcelles},
            lambda donnees: self._calculer(resultat, donnees),
            lambda erreur: self._echec(resultat, erreur, lambda: self._enrichir(resultat)),
        )

    def _calculer(self, resultat: ResultatSite, enrichissement: Json) -> None:
        resultat.enrichissement = enrichissement
        self._essais = 0
        self._poster(
            "/evaluation/calculer",
            {"donneesEnrichies": enrichissement, "donneesComplementaires": resultat.complementaires},
            lambda donnees: self._site_termine(resultat, donnees),
            lambda erreur: self._echec(resultat, erreur, lambda: self._calculer(resultat, enrichissement)),
        )

    def _site_termine(self, resultat: ResultatSite, mutabilite: Json | None) -> None:
        resultat.mutabilite = mutabilite
        self.resultats.append(resultat)
        self.progression(len(self.resultats), len(self.sites))
        QTimer.singleShot(self.intervalle_ms, self._suivant)

    def _echec(self, resultat: ResultatSite, erreur: ErreurApi, reessayer: Callable[[], None]) -> None:
        if self._annulee:
            return
        if erreur.bloquante:
            self.termine(self.resultats, erreur)
            return
        # Limite de débit : on patiente plutôt que de perdre le site
        if "429" in erreur.message and self._essais < ESSAIS_DEBIT:
            self._essais += 1
            QTimer.singleShot(ATTENTE_DEBIT_MS, reessayer)
            return
        if erreur.message == MESSAGE_DELAI and self._essais < ESSAIS_DELAI:
            self._essais += 1
            QTimer.singleShot(self.intervalle_ms, reessayer)
            return
        resultat.erreur = erreur.message
        self._site_termine(resultat, None)

    # --- HTTP -----------------------------------------------------------------------------------

    def _poster(
        self, chemin: str, corps: Json, succes: Callable[[Json], None], echec: Callable[[ErreurApi], None]
    ) -> None:
        requete = QNetworkRequest(QUrl(self.url + chemin))
        requete.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        requete.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, self.agent)
        # L'API identifie un intégrateur serveur à son en-tête Origin
        requete.setRawHeader(b"Origin", self.origine.encode("utf-8"))
        requete.setTransferTimeout(DELAI_REQUETE_MS)
        reponse = QgsNetworkAccessManager.instance().post(requete, json.dumps(corps).encode("utf-8"))
        self._reponse = reponse

        def recu() -> None:
            self._reponse = None
            statut = int(reponse.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0)
            # Une requête interrompue n'a plus de corps à lire
            contenu = bytes(reponse.readAll()) if reponse.isOpen() else b""
            erreur_reseau = reponse.errorString()
            delai_depasse = reponse.error() in ERREURS_DELAI
            reponse.deleteLater()
            if self._annulee:
                return
            if 200 <= statut < 300:
                try:
                    donnees = json.loads(contenu.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    echec(ErreurApi("Réponse illisible de l'API."))
                    return
                succes(donnees)
            else:
                echec(message_http(statut, contenu, erreur_reseau, delai_depasse))

        reponse.finished.connect(recu)
