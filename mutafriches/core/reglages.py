"""Réglages de l'extension, déclarés dans l'arbre de QGIS (`plugins/mutafriches/...`).

Déclarés, ils apparaissent avec leur description dans Préférences › Options › Avancé ; la page
« Mutafriches » des options (`ui/options.py`) en montre l'essentiel. ADR-0004, ADR-0006.
"""

import os

from qgis.core import (
    QgsSettings,
    QgsSettingsEntryBool,
    QgsSettingsEntryString,
    QgsSettingsTree,
)

NOM_NOEUD = "mutafriches"
# Seule API interrogée : aucun réglage ni option ne permet d'en changer (ADR-0006)
URL_PRODUCTION = "https://mutafriches.beta.gouv.fr"
# Tests et captures de l'équipe : une autre API ne se désigne qu'au lancement de QGIS
VARIABLE_API = "MUTAFRICHES_API_URL"
VARIABLE_INTERVALLE = "MUTAFRICHES_INTERVALLE_MS"
# Origine commune aux versions d'avant la déclaration par structure : toujours acceptée, elle ne
# sert plus qu'avec une API sans registre des intégrateurs (core/declaration.py)
ORIGINE_HISTORIQUE = "https://qgis.mutafriches.beta.gouv.fr"
# Deux requêtes par site et 100 requêtes par minute et par IP : un site toutes les 1,5 s au plus
INTERVALLE_DEFAUT_MS = 1500

# Un rechargement de l'extension réimporte ce module : repartir d'un nœud neuf
QgsSettingsTree.unregisterPluginTreeNode(NOM_NOEUD)
_racine = QgsSettingsTree.createPluginTreeNode(NOM_NOEUD)
_api = _racine.createChildNode("api")
_utilisateur = _racine.createChildNode("utilisateur")
_carte = _racine.createChildNode("carte")

DECLARATIONS = QgsSettingsEntryString(
    "declarations",
    _api,
    "",
    "Origine obtenue en déclarant la structure, par adresse d'API (JSON). Vide : déclaration à la prochaine analyse.",
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
# Distinct de l'e-mail : accord pour être sollicité (ACCEPTE_CONTACT chez Brevo), exigé à l'accueil
ACCEPTE_CONTACT = QgsSettingsEntryBool(
    "accepte_contact",
    _utilisateur,
    False,
    "Accord pour être contacté (retours d'expérience, évolutions du service). Jamais coché par défaut, exigé.",
)
FOND_OSM = QgsSettingsEntryBool(
    "fond_osm", _carte, True, "Ajouter un fond OpenStreetMap à l'ouverture du panneau sur un projet vide."
)

# Clés d'avant la version 0.2.0, hors de l'arbre de QGIS : reprises une fois, puis effacées
_ANCIENNES_CLES: tuple[tuple[str, QgsSettingsEntryString], ...] = (
    ("mutafriches/utilisateur/structure", STRUCTURE),
    ("mutafriches/utilisateur/mail", MAIL),
)
# Réglages retirés : choix d'environnement, adresse d'API libre, délai et mode développeur (ADR-0006),
# origine libre (remplacée par la déclaration), consentement des 0.3.x (libellé et finalité
# différents : jamais repris comme accord de contact) et accueil passé
_CLES_OBSOLETES = (
    "mutafriches/api/environnement",
    "mutafriches/api/url",
    "mutafriches/api/intervalle_ms",
    "mutafriches/api/origine",
    "mutafriches/dev",
    "mutafriches/utilisateur/consentement",
    "plugins/mutafriches/api/environnement",
    "plugins/mutafriches/api/url",
    "plugins/mutafriches/api/intervalle_ms",
    "plugins/mutafriches/api/origine",
    "plugins/mutafriches/dev",
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
        if not entree.exists():
            entree.setValue(str(reglages.value(ancienne)))
            reprises += 1
        reglages.remove(ancienne)
    for obsolete in _CLES_OBSOLETES:
        reglages.remove(obsolete)
    return reprises


def url_de_test() -> str:
    """Adresse d'API posée au lancement de QGIS par les tests et les captures, sinon chaîne vide."""
    valeur = os.environ.get(VARIABLE_API, "").strip().rstrip("/")
    return valeur if valeur.startswith(("http://", "https://")) else ""


def intervalle_ms() -> int:
    # Le délai ne se raccourcit que face à une API de test : la production limite le débit
    if not url_de_test():
        return INTERVALLE_DEFAUT_MS
    try:
        return max(0, int(os.environ.get(VARIABLE_INTERVALLE, "")))
    except ValueError:
        return INTERVALLE_DEFAUT_MS


def effacer_utilisateur() -> None:
    """Tests et remise à zéro (scripts/reinitialiser.sh) : aucune action de l'interface n'y mène."""
    for entree in (PRENOM, NOM, STRUCTURE, TYPE_STRUCTURE, DOMAINE, MAIL, ACCEPTE_CONTACT, DECLARATIONS):
        entree.remove()


def retirer_de_l_arbre() -> None:
    """À la désactivation de l'extension : ses réglages restent enregistrés, seul l'arbre est nettoyé."""
    QgsSettingsTree.unregisterPluginTreeNode(NOM_NOEUD)
