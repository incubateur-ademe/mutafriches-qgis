#!/usr/bin/env bash
# Régénère le terrain puis fige les réponses simulées avec l'algorithme Mutafriches local.
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
export MUTAFRICHES_DIR="${MUTAFRICHES_DIR:-$RACINE/../mutafriches}"

# Générateur exécuté avec le Python de QGIS (géométries) ; interroge le WFS de la Géoplateforme
(source "$RACINE/scripts/_env_qgis.sh" && "$QGIS_PYTHON" "$RACINE/outils/generer_terrain.py")
rm -f "$RACINE"/mutafriches/demo/scenarios/*.json
# tsx lancé depuis apps/api pour résoudre l'alias "@/" de son tsconfig
cd "$MUTAFRICHES_DIR/apps/api"
./node_modules/.bin/tsx --tsconfig ./tsconfig.json "$RACINE/outils/figer-reponses.ts"
