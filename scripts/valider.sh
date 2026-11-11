#!/usr/bin/env bash
# Validation complète avant tout commit : format, lint, types, tests, paquet.
# Ruff et mypy tournent dans l'environnement uv du dépôt, jamais dans le Python de QGIS.
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"
MODE="${1:-}"

if [ "$MODE" = "--check" ]; then
  uv run ruff format --check .
  uv run ruff check .
else
  uv run ruff format .
  uv run ruff check --fix .
fi
uv run mypy
"$RACINE/scripts/tests.sh"
"$RACINE/scripts/package.sh"
uv run python scripts/verifier-paquet.py
