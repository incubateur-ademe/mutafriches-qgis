import unittest
from pathlib import Path

from _qgis import RACINE  # noqa: F401  (initialise QGIS)
from qgis.core import QgsCategorizedSymbolRenderer, QgsProject

from mutafriches.carto.couches import NOM_COUCHE_MUTABILITE, champs_mutabilite, creer_couches
from mutafriches.core.attributaire import (
    FICHIER_CNIG_ERREURS,
    FICHIER_CNIG_EXEMPLE,
    FICHIER_MODELE_CNIG,
    ORDRE_USAGES,
    apparier,
    charger_table,
    profil_ecart,
    synthese,
)
from mutafriches.core.cnig import lire_cnig


class TestCnig(unittest.TestCase):
    def test_exemple_montereau_valide(self) -> None:
        lecture = lire_cnig(FICHIER_CNIG_EXEMPLE)
        self.assertTrue(lecture.valide, [p.message for p in lecture.problemes])
        self.assertEqual(len(lecture.sites), 28)
        self.assertEqual(len(lecture.colonnes), 51)
        self.assertEqual(lecture.sites[0].comm_insee, "77305")
        self.assertTrue(all(s.parcelles for s in lecture.sites))

    def test_lignes_en_erreur_ecartees_sans_refuser_le_fichier(self) -> None:
        lecture = lire_cnig(FICHIER_CNIG_ERREURS)
        self.assertTrue(lecture.valide)
        self.assertEqual((len(lecture.sites_ok), len(lecture.sites_ko)), (4, 6))
        erreurs = {s.ligne: s.erreurs for s in lecture.sites_ko}
        self.assertIn("déjà utilisé ligne 3", erreurs[4][0])
        self.assertIn("mal formée", erreurs[5][0])
        self.assertEqual(erreurs[7], ["site_nom vide"])
        self.assertIn("comm_insee", erreurs[8][0])
        self.assertEqual(erreurs[9], ["geompoint vide"])
        self.assertEqual(erreurs[10], ["unite_fonciere_refcad vide"])

    def test_modele_fictif_valide_mais_hors_table(self) -> None:
        lecture = lire_cnig(FICHIER_MODELE_CNIG)
        self.assertTrue(lecture.valide)
        self.assertEqual(len(lecture.sites_ok), 3)
        self.assertTrue(all(s.comm_insee == "99999" for s in lecture.sites))
        sites, _ = charger_table()
        self.assertEqual(apparier(sites, {s.site_id: s.parcelles for s in lecture.sites}), [])

    def test_erreurs_ligne_a_ligne(self) -> None:
        chemin = Path(RACINE) / "dist" / "test-cnig.csv"
        chemin.parent.mkdir(exist_ok=True)
        chemin.write_text(
            "site_id,site_nom,comm_insee,unite_fonciere_refcad,geompoint\n"
            "A,Site A,77305,77305000AB0160|77305000AB0161,POINT(48 2)\n"
            "A,,7730,AB 160,\n",
            encoding="utf-8",
        )
        lecture = lire_cnig(chemin)
        self.assertTrue(lecture.valide)
        self.assertEqual([s.ligne for s in lecture.sites_ko], [3])
        self.assertEqual(len(lecture.sites_ko[0].erreurs), 5)

    def test_format_inconnu(self) -> None:
        lecture = lire_cnig(Path("sites.xlsx"))
        self.assertFalse(lecture.valide)
        self.assertEqual(len(lecture.problemes), 1)


class TestAttributaire(unittest.TestCase):
    def test_table_figee_et_synthese(self) -> None:
        sites, meta = charger_table()
        self.assertEqual(len(sites), 28)
        s = synthese(sites, meta)
        self.assertEqual(s.commune, "Montereau-Fault-Yonne")
        self.assertEqual(sum(s.par_usage.values()), 28)
        self.assertEqual(sum(s.par_fiabilite.values()), 28)
        self.assertEqual(sum(s.par_profil.values()), 28)
        self.assertEqual(list(s.par_usage), list(ORDRE_USAGES))
        self.assertTrue(all(s.indice_max >= 70 for s in s.sites_forte_compatibilite))
        self.assertEqual(s.version_algorithme, "v1.19")

    def test_appariement_par_parcelles(self) -> None:
        sites, _ = charger_table()
        lecture = lire_cnig(FICHIER_CNIG_EXEMPLE)
        apparies = apparier(sites, {s.site_id: s.parcelles for s in lecture.sites})
        self.assertEqual(len(apparies), 28)
        self.assertTrue(all(s.site_id.startswith("77305_") for s in apparies))

    def test_profils(self) -> None:
        self.assertEqual(profil_ecart(5)[0], "Profil plat")
        self.assertEqual(profil_ecart(24.9)[0], "Contraste net")
        self.assertEqual(profil_ecart(40)[0], "Fort contraste")


class TestCouches(unittest.TestCase):
    def test_colonnes_mutabilite_dans_l_ordre_demande(self) -> None:
        noms = [c.name() for c in champs_mutabilite()]
        self.assertEqual(
            noms[:5],
            ["site_id", "site_nom", "mf_usage_prioritaire", "mf_usage_prioritaire_lib", "mf_indice_prioritaire"],
        )
        self.assertEqual(noms[5:12], [f"mf_indice_{u}" for u in ORDRE_USAGES])
        self.assertEqual(
            noms[12:],
            [
                "mf_fiabilite",
                "mf_fiabilite_niveau",
                "mf_usages_exclus",
                "nb_parcelles",
                "unite_fonciere_refcad",
                "comm_insee",
                "mf_version_algorithme",
            ],
        )

    def test_couches_et_symbologie(self) -> None:
        sites, _ = charger_table()
        mutabilite, qualification = creer_couches(sites, "test")
        self.assertEqual(mutabilite.featureCount(), 28)
        self.assertEqual(qualification.featureCount(), 28)
        rendu = mutabilite.renderer()
        self.assertIsInstance(rendu, QgsCategorizedSymbolRenderer)
        self.assertEqual(len(rendu.categories()), 8)
        self.assertTrue(mutabilite.labelsEnabled())
        self.assertEqual(mutabilite.name(), f"{NOM_COUCHE_MUTABILITE} (test)")
        entite = next(mutabilite.getFeatures())
        self.assertTrue(entite["mf_usage_prioritaire"])
        self.assertTrue(QgsProject.instance().mapLayersByName(mutabilite.name()))


if __name__ == "__main__":
    unittest.main()
