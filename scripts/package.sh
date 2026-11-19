#!/usr/bin/env bash
# Construit dist/mutafriches-<version>.zip, installable par « Installer depuis un ZIP », et les
# deux fichiers de test de bout en bout joints à chaque release (noms stables, sans version).
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^version=//p' "$RACINE/mutafriches/metadata.txt")"
SORTIE="$RACINE/dist/mutafriches-$VERSION.zip"
mkdir -p "$RACINE/dist"
# Un seul ZIP dans dist/ : les scripts E2E et de captures installent « le » ZIP présent
rm -f "$RACINE"/dist/mutafriches-*.zip
cd "$RACINE"
LISTE="$(find mutafriches -type f ! -name "*.pyc" ! -path "*/__pycache__/*" ! -name ".DS_Store" | LC_ALL=C sort)"
# Dates fixes : deux constructions du même état produisent le même ZIP
echo "$LISTE" | while read -r f; do TZ=UTC touch -t 202601010000 "$f"; done
echo "$LISTE" | zip -X -q "$SORTIE" -@
echo "$SORTIE ($(du -h "$SORTIE" | cut -f1))"
# Vrais sites de Montereau, pour les tests de l'équipe contre le staging : l'inventaire complet,
# et ses cinq premiers sites pour un passage rapide
INVENTAIRE="$RACINE/mutafriches/demo/montereau/friches-cnig-montereau.csv"
cp "$INVENTAIRE" "$RACINE/dist/friches-cnig-test-montereau.csv"
head -n 6 "$INVENTAIRE" > "$RACINE/dist/friches-cnig-test-montereau-5-sites.csv"
