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
# Origine commune aux versions d'avant la déclaration par structure : toujours acceptée, elle ne
# sert plus qu'avec une API sans registre des intégrateurs (core/declaration.py)
ORIGINE_HISTORIQUE = "https://qgis.mutafriches.beta.gouv.fr"
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
    "Service interrogé : production, staging (environnement de test) ou demonstration (données figées).",
)
URL = QgsSettingsEntryString(
    "url", _api, "", "Adresse d'API libre (serveur local, tests). Vide : adresse de l'environnement choisi."
)
DECLARATIONS = QgsSettingsEntryString(
    "declarations",
    _api,
    "",
    "Origine obtenue en déclarant la structure, par adresse d'API (JSON). Vide : déclaration à la prochaine analyse.",
)
INTERVALLE_MS = QgsSettingsEntryInteger(
    "intervalle_ms",
    _api,
    INTERVALLE_DEFAUT_MS,
    "Délai entre deux sites, en millisecondes. Ne pas descendre sous 1500 sur une API réelle (limite de débit).",
)
DEV = QgsSettingsEntryBool(
    "dev",
    _racine,
    False,
    "Mode développeur : donne accès aux réglages d'API (adresse libre, délai) dans les options.",
)
# Déclaration de la structure (ADR-0055 de Mutafriches) : prénom, nom et mail partent chez Brevo
PRENOM = QgsSettingsEntryString("prenom", _utilisateur, "", "Prénom du déclarant.")
NOM = QgsSettingsEntryString("nom", _utilisateur, "", "Nom du déclarant.")
STRUCTURE = QgsSettingsEntryString("structure", _utilisateur, "", "Nom de la structure déclarée.")
TYPE_STRUCTURE = QgsSettingsEntryString(
    "type_structure", _utilisateur, "", "Type de la structure (collectivite, bureau_etudes…)."
)
DOMAINE = QgsSettingsEntryString(
    "domaine", _utilisateur, "", "Domaine de la structure, envoyé dans l'en-tête Origin (ma-collectivite.fr)."
)
MAIL = QgsSettingsEntryString("mail", _utilisateur, "", "Adresse e-mail de contact du déclarant.")
FOND_OSM = QgsSettingsEntryBool(
    "fond_osm", _carte, True, "Ajouter un fond OpenStreetMap à l'ouverture du panneau sur un projet vide."
)

# Clés d'avant la version 0.2.0, hors de l'arbre de QGIS : reprises une fois, puis effacées
_ANCIENNES_CLES: tuple[tuple[str, QgsSettingsEntryString | QgsSettingsEntryBool | QgsSettingsEntryInteger], ...] = (
    ("mutafriches/api/environnement", ENVIRONNEMENT),
    ("mutafriches/api/url", URL),
    ("mutafriches/api/intervalle_ms", INTERVALLE_MS),
    ("mutafriches/dev", DEV),
    ("mutafriches/utilisateur/structure", STRUCTURE),
    ("mutafriches/utilisateur/mail", MAIL),
)
# Réglages retirés : origine libre (remplacée par la déclaration), consentement et accueil passé
_CLES_OBSOLETES = (
    "mutafriches/api/origine",
    "mutafriches/utilisateur/consentement",
    "plugins/mutafriches/api/origine",
    "plugins/mutafriches/utilisateur/consentement",
    "plugins/mutafriches/utilisateur/accueil_vu",
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
    for obsolete in _CLES_OBSOLETES:
        reglages.remove(obsolete)
    # La démonstration s'appelait « demo » avant les environnements
    if ENVIRONNEMENT.value() not in ENVIRONNEMENTS:
        ENVIRONNEMENT.remove()
    return reprises


def environnement() -> str:
    valeur = ENVIRONNEMENT.value()
    return valeur if valeur in ENVIRONNEMENTS else PRODUCTION


def mode_developpeur() -> bool:
    return DEV.value() or os.environ.get(VARIABLE_DEV, "") not in ("", "0", "false")


def url_personnalisee() -> str:
    return URL.value().strip().rstrip("/") if mode_developpeur() else ""


def intervalle_ms() -> int:
    return max(0, INTERVALLE_MS.value())


def effacer_utilisateur() -> None:
    for entree in (PRENOM, NOM, STRUCTURE, TYPE_STRUCTURE, DOMAINE, MAIL, DECLARATIONS):
        entree.remove()


def retirer_de_l_arbre() -> None:
    """À la désactivation de l'extension : ses réglages restent enregistrés, seul l'arbre est nettoyé."""
    QgsSettingsTree.unregisterPluginTreeNode(NOM_NOEUD)
