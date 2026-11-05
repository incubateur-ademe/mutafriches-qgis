"""Lecture et contrôle d'un fichier de sites au standard CNIG Friches (v2023-12 rev. 2025-12)."""

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Miroir de COLONNES_FRICHE_CNIG (packages/shared-types/src/cnig), TableSchema v1.0.6
COLONNES_CNIG: tuple[str, ...] = (
    "site_id", "site_nom", "site_type", "site_adresse", "site_identif_date", "site_actu_date",
    "site_url", "site_ademe_url", "site_securite", "site_occupation", "site_statut",
    "site_projet_url", "site_reconv_annee", "site_reconv_type", "activite_libelle",
    "activite_code", "activite_fin_annee", "comm_nom", "comm_insee", "bati_type", "bati_nombre",
    "bati_surface", "bati_pollution", "bati_vacance", "bati_patrimoine", "bati_etat",
    "local_ancien_annee", "local_recent_annee", "proprio_type", "proprio_personne", "proprio_nom",
    "sol_pollution_annee", "sol_pollution_existe", "sol_pollution_origine",
    "sol_pollution_commentaire", "sol_depollution_fiche", "unite_fonciere_surface",
    "unite_fonciere_refcad", "urba_zone_type", "urba_zone_lib", "urba_zone_formdomi", "urba_zaer",
    "urba_doc_type", "desserte_distance", "desserte_commentaire", "source_nom", "source_url",
    "source_producteur", "source_contact", "geompoint", "geomsurf",
)
# Colonnes dont le standard impose le remplissage (§3.3) et dont le prototype a besoin
COLONNES_OBLIGATOIRES: tuple[str, ...] = ("site_id", "site_nom", "comm_insee", "unite_fonciere_refcad", "geompoint")
EXTENSIONS = (".csv", ".geojson", ".json")
FORMAT_IDU = re.compile(r"^(?:\d{5}|2[AB]\d{3})[0-9A-Z]{3}[0-9A-Z]{2}\d{4}$")
FORMAT_INSEE = re.compile(r"^(?:\d{5}|2[AB]\d{3})$")
SEPARATEUR_VALEURS = "|"


@dataclass(frozen=True)
class Probleme:
    # Une ligne vide désigne le fichier entier
    ligne: int
    message: str
    bloquant: bool = True


@dataclass
class SiteCnig:
    site_id: str
    site_nom: str
    comm_insee: str
    parcelles: list[str]
    ligne: int
    # Erreurs de la ligne : une ligne en erreur est écartée, pas le fichier
    erreurs: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.erreurs


@dataclass
class LectureCnig:
    fichier: str
    # Toutes les lignes lues, correctes ou non, dans l'ordre du fichier
    sites: list[SiteCnig] = field(default_factory=list)
    # Problèmes du fichier entier (format, colonnes) ; les erreurs de ligne sont sur les sites
    problemes: list[Probleme] = field(default_factory=list)
    colonnes: list[str] = field(default_factory=list)

    @property
    def sites_ok(self) -> list[SiteCnig]:
        return [s for s in self.sites if s.ok]

    @property
    def sites_ko(self) -> list[SiteCnig]:
        return [s for s in self.sites if not s.ok]

    @property
    def valide(self) -> bool:
        return bool(self.sites_ok) and not any(p.bloquant for p in self.problemes)

    @property
    def bloquants(self) -> list[Probleme]:
        return [p for p in self.problemes if p.bloquant]


def _lignes_csv(chemin: Path) -> tuple[list[str], list[dict[str, str]]]:
    with chemin.open(encoding="utf-8-sig", newline="") as flux:
        extrait = flux.read(4096)
        flux.seek(0)
        try:
            dialecte = csv.Sniffer().sniff(extrait, delimiters=",;\t")
        except csv.Error:
            dialecte = csv.excel
        lecteur = csv.DictReader(flux, dialect=dialecte)
        lignes = [{(k or "").strip(): (v or "").strip() for k, v in ligne.items()} for ligne in lecteur]
        return [c.strip() for c in lecteur.fieldnames or []], lignes


def _lignes_geojson(chemin: Path) -> tuple[list[str], list[dict[str, str]]]:
    collection = json.loads(chemin.read_text(encoding="utf-8-sig"))
    entites = collection.get("features") if isinstance(collection, dict) else None
    if not isinstance(entites, list):
        raise ValueError("Le fichier n'est pas une FeatureCollection GeoJSON.")
    colonnes: list[str] = []
    lignes = []
    for entite in entites:
        proprietes = entite.get("properties") or {}
        for cle in proprietes:
            if cle not in colonnes:
                colonnes.append(cle)
        ligne = {k: ("" if v is None else str(v)) for k, v in proprietes.items()}
        # Une géométrie GeoJSON vaut le geompoint obligatoire du CSV
        if entite.get("geometry") and "geompoint" not in ligne:
            ligne["geompoint"] = "GEOJSON"
            if "geompoint" not in colonnes:
                colonnes.append("geompoint")
        lignes.append(ligne)
    return colonnes, lignes


def lire_cnig(chemin: Path) -> LectureCnig:
    lecture = LectureCnig(fichier=chemin.name)
    if not chemin.exists():
        lecture.problemes.append(Probleme(0, "Fichier introuvable."))
        return lecture
    if chemin.suffix.lower() not in EXTENSIONS:
        lecture.problemes.append(Probleme(0, "Format non pris en charge : CSV ou GeoJSON attendu (standard CNIG Friches)."))
        return lecture
    try:
        colonnes, lignes = _lignes_csv(chemin) if chemin.suffix.lower() == ".csv" else _lignes_geojson(chemin)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as erreur:
        lecture.problemes.append(Probleme(0, f"Fichier illisible : {erreur}"))
        return lecture
    lecture.colonnes = colonnes
    manquantes = [c for c in COLONNES_OBLIGATOIRES if c not in colonnes]
    if manquantes:
        lecture.problemes.append(Probleme(0, "Colonnes obligatoires absentes : " + ", ".join(manquantes) + "."))
        return lecture
    inconnues = [c for c in colonnes if c not in COLONNES_CNIG and not c.startswith("mf_")]
    if inconnues:
        lecture.problemes.append(Probleme(0, "Colonnes hors standard ignorées : " + ", ".join(inconnues[:6]) + ("…" if len(inconnues) > 6 else "") + ".", False))
    if not lignes:
        lecture.problemes.append(Probleme(0, "Le fichier ne contient aucun site."))
        return lecture

    identifiants: dict[str, int] = {}
    for numero, ligne in enumerate(lignes, start=2):
        site_id = ligne.get("site_id", "")
        nom = ligne.get("site_nom", "")
        insee = ligne.get("comm_insee", "")
        refcad = ligne.get("unite_fonciere_refcad", "")
        parcelles = [p.strip() for p in refcad.split(SEPARATEUR_VALEURS) if p.strip()]
        site = SiteCnig(site_id, nom, insee, parcelles, numero)
        if not site_id:
            site.erreurs.append("site_id vide")
        elif site_id in identifiants:
            site.erreurs.append(f"site_id déjà utilisé ligne {identifiants[site_id]}")
        else:
            identifiants[site_id] = numero
        if not nom:
            site.erreurs.append("site_nom vide")
        if not FORMAT_INSEE.match(insee):
            site.erreurs.append(f"comm_insee « {insee} » invalide (5 caractères attendus)")
        if not parcelles:
            site.erreurs.append("unite_fonciere_refcad vide")
        else:
            mal_formees = [p for p in parcelles if not FORMAT_IDU.match(p)]
            if mal_formees:
                site.erreurs.append(f"parcelle « {mal_formees[0]} » mal formée (14 caractères, ex. 77305000AB0160)")
        if not ligne.get("geompoint"):
            site.erreurs.append("geompoint vide")
        lecture.sites.append(site)
    return lecture
