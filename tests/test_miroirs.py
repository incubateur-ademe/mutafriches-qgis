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
from mutafriches.core.referentiel import CLES_TERRAIN, USAGES

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


if __name__ == "__main__":
    unittest.main()
