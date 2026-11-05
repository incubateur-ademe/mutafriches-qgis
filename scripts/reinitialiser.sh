#!/usr/bin/env bash
# Efface ce que le prototype mémorise dans le profil QGIS (accueil : structure, mail,
# consentement), pour revoir l'accueil à la prochaine ouverture du panneau. QGIS doit être fermé.
set -euo pipefail
PROFIL="${QGIS_PROFIL:-$HOME/Library/Application Support/QGIS/QGIS3/profiles/default}"
INI="$PROFIL/qgis.org/QGIS3.ini"

if pgrep -x QGIS >/dev/null 2>&1; then
  echo "Fermer QGIS d'abord : il réécrit ses réglages à la fermeture." >&2
  exit 1
fi
if [ ! -f "$INI" ]; then
  echo "Réglages introuvables : $INI" >&2
  exit 1
fi
# Section [mutafriches] : clés utilisateur\structure, utilisateur\mail, utilisateur\consentement
python3 - "$INI" <<'PY'
import re
import sys
from pathlib import Path

chemin = Path(sys.argv[1])
texte = chemin.read_text(encoding="utf-8")
nouveau, n = re.subn(r"(?ms)^\[mutafriches\]\n(?:[^\[\n][^\n]*\n|\n)*", "", texte)
chemin.write_text(nouveau, encoding="utf-8")
print("Accueil réinitialisé." if n else "Rien à effacer : l'accueil n'était pas mémorisé.")
PY
