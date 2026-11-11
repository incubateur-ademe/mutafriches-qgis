"""Réglages de l'extension, déclarés dans l'arbre de QGIS (`plugins/mutafriches/...`).

Déclarés, ils apparaissent avec leur description dans Préférences › Options › Avancé, et sont
modifiables par la page « Mutafriches » des options (`ui/options.py`). ADR-0004.
"""

import os

from qgis.core import (
    QgsSettings,
    QgsSettingsEntryBool,
    QgsSettingsEntryInteger,
    QgsSettingsEntryString,
    QgsSettingsTree,
)

NOM_NOEUD = "mutafriches"
PRODUCTION = "production"
STAGING = "staging"
DEMONSTRATION = "demonstration"
ENVIRONNEMENTS = (PRODUCTION, STAGING, DEMONSTRATION)
# Origine conventionnelle de l'extension, à déclarer dans ALLOWED_INTEGRATOR_ORIGINS sur chaque
# environnement : elle sert d'identifiant d'intégrateur (docs/acces-api-integrateur.md de Mutafriches)
ORIGINE_DEFAUT = "https://qgis.mutafriches.beta.gouv.fr"
# Deux requêtes par site et 100 requêtes par minute et par IP : un site toutes les 1,5 s au plus
INTERVALLE_DEFAUT_MS = 1500
VARIABLE_DEV = "MUTAFRICHES_DEV"

# Un rechargement de l'extension réimporte ce module : repartir d'un nœud neuf
QgsSettingsTree.unregisterPluginTreeNode(NOM_NOEUD)
_racine = QgsSettingsTree.createPluginTreeNode(NOM_NOEUD)
_api = _racine.createChildNode("api")
_utilisateur = _racine.createChildNode("utilisateur")
_carte = _racine.createChildNode("carte")

ENVIRONNEMENT = QgsSettingsEntryString(
    "environnement",
    _api,
    PRODUCTION,
    "Service interrogé : production, staging (équipe) ou demonstration (données figées).",
)
URL = QgsSettingsEntryString(
    "url", _api, "", "Adresse d'API libre (serveur local, tests). Vide : adresse de l'environnement choisi."
)
ORIGINE = QgsSettingsEntryString(
    "origine", _api, ORIGINE_DEFAUT, "En-tête Origin envoyé à l'API : identifie l'extension côté Mutafriches."
)
INTERVALLE_MS = QgsSettingsEntryInteger(
    "intervalle_ms",
    _api,
    INTERVALLE_DEFAUT_MS,
    "Délai entre deux sites, en millisecondes. Ne pas descendre sous 1500 sur une API réelle (limite de débit).",
)
DEV = QgsSettingsEntryBool(
    "dev", _racine, False, "Mode développeur : donne accès au staging et aux réglages d'API dans les options."
)
STRUCTURE = QgsSettingsEntryString("structure", _utilisateur, "", "Structure de l'utilisateur, saisie à l'accueil.")
MAIL = QgsSettingsEntryString("mail", _utilisateur, "", "Adresse mail de l'utilisateur, saisie à l'accueil.")
CONSENTEMENT = QgsSettingsEntryBool(
    "consentement", _utilisateur, False, "Accord pour être contacté par l'équipe Mutafriches."
)
FOND_OSM = QgsSettingsEntryBool(
    "fond_osm", _carte, True, "Ajouter un fond OpenStreetMap à l'ouverture du panneau sur un projet vide."
)

# Clés d'avant la version 0.2.0, hors de l'arbre de QGIS : reprises une fois, puis effacées
_ANCIENNES_CLES: tuple[tuple[str, QgsSettingsEntryString | QgsSettingsEntryBool | QgsSettingsEntryInteger], ...] = (
    ("mutafriches/api/environnement", ENVIRONNEMENT),
    ("mutafriches/api/url", URL),
    ("mutafriches/api/origine", ORIGINE),
    ("mutafriches/api/intervalle_ms", INTERVALLE_MS),
    ("mutafriches/dev", DEV),
    ("mutafriches/utilisateur/structure", STRUCTURE),
    ("mutafriches/utilisateur/mail", MAIL),
    ("mutafriches/utilisateur/consentement", CONSENTEMENT),
)


def migrer_anciens_reglages() -> int:
    """Reprend les réglages des versions 0.1.x ; renvoie le nombre de valeurs reprises."""
    reglages = QgsSettings()
    reprises = 0
    for ancienne, entree in _ANCIENNES_CLES:
        if not reglages.contains(ancienne):
            continue
        valeur = reglages.value(ancienne)
        if not entree.exists():
            if isinstance(entree, QgsSettingsEntryBool):
                entree.setValue(str(valeur).lower() == "true")
            elif isinstance(entree, QgsSettingsEntryInteger):
                entree.setValue(int(valeur))
            else:
                entree.setValue(str(valeur))
            reprises += 1
        reglages.remove(ancienne)
    # La démonstration s'appelait « demo » avant les environnements
    if ENVIRONNEMENT.value() not in ENVIRONNEMENTS:
        ENVIRONNEMENT.remove()
    return reprises


def environnement() -> str:
    valeur = ENVIRONNEMENT.value()
    # Le staging n'est accessible qu'à l'équipe : sans mode développeur, retour à la production
    if valeur == STAGING and not mode_developpeur():
        return PRODUCTION
    return valeur if valeur in ENVIRONNEMENTS else PRODUCTION


def mode_developpeur() -> bool:
    return DEV.value() or os.environ.get(VARIABLE_DEV, "") not in ("", "0", "false")


def url_personnalisee() -> str:
    return URL.value().strip().rstrip("/") if mode_developpeur() else ""


def origine() -> str:
    return ORIGINE.value().strip() or ORIGINE_DEFAUT


def intervalle_ms() -> int:
    return max(0, INTERVALLE_MS.value())


def effacer_utilisateur() -> None:
    for entree in (STRUCTURE, MAIL, CONSENTEMENT):
        entree.remove()


def retirer_de_l_arbre() -> None:
    """À la désactivation de l'extension : ses réglages restent enregistrés, seul l'arbre est nettoyé."""
    QgsSettingsTree.unregisterPluginTreeNode(NOM_NOEUD)
