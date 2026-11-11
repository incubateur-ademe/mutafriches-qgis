"""Client de l'API Mutafriches existante : un site = enrichissement puis calcul de mutabilité.

Aucune route par lot ni import d'inventaire côté API : l'extension enchaîne elle-même les
appels, site par site, sous la limite de 100 requêtes par minute (ADR-0003).
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from qgis.core import QgsNetworkAccessManager, QgsSettings
from qgis.PyQt.QtCore import QObject, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from .cnig import SiteCnig, complementaires_depuis_cnig

# Réponse JSON de l'API : structure libre, vérifiée à l'usage
Json = dict[str, Any]

PRODUCTION = "production"
STAGING = "staging"
DEMONSTRATION = "demonstration"
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
# Origine conventionnelle de l'extension, à déclarer dans ALLOWED_INTEGRATOR_ORIGINS sur chaque
# environnement : elle sert d'identifiant d'intégrateur (docs/acces-api-integrateur.md de Mutafriches)
ORIGINE_DEFAUT = "https://qgis.mutafriches.beta.gouv.fr"
CLE_ENVIRONNEMENT = "mutafriches/api/environnement"
# Adresse libre (serveur local, tests) : prend le pas sur celle de l'environnement
CLE_URL = "mutafriches/api/url"
CLE_ORIGINE = "mutafriches/api/origine"
CLE_INTERVALLE = "mutafriches/api/intervalle_ms"
CLE_DEV = "mutafriches/dev"
VARIABLE_DEV = "MUTAFRICHES_DEV"

DELAI_REQUETE_MS = 90_000
# Deux requêtes par site et 100 requêtes par minute et par IP : un site toutes les 1,5 s au plus
INTERVALLE_SITES_MS = 1500
ATTENTE_DEBIT_MS = 20_000
ESSAIS_DEBIT = 2
MESSAGE_DELAI = "Délai dépassé : l'API n'a pas répondu à temps pour ce site."
# Un second essai aboutit souvent : l'API a mis en cache ce qu'elle avait déjà récupéré
ESSAIS_DELAI = 1
ERREURS_DELAI = (QNetworkReply.NetworkError.OperationCanceledError, QNetworkReply.NetworkError.TimeoutError)


def environnement_api() -> str:
    valeur = str(QgsSettings().value(CLE_ENVIRONNEMENT, PRODUCTION))
    return valeur if valeur in LIBELLES_ENVIRONNEMENTS else PRODUCTION


def definir_environnement_api(environnement: str) -> None:
    QgsSettings().setValue(CLE_ENVIRONNEMENT, environnement)


def mode_developpeur() -> bool:
    """Le staging n'est proposé qu'à l'équipe : variable d'environnement ou réglage avancé."""
    reglage = str(QgsSettings().value(CLE_DEV, "false")).lower() == "true"
    return reglage or os.environ.get(VARIABLE_DEV, "") not in ("", "0", "false")


def url_personnalisee() -> str:
    return str(QgsSettings().value(CLE_URL, "") or "").rstrip("/")


def url_api(environnement: str = "") -> str:
    return url_personnalisee() or URLS.get(environnement or environnement_api(), URLS[PRODUCTION])


def intervalle_api() -> int:
    # Réglable pour les tests ; en production, laisser la valeur par défaut (limite de débit)
    return int(QgsSettings().value(CLE_INTERVALLE, INTERVALLE_SITES_MS) or INTERVALLE_SITES_MS)


def origine_api() -> str:
    return str(QgsSettings().value(CLE_ORIGINE, ORIGINE_DEFAUT) or ORIGINE_DEFAUT)


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
        self.origine = origine_api()
        self.agent = f"mutafriches-qgis/{version_extension or 'dev'}"
        self.intervalle_ms = intervalle_api() if intervalle_ms is None else intervalle_ms
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
