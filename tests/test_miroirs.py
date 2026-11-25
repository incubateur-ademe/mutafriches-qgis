"""Les constantes recopiées de Mutafriches (shared-types) doivent rester identiques à leur source.

Lit le dépôt voisin (`../mutafriches`, ou la variable MUTAFRICHES_DEPOT) ; ignoré s'il est absent.
"""

import os
import re
import unittest
from pathlib import Path

from _qgis import RACINE

from mutafriches.core.attributaire import NIVEAUX_FIABILITE
from mutafriches.core.cnig import CHAMPS_COMPLEMENTAIRES, COLONNES_CNIG
from mutafriches.core.declaration import (
    EN_TETE_CLIENT,
    FORMAT_NOM_DOMAINE,
    PREFIXE_CLIENT_QGIS,
    TYPES_STRUCTURE,
    hote_de_domaine,
)
from mutafriches.core.referentiel import CLES_TERRAIN, USAGES
from mutafriches.ui import contenus

DEPOT = Path(os.environ.get("MUTAFRICHES_DEPOT") or Path(RACINE).parent / "mutafriches")
TYPES = DEPOT / "packages" / "shared-types" / "src"


def bloc(fichier: str, constante: str) -> str:
    """Corps de la déclaration `export const <constante> ... = [ ou {` jusqu'à sa fermeture."""
    source = (TYPES / fichier).read_text(encoding="utf-8")
    debut = re.search(rf"export const {constante}\b[^=]*=\s*[\[{{]", source)
    assert debut is not None, f"{constante} introuvable dans {fichier}"
    ouvrant = source[debut.end() - 1]
    fermant = "]" if ouvrant == "[" else "}"
    niveau, position = 1, debut.end()
    while niveau and position < len(source):
        niveau += {ouvrant: 1, fermant: -1}.get(source[position], 0)
        position += 1
    return source[debut.end() : position - 1]


def chaines(texte: str) -> list[str]:
    return re.findall(r'"([^"]*)"', texte)


@unittest.skipUnless(TYPES.is_dir(), f"dépôt Mutafriches absent ({DEPOT})")
class TestMiroirs(unittest.TestCase):
    def test_colonnes_cnig(self) -> None:
        self.assertEqual(list(COLONNES_CNIG), chaines(bloc("cnig/friche-cnig.types.ts", "COLONNES_FRICHE_CNIG")))

    def test_criteres_manuels(self) -> None:
        requis = chaines(
            bloc("evaluation/utils/donnees-complementaires.validation.ts", "CHAMPS_COMPLEMENTAIRES_REQUIS")
        )
        self.assertEqual(list(CHAMPS_COMPLEMENTAIRES), requis)
        self.assertEqual(sorted(CLES_TERRAIN), sorted(requis))

    def test_libelles_des_usages(self) -> None:
        corps = bloc("evaluation/constants/usages.constants.ts", "USAGE_LABELS")
        libelles = dict(re.findall(r'UsageType\.(\w+)\]:\s*"([^"]*)"', corps))
        self.assertEqual(USAGES, {cle.lower(): libelle for cle, libelle in libelles.items()})

    def test_niveaux_de_fiabilite(self) -> None:
        corps = bloc("evaluation/constants/fiabilite.constants.ts", "NIVEAUX_FIABILITE")
        self.assertEqual(list(NIVEAUX_FIABILITE), re.findall(r'text:\s*"([^"]*)"', corps))

    def test_types_de_structure(self) -> None:
        corps = bloc("integration/declaration-integrateur.ts", "TYPE_STRUCTURE_LABELS")
        self.assertEqual(TYPES_STRUCTURE, dict(re.findall(r'(\w+):\s*"([^"]*)"', corps)))

    def test_en_tete_client_et_format_de_domaine(self) -> None:
        source = (TYPES / "integration" / "declaration-integrateur.ts").read_text(encoding="utf-8")
        self.assertIn(f'EN_TETE_CLIENT_MUTAFRICHES = "{EN_TETE_CLIENT}"', source)
        self.assertIn(f'PREFIXE_CLIENT_QGIS = "{PREFIXE_CLIENT_QGIS}"', source)
        format_ts = re.search(r"FORMAT_NOM_DOMAINE =\s*/(.+)/;", source)
        assert format_ts is not None
        self.assertEqual(FORMAT_NOM_DOMAINE.pattern, format_ts.group(1))

    def test_regle_de_domaine_sur_les_cas_de_shared_types(self) -> None:
        spec = (TYPES / "integration" / "declaration-integrateur.spec.ts").read_text(encoding="utf-8")
        # Deux tableaux de cas, chacun clos par « ])( » : saisies acceptées, puis refusées
        acceptes, refuses = spec.split("])(")[:2]
        paires = re.findall(r'\["([^"]*)", "([^"]*)"\]', acceptes)
        self.assertGreater(len(paires), 5)
        for saisie, hote in paires:
            self.assertEqual(hote_de_domaine(saisie), hote, saisie)
        cas_refuses = re.findall(r'\["([^"]*)", "[^"]*"\]', refuses)
        self.assertGreater(len(cas_refuses), 15)
        for saisie in [*cas_refuses, "a" * 64 + ".fr"]:
            self.assertIsNone(hote_de_domaine(saisie), saisie)

    def test_libelle_du_consentement(self) -> None:
        source = DEPOT / "apps" / "ui" / "src" / "features" / "integrer" / "data" / "declaration-integrateur.ts"
        texte_source = source.read_text(encoding="utf-8") if source.is_file() else ""
        trouve = re.search(r'LIBELLE_CONSENTEMENT_CONTACT =\s*"([^"]*)"', texte_source)
        if trouve is None:
            self.skipTest("LIBELLE_CONSENTEMENT_CONTACT absent : PR 285 de Mutafriches pas encore fusionnée")
        self.assertEqual(contenus.LIBELLE_ACCEPTE_CONTACT, trouve.group(1))


if __name__ == "__main__":
    unittest.main()
