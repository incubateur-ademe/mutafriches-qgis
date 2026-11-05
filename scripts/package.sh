#!/usr/bin/env bash
# Construit dist/mutafriches-<version>.zip, installable par « Installer depuis un ZIP ».
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^version=//p' "$RACINE/mutafriches/metadata.txt")"
SORTIE="$RACINE/dist/mutafriches-$VERSION.zip"
mkdir -p "$RACINE/dist"
rm -f "$SORTIE"
cd "$RACINE"
LISTE="$(find mutafriches -type f ! -name "*.pyc" ! -path "*/__pycache__/*" ! -name ".DS_Store" | LC_ALL=C sort)"
# Dates fixes : deux constructions du même état produisent le même ZIP
echo "$LISTE" | while read -r f; do TZ=UTC touch -t 202601010000 "$f"; done
echo "$LISTE" | zip -X -q "$SORTIE" -@
echo "$SORTIE ($(du -h "$SORTIE" | cut -f1))"
