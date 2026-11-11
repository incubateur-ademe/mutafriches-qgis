import unittest

import serveur_factice
from _qgis import RACINE  # noqa: F401  (initialise QGIS)
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QEventLoop, QTimer

from mutafriches.core.attributaire import FICHIER_CNIG_EXEMPLE, site_depuis_api, synthese
from mutafriches.core.client_api import CLE_ORIGINE, CLE_URL, AnalyseInventaire, ErreurApi, ResultatSite
from mutafriches.core.cnig import SiteCnig, complementaires_depuis_cnig, lire_cnig


def analyser(sites: list[SiteCnig]) -> tuple[list[ResultatSite], ErreurApi | None, list[tuple[int, int]]]:
    boucle = QEventLoop()
    sortie: dict[str, object] = {}
    etapes: list[tuple[int, int]] = []

    def termine(resultats: list[ResultatSite], erreur: ErreurApi | None) -> None:
        sortie["resultats"], sortie["erreur"] = resultats, erreur
        boucle.quit()

    analyse = AnalyseInventaire(sites, lambda a, b: etapes.append((a, b)), termine, "test", intervalle_ms=0)
    analyse.demarrer()
    QTimer.singleShot(20000, boucle.quit)
    boucle.exec()
    return sortie.get("resultats", []), sortie.get("erreur"), etapes  # type: ignore[return-value]


class TestClientApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.serveur = serveur_factice.demarrer()
        QgsSettings().setValue(CLE_URL, f"http://127.0.0.1:{cls.serveur.server_address[1]}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.shutdown()
        QgsSettings().remove(CLE_URL)
        QgsSettings().remove(CLE_ORIGINE)

    def setUp(self) -> None:
        QgsSettings().remove(CLE_ORIGINE)
        self.sites = lire_cnig(FICHIER_CNIG_EXEMPLE).sites_ok

    def test_inventaire_analyse_site_par_site(self) -> None:
        resultats, erreur, etapes = analyser(self.sites[:5])
        self.assertIsNone(erreur)
        self.assertEqual(len(resultats), 5)
        self.assertTrue(all(r.ok for r in resultats))
        self.assertEqual(etapes[0], (0, 5))
        self.assertEqual(etapes[-1], (5, 5))
        r = resultats[0]
        site = site_depuis_api(
            r.site.site_id, r.site.site_nom, r.site.parcelles, r.enrichissement, r.mutabilite, r.complementaires
        )
        self.assertEqual(site.code_insee, "77305")
        self.assertEqual(len(site.indices), 7)
        self.assertEqual(site.indice_max, max(v for u, v in site.indices.items() if u not in site.usages_exclus))
        self.assertTrue(site.fiabilite_niveau)
        self.assertIsNotNone(site.geometrie)
        s = synthese([site], {"provenance": "API"})
        self.assertEqual((s.commune, s.provenance), ("Montereau-Fault-Yonne", "API"))

    def test_echec_d_un_site_sans_arreter_les_autres(self) -> None:
        inconnu = SiteCnig("X", "Site inconnu", "77305", [serveur_factice.PARCELLE_EN_ECHEC], 99)
        resultats, erreur, _ = analyser([self.sites[0], inconnu, self.sites[1]])
        self.assertIsNone(erreur)
        self.assertEqual([r.ok for r in resultats], [True, False, True])
        self.assertIn("Parcelle introuvable", resultats[1].erreur)

    def test_delai_depasse_reessaye_puis_ecarte_le_site_seul(self) -> None:
        from qgis.core import QgsNetworkAccessManager

        ancien = QgsNetworkAccessManager.timeout()
        QgsNetworkAccessManager.setTimeout(1000)
        try:
            lent = SiteCnig("L", "Site lent", "77305", [serveur_factice.PARCELLE_TROP_LENTE], 98)
            rattrape = SiteCnig("R", "Site rattrapé", "77305", [serveur_factice.PARCELLE_LENTE_UNE_FOIS], 97)
            resultats, erreur, _ = analyser([lent, rattrape, self.sites[0]])
        finally:
            QgsNetworkAccessManager.setTimeout(ancien)
        self.assertIsNone(erreur)
        self.assertEqual([r.ok for r in resultats], [False, True, True])
        self.assertIn("Délai dépassé", resultats[0].erreur)

    def test_origine_non_autorisee_arrete_l_inventaire(self) -> None:
        QgsSettings().setValue(CLE_ORIGINE, "https://autre.exemple.fr")
        resultats, erreur, _ = analyser(self.sites[:3])
        self.assertEqual(resultats, [])
        self.assertIsNotNone(erreur)
        self.assertTrue(erreur.bloquante)
        self.assertIn("Accès refusé", erreur.message)

    def test_api_injoignable(self) -> None:
        QgsSettings().setValue(CLE_URL, "http://127.0.0.1:9")
        try:
            resultats, erreur, _ = analyser(self.sites[:1])
        finally:
            QgsSettings().setValue(CLE_URL, f"http://127.0.0.1:{self.serveur.server_address[1]}")
        self.assertEqual(resultats, [])
        self.assertTrue(erreur is not None and erreur.bloquante)


class TestEnvironnements(unittest.TestCase):
    def tearDown(self) -> None:
        for cle in ("mutafriches/api/environnement", "mutafriches/dev"):
            QgsSettings().remove(cle)

    def test_adresse_par_environnement(self) -> None:
        from mutafriches.core.client_api import (
            STAGING,
            definir_environnement_api,
            environnement_api,
            mode_developpeur,
            url_api,
        )

        self.assertEqual(environnement_api(), "production")
        self.assertEqual(url_api(), "https://mutafriches.beta.gouv.fr")
        definir_environnement_api(STAGING)
        self.assertEqual(url_api(), "https://mutafriches.incubateur.ademe.dev")
        # Une adresse personnalisée (tests, serveur local) prend le pas sur l'environnement
        QgsSettings().setValue(CLE_URL, "http://127.0.0.1:1/")
        self.assertEqual(url_api(), "http://127.0.0.1:1")
        QgsSettings().remove(CLE_URL)
        QgsSettings().setValue("mutafriches/api/environnement", "inconnu")
        self.assertEqual(environnement_api(), "production")
        self.assertFalse(mode_developpeur())
        QgsSettings().setValue("mutafriches/dev", "true")
        self.assertTrue(mode_developpeur())


class TestComplementairesCnig(unittest.TestCase):
    def site(self, **valeurs: str) -> SiteCnig:
        return SiteCnig("A", "A", "77305", ["77305000AB0160"], 2, valeurs=valeurs)

    def test_neuf_criteres_toujours_presents(self) -> None:
        reponses = complementaires_depuis_cnig(self.site())
        self.assertEqual(len(reponses), 9)
        self.assertEqual(set(reponses.values()), {"ne-sait-pas"})

    def test_valeurs_sans_ambiguite_seulement(self) -> None:
        reponses = complementaires_depuis_cnig(
            self.site(
                bati_etat="Dégradation moyenne", bati_patrimoine="aucun", sol_pollution_existe="pollution traitée"
            )
        )
        self.assertEqual(reponses["etatBatiInfrastructure"], "degradation-moyenne")
        self.assertEqual(reponses["valeurArchitecturaleHistorique"], "ne-sait-pas")
        self.assertEqual(reponses["presencePollution"], "deja-geree")

    def test_pas_de_bati_vaut_pour_les_deux_criteres(self) -> None:
        reponses = complementaires_depuis_cnig(self.site(bati_etat="sans objet"))
        self.assertEqual(reponses["etatBatiInfrastructure"], "pas-de-bati")
        self.assertEqual(reponses["valeurArchitecturaleHistorique"], "pas-de-bati")

    def test_amiante(self) -> None:
        reponses = complementaires_depuis_cnig(
            self.site(sol_pollution_existe="pollution avérée", bati_pollution="amiante")
        )
        self.assertEqual(reponses["presencePollution"], "oui-amiante")
        reponses = complementaires_depuis_cnig(self.site(sol_pollution_existe="pollution avérée"))
        self.assertEqual(reponses["presencePollution"], "ne-sait-pas")


if __name__ == "__main__":
    unittest.main()
