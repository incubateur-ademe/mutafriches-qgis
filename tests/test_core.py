import unittest

from _qgis import RACINE  # noqa: F401  (initialise QGIS)
from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer

from mutafriches.carto.selection import analyser, champ_identifiant, libelle_parcelle
from mutafriches.core.recapitulatif import (
    construire_detail_usage,
    construire_recapitulatif,
    deriver_raccordement_eau,
    valeur_etape,
)
from mutafriches.core.referentiel import CLES_TERRAIN, SECTIONS

from mutafriches.core.modele import ParcelleSite, Site
from mutafriches.core.service import ErreurService, ResultatEvaluation
from mutafriches.core.service_simule import ServiceSimule, choisir_point, choisir_variante

STATION = [f"49353000AV{n}" for n in ("1255", "1256", "1257", "1258")]
WKT = "POLYGON((565600 6525600, 565700 6525600, 565700 6525700, 565600 6525700, 565600 6525600))"


def service(mesurer=None) -> ServiceSimule:  # type: ignore[no-untyped-def]
    return ServiceSimule(delai_enrichissement_ms=None, delai_evaluation_ms=None, mesurer=mesurer)


def appeler_enrichir(svc: ServiceSimule, ids: list[str]) -> object:
    sortie: list[object] = []
    svc.enrichir(ids, sortie.append, sortie.append)
    return sortie[0]


def site_usine() -> Site:
    return Site(
        parcelles=[ParcelleSite(i, i[-6:], 4000.0) for i in STATION],
        geometrie_wkt=WKT,
    )


class TestServiceSimule(unittest.TestCase):
    def test_trois_scenarios_figes(self) -> None:
        ids = [s.id for s in service().scenarios]
        self.assertEqual(ids, ["station-service", "pierre-timbaud", "pont-malembert"])

    def test_enrichissement_independant_de_l_ordre(self) -> None:
        resultat = appeler_enrichir(service(), list(reversed(STATION)))
        self.assertIsInstance(resultat, dict)
        self.assertEqual(resultat["nombreParcelles"], 4)  # type: ignore[index]

    def test_parcelle_hors_terrain_non_recuperable(self) -> None:
        resultat = appeler_enrichir(service(mesurer=lambda ids: None), ["87085000ZZ9999"])
        self.assertIsInstance(resultat, ErreurService)
        self.assertFalse(resultat.recuperable)  # type: ignore[union-attr]

    def test_selection_libre_recoit_le_profil_generique(self) -> None:
        svc = service(mesurer=lambda ids: 7200.0)
        enrichissement = appeler_enrichir(svc, ["49353000AV0100"])
        self.assertEqual(enrichissement["surfaceSite"], 7200)  # type: ignore[index]
        self.assertEqual(enrichissement["surfaceBati"], 1440)  # type: ignore[index]
        sortie: list[ResultatEvaluation] = []
        svc.evaluer(enrichissement, {}, sortie.append, self.fail)  # type: ignore[arg-type]
        self.assertIn("8\u202f000 m²", sortie[0].note_simulation or "")
        self.assertEqual(enrichissement["commune"], "Trélazé")  # type: ignore[index]
        self.assertEqual(len(sortie[0].resultat["resultats"]), 7)  # type: ignore[arg-type]

    def test_point_de_grille_le_plus_proche(self) -> None:
        points = service().generique["points"]
        point = choisir_point(points, {"surfaceSite": 11000, "surfaceBati": 5000})  # type: ignore[arg-type]
        self.assertEqual((point["surfaceSite"], point["surfaceBati"]), (12500, 6250))

    def test_erreur_recuperable_puis_succes(self) -> None:
        svc = service()
        ids = ["49353000AV1349", "49353000AV1350"]
        premier = appeler_enrichir(svc, ids)
        self.assertIsInstance(premier, ErreurService)
        self.assertTrue(premier.recuperable)  # type: ignore[union-attr]
        second = appeler_enrichir(svc, ids)
        self.assertIn("surfaceBati", second["champsManquants"])  # type: ignore[index]
        svc.reinitialiser()
        self.assertIsInstance(appeler_enrichir(svc, ids), ErreurService)

    def test_evaluation_sans_saisie_multiparcellaire(self) -> None:
        svc = service()
        enrichissement = appeler_enrichir(svc, STATION)
        sortie: list[ResultatEvaluation] = []
        svc.evaluer(enrichissement, {}, sortie.append, self.fail)  # type: ignore[arg-type]
        self.assertEqual(sortie[0].variante_id, "sans-saisie")
        self.assertEqual(sortie[0].ecarts, 0)
        self.assertEqual(sortie[0].resultat["fiabilite"]["note"], 6.5)  # type: ignore[index]
        self.assertEqual(len(sortie[0].resultat["resultats"]), 7)  # type: ignore[arg-type]

    def test_variante_la_plus_proche_signale_les_ecarts(self) -> None:
        scenario = service().scenarios[0]
        saisie = {"typeProprietaire": "prive", "etatBatiInfrastructure": "degradation-heterogene"}
        _, ecarts = choisir_variante(scenario.evaluations, saisie)
        self.assertEqual(ecarts, 0)
        saisie["presencePollution"] = "non"
        variante, ecarts = choisir_variante(scenario.evaluations, saisie)
        self.assertEqual((variante["id"], ecarts), ("partielle", 1))


class TestModele(unittest.TestCase):
    def test_changer_perimetre_invalide_enrichissement_et_resultats(self) -> None:
        site = site_usine()
        site.enrichissement = {"surfaceSite": 12000}
        site.evaluation = {"resultats": []}
        site.definir_reponse("typeProprietaire", "prive")
        site.changer_perimetre(site.parcelles[:2], WKT)
        self.assertIsNone(site.enrichissement)
        self.assertIsNone(site.evaluation)
        self.assertEqual(site.nombre_reponses, 1)


class TestSelection(unittest.TestCase):
    def couche(self, champs: str, entites: list[tuple[str, str]]) -> QgsVectorLayer:
        couche = QgsVectorLayer(f"Polygon?crs=EPSG:4326{champs}", "test", "memory")
        for valeur, wkt in entites:
            entite = QgsFeature(couche.fields())
            if valeur:
                entite.setAttribute(0, valeur)
            entite.setGeometry(QgsGeometry.fromWkt(wkt))
            couche.dataProvider().addFeatures([entite])
        return couche

    def test_couche_wgs84_avec_identifiant_etalab(self) -> None:
        # Deux carrés de ~0,001° accolés, à Limoges
        a = "POLYGON((1.262 45.822,1.263 45.822,1.263 45.823,1.262 45.823,1.262 45.822))"
        b = "POLYGON((1.263 45.822,1.264 45.822,1.264 45.823,1.263 45.823,1.263 45.822))"
        couche = self.couche("&field=id:string", [("87085000HS0247", a), ("87085000HS0248", b)])
        self.assertEqual(champ_identifiant(couche), "id")
        analyse = analyser(couche, list(couche.getFeatures()))
        self.assertTrue(analyse.valide)
        self.assertEqual([p.libelle for p in analyse.parcelles], ["HS 0247", "HS 0248"])
        # Surface en m² (Lambert 93), pas en degrés carrés
        self.assertTrue(8000 < analyse.parcelles[0].surface_m2 < 9500, analyse.parcelles[0].surface_m2)

    def test_couche_sans_identifiant_et_parcelles_disjointes(self) -> None:
        a = "POLYGON((1.262 45.822,1.263 45.822,1.263 45.823,1.262 45.823,1.262 45.822))"
        c = "POLYGON((1.270 45.822,1.271 45.822,1.271 45.823,1.270 45.823,1.270 45.822))"
        couche = self.couche("&field=nom:string", [("", a), ("", c)])
        self.assertIsNone(champ_identifiant(couche))
        analyse = analyser(couche, list(couche.getFeatures()))
        self.assertFalse(analyse.contigu)
        self.assertTrue(all(p.idu.startswith("test #") for p in analyse.parcelles))

    def test_commune_inconnue_hors_exemple(self) -> None:
        svc = service(mesurer=lambda ids: 900.0)
        enrichissement = appeler_enrichir(svc, ["75056000AB0001"])
        self.assertEqual(enrichissement["commune"], "Code INSEE 75056")  # type: ignore[index]

    def test_format_idu_corse(self) -> None:
        self.assertEqual(libelle_parcelle("2A004000AB0012"), "AB 0012")


class TestRecapitulatif(unittest.TestCase):
    def test_recapitulatif_et_detail_comme_le_web(self) -> None:
        svc = service()
        enrichissement = appeler_enrichir(svc, STATION)
        sortie: list[ResultatEvaluation] = []
        svc.evaluer(enrichissement, {}, sortie.append, self.fail)  # type: ignore[arg-type]
        complementaires = {**{c: "ne-sait-pas" for c in CLES_TERRAIN}, "typeProprietaire": "prive"}
        complementaires["raccordementEau"] = deriver_raccordement_eau(enrichissement["surfaceBati"])  # type: ignore[arg-type, index]
        sections = construire_recapitulatif(enrichissement, complementaires)  # type: ignore[arg-type]
        self.assertEqual([s.titre for s in sections], list(SECTIONS.values()))
        lignes = {l.cle: l for s in sections for l in s.lignes}
        self.assertEqual(lignes["typeProprietaire"].valeur, "Privé")
        self.assertEqual(lignes["qualitePaysage"].valeur, "Ne sait pas")
        self.assertEqual(lignes["surfaceSite"].valeur, "1\u202f205 m²")
        self.assertEqual(lignes["surfaceSite"].source, "Cadastre")
        self.assertTrue(lignes["ilotChaleurUrbain"].informatif)
        resultat = sortie[0].resultat["resultats"][0]  # type: ignore[index]
        detail = construire_detail_usage(resultat, enrichissement, complementaires)  # type: ignore[arg-type]
        impacts = {l.impact.libelle for _, ls in detail for l in ls}
        self.assertTrue(impacts <= {"Très positif", "Positif", "Neutre", "Négatif", "Très négatif", "Bloquant"})
        self.assertTrue(resultat["tags"])  # type: ignore[index]

    def test_valeurs_etape(self) -> None:
        e = {"distanceTransportCommun": None, "risqueInondation": "oui", "zonageAbcLogement": "abis"}
        self.assertEqual(valeur_etape("distanceTransportCommun", e, {}), "Aucun arrêt à moins de 2 km")
        self.assertEqual(valeur_etape("distanceAutoroute", e, {}), "")
        self.assertEqual(valeur_etape("risquesNaturels", e, {}), ["Inondations"])
        self.assertEqual(valeur_etape("zonageAbcLogement", e, {}), "A BIS")


if __name__ == "__main__":
    unittest.main()
