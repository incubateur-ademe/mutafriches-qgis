"""Serveur HTTP factice de l'API Mutafriches, pour les tests et le parcours E2E.

Rejoue la table attributaire figée de Montereau sous la forme des vraies réponses de
POST /enrichissement et POST /evaluation/calculer. Contrôle l'en-tête Origin comme l'API.

Usage : python3 tests/serveur_factice.py [port]
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
TABLE = RACINE / "mutafriches" / "demo" / "montereau" / "attributaire-77305.geojson"
ORIGINE_AUTORISEE = "https://qgis.mutafriches.beta.gouv.fr"
USAGES = ("residentiel", "equipements", "culture", "tertiaire", "industrie", "renaturation", "photovoltaique")
# Parcelle dont l'enrichissement échoue, pour tester un échec site par site
PARCELLE_EN_ECHEC = "77305000ZZ9999"
# Parcelle absente du cadastre : l'API réelle répond 500 « Erreur lors de l'enrichissement »
PARCELLE_INCONNUE = "77305000ZZ5000"
# Parcelle dont la réponse dépasse le délai du client (toujours, ou seulement au premier appel)
PARCELLE_TROP_LENTE = "77305000ZZ8888"
PARCELLE_LENTE_UNE_FOIS = "77305000ZZ7777"
ATTENTE_LENTE_S = 3.0
_deja_lentes: set[str] = set()


def _sites() -> dict[str, dict]:
    collection = json.loads(TABLE.read_text(encoding="utf-8"))
    return {",".join(sorted(e["properties"]["parcelles"].split("|"))): e for e in collection["features"]}


SITES = _sites()


def enrichissement(identifiants: list[str]) -> tuple[int, dict]:
    if PARCELLE_TROP_LENTE in identifiants or (
        PARCELLE_LENTE_UNE_FOIS in identifiants and PARCELLE_LENTE_UNE_FOIS not in _deja_lentes
    ):
        _deja_lentes.update(identifiants)
        time.sleep(ATTENTE_LENTE_S)
        return 400, {"statusCode": 400, "message": "Réponse tardive"}
    if PARCELLE_LENTE_UNE_FOIS in identifiants:
        identifiants = sorted(next(iter(SITES)).split(","))
    if PARCELLE_INCONNUE in identifiants:
        return 500, {"statusCode": 500, "message": "Erreur lors de l'enrichissement"}
    if PARCELLE_EN_ECHEC in identifiants:
        return 400, {"statusCode": 400, "message": "Parcelle introuvable au cadastre"}
    entite = SITES.get(",".join(sorted(identifiants)))
    if entite is None:
        return 400, {"statusCode": 400, "message": "Site inconnu du serveur factice"}
    p = entite["properties"]
    reponse = {k: v for k, v in p.items() if k[0].islower() and "_" not in k and v is not None}
    reponse.update(
        {
            "identifiantParcelle": p["parcelle_predominante"] or identifiants[0],
            "identifiantsParcelles": sorted(identifiants),
            "nombreParcelles": len(identifiants),
            "codeInsee": p["code_insee"],
            "commune": p["commune"],
            "geometrieSite": entite["geometry"],
            "sourcesUtilisees": ["Cadastre"],
            "champsManquants": [],
            "sourcesEchouees": [],
        }
    )
    return 200, reponse


def mutabilite(donnees: dict) -> tuple[int, dict]:
    complementaires = donnees.get("donneesComplementaires") or {}
    if len([v for v in complementaires.values() if v]) < 9:
        return 400, {"statusCode": 400, "message": "DONNEES_COMPLEMENTAIRES_INCOMPLETES"}
    identifiants = (donnees.get("donneesEnrichies") or {}).get("identifiantsParcelles") or []
    entite = SITES.get(",".join(sorted(identifiants)))
    if entite is None:
        return 400, {"statusCode": 400, "message": "Site inconnu du serveur factice"}
    p = entite["properties"]
    exclus = [u for u in str(p.get("usages_exclus") or "").split("|") if u]
    classes = sorted(USAGES, key=lambda u: (u in exclus, -(p.get(f"indice_{u}") or 0)))
    return 200, {
        "fiabilite": {
            "note": p["fiabilite"],
            "text": p["fiabilite_niveau"],
            "description": "",
            "criteresRenseignes": 0,
            "criteresTotal": 0,
            "poidsRenseignes": 0,
            "poidsTotal": 0,
        },
        "resultats": [
            {"rang": rang, "usage": usage, "indiceMutabilite": p.get(f"indice_{usage}") or 0, "exclu": usage in exclus}
            for rang, usage in enumerate(classes, start=1)
        ],
        "evaluationId": "factice",
    }


class Gestionnaire(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # silence
        return

    def _repondre(self, statut: int, corps: dict) -> None:
        contenu = json.dumps(corps).encode("utf-8")
        self.send_response(statut)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(contenu)))
        self.end_headers()
        self.wfile.write(contenu)

    def do_POST(self) -> None:
        donnees = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        if self.headers.get("Origin") != ORIGINE_AUTORISEE:
            self._repondre(403, {"statusCode": 403, "message": "Origin required"})
        elif self.path.startswith("/enrichissement"):
            self._repondre(*enrichissement(donnees.get("identifiants") or []))
        elif self.path.startswith("/evaluation/calculer"):
            self._repondre(*mutabilite(donnees))
        else:
            self._repondre(404, {"statusCode": 404, "message": "Not Found"})


def demarrer(port: int = 0) -> ThreadingHTTPServer:
    serveur = ThreadingHTTPServer(("127.0.0.1", port), Gestionnaire)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur


if __name__ == "__main__":
    serveur = ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8799), Gestionnaire)
    serveur.serve_forever()
