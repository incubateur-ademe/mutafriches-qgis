"""Contrôle du ZIP de l'extension : métadonnées valides, rien d'étranger au plugin dans l'archive."""

import configparser
import re
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CHAMPS_REQUIS = ("name", "qgisMinimumVersion", "description", "version", "author", "email")
INTERDITS = ("__pycache__", ".pyc", ".DS_Store", "tests/", ".venv", ".mypy_cache", ".ruff_cache")


def main() -> int:
    archives = sorted((RACINE / "dist").glob("mutafriches-*.zip"))
    if not archives:
        print("Aucun ZIP dans dist/ : lancer scripts/package.sh")
        return 1
    archive = archives[-1]
    erreurs: list[str] = []
    with zipfile.ZipFile(archive) as contenu:
        noms = contenu.namelist()
        etrangers = [n for n in noms if not n.startswith("mutafriches/")]
        if etrangers:
            erreurs.append(f"fichiers hors du dossier du plugin : {etrangers[:3]}")
        erreurs += [f"fichier à exclure : {n}" for n in noms if any(i in n for i in INTERDITS)]
        for requis in ("mutafriches/__init__.py", "mutafriches/metadata.txt", "mutafriches/plugin.py"):
            if requis not in noms:
                erreurs.append(f"fichier manquant : {requis}")
        if "mutafriches/metadata.txt" in noms:
            metadonnees = configparser.ConfigParser()
            metadonnees.read_string(contenu.read("mutafriches/metadata.txt").decode("utf-8"))
            general = metadonnees["general"] if metadonnees.has_section("general") else {}
            erreurs += [f"metadata.txt : champ « {c} » absent" for c in CHAMPS_REQUIS if not general.get(c)]
            version = general.get("version", "")
            if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                erreurs.append(f"metadata.txt : version « {version} » hors SemVer")
            elif version not in archive.name:
                erreurs.append(f"le nom du ZIP ne porte pas la version {version}")
    for erreur in erreurs:
        print(f"[ZIP] {erreur}")
    print(f"{archive.name} : {len(noms)} fichiers, {'OK' if not erreurs else str(len(erreurs)) + ' erreur(s)'}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
