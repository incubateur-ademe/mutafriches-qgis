#!/usr/bin/env bash
# Tests unitaires avec le Python de QGIS (hors interface graphique).
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
source "$RACINE/scripts/_env_qgis.sh"
cd "$RACINE"
"$QGIS_PYTHON" -m unittest discover -s tests -p "test_*.py" "$@"
