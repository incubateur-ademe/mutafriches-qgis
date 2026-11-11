import unittest

import serveur_factice
from _qgis import RACINE  # noqa: F401  (initialise QGIS)
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QEventLoop, QTimer

from mutafriches.core import reglages
from mutafriches.core.attributaire import FICHIER_CNIG_EXEMPLE, site_depuis_api, synthese
from mutafriches.core.client_api import AnalyseInventaire, ErreurApi, ResultatSite, url_api
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
        # Une adresse libre n'est lue qu'en mode développeur
        reglages.DEV.setValue(True)
        reglages.URL.setValue(f"http://127.0.0.1:{cls.serveur.server_address[1]}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.shutdown()
        for entree in (reglages.URL, reglages.ORIGINE, reglages.DEV):
            entree.remove()

    def setUp(self) -> None:
        reglages.ORIGINE.remove()
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

    def test_erreur_serveur_expliquee_et_limitee_au_site(self) -> None:
        inconnu = SiteCnig("I", "Site inconnu du cadastre", "77305", [serveur_factice.PARCELLE_INCONNUE], 96)
        resultats, erreur, _ = analyser([inconnu, self.sites[0]])
        self.assertIsNone(erreur)
        self.assertEqual([r.ok for r in resultats], [False, True])
        self.assertIn("parcelles introuvables au cadastre", resultats[0].erreur)
        self.assertNotIn("500", resultats[0].erreur)

    def test_origine_non_autorisee_arrete_l_inventaire(self) -> None:
        reglages.ORIGINE.setValue("https://autre.exemple.fr")
        resultats, erreur, _ = analyser(self.sites[:3])
        self.assertEqual(resultats, [])
        self.assertIsNotNone(erreur)
        self.assertTrue(erreur.bloquante)
        self.assertIn("Accès refusé", erreur.message)

    def test_api_injoignable(self) -> None:
        reglages.URL.setValue("http://127.0.0.1:9")
        try:
            resultats, erreur, _ = analyser(self.sites[:1])
        finally:
            reglages.URL.setValue(f"http://127.0.0.1:{self.serveur.server_address[1]}")
        self.assertEqual(resultats, [])
        self.assertTrue(erreur is not None and erreur.bloquante)


class TestReglages(unittest.TestCase):
    def setUp(self) -> None:
        self.entrees = (reglages.ENVIRONNEMENT, reglages.DEV, reglages.URL, reglages.STRUCTURE, reglages.MAIL)
        for entree in self.entrees:
            entree.remove()

    tearDown = setUp

    def test_reglages_declares_dans_l_arbre_de_qgis(self) -> None:
        self.assertEqual(reglages.DEV.key(), "/plugins/mutafriches/dev")
        self.assertEqual(reglages.URL.key(), "/plugins/mutafriches/api/url")
        self.assertTrue(reglages.FOND_OSM.value())

    def test_adresse_par_environnement(self) -> None:
        self.assertEqual(reglages.environnement(), "production")
        self.assertEqual(url_api(), "https://mutafriches.beta.gouv.fr")
        reglages.ENVIRONNEMENT.setValue("inconnu")
        self.assertEqual(reglages.environnement(), "production")

    def test_staging_et_adresse_libre_reserves_au_mode_developpeur(self) -> None:
        reglages.ENVIRONNEMENT.setValue("staging")
        reglages.URL.setValue("http://127.0.0.1:1/")
        self.assertEqual(reglages.environnement(), "production")
        self.assertEqual(url_api(), "https://mutafriches.beta.gouv.fr")
        reglages.DEV.setValue(True)
        self.assertEqual(reglages.environnement(), "staging")
        self.assertEqual(url_api(), "http://127.0.0.1:1")
        reglages.URL.remove()
        self.assertEqual(url_api(), "https://mutafriches.incubateur.ademe.dev")

    def test_reprise_des_reglages_0_1(self) -> None:
        anciens = QgsSettings()
        anciens.setValue("mutafriches/utilisateur/structure", "CC du Pays de Montereau")
        anciens.setValue("mutafriches/utilisateur/mail", "sig@exemple.fr")
        anciens.setValue("mutafriches/dev", "true")
        anciens.setValue("mutafriches/api/environnement", "demo")
        self.assertEqual(reglages.migrer_anciens_reglages(), 4)
        self.assertEqual(
            (reglages.STRUCTURE.value(), reglages.MAIL.value()), ("CC du Pays de Montereau", "sig@exemple.fr")
        )
        self.assertTrue(reglages.DEV.value())
        self.assertEqual(reglages.environnement(), "production")
        self.assertFalse(anciens.contains("mutafriches/utilisateur/mail"))
        self.assertEqual(reglages.migrer_anciens_reglages(), 0)


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
