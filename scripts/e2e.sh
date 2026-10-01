#!/usr/bin/env bash
# Parcours complet dans une vraie session QGIS, sur un profil isolé (le profil de
# l'utilisateur n'est pas touché). Deux lancements : parcelles d'exemple, puis couche de
# l'utilisateur dans un autre SCR. Captures et rapports dans dist/e2e/.
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
E2E="$RACINE/dist/e2e"
PROFILS="$E2E/profils"
PROFIL="$PROFILS/profiles/default"

"$RACINE/scripts/package.sh" > /dev/null
rm -rf "$E2E"
# Sous macOS, QSettings range les réglages sous le domaine de l'organisation (qgis.org)
mkdir -p "$PROFIL/python/plugins" "$PROFIL/qgis.org"
unzip -q "$RACINE"/dist/mutafriches-*.zip -d "$PROFIL/python/plugins"
cat > "$PROFIL/qgis.org/QGIS3.ini" <<INI
[PythonPlugins]
mutafriches=true

[locale]
overrideFlag=true
userLocale=fr_FR

[qgis]
checkVersion=false
showTips=false
INI

for PHASE in parcours couche-utilisateur; do
  echo "Phase $PHASE…"
  MF_E2E_SORTIE="$E2E" MF_E2E_PHASE="$PHASE" \
    "$QGIS_APP/Contents/MacOS/QGIS" --profiles-path "$PROFILS" --noversioncheck --nologo \
    --code "$RACINE/tests/e2e/parcours_qgis.py" > "$E2E/qgis-$PHASE.log" 2>&1 || true
  if [ ! -f "$E2E/rapport-$PHASE.json" ]; then
    echo "Pas de rapport pour la phase $PHASE (voir $E2E/qgis-$PHASE.log)"
    exit 1
  fi
done

python3 - "$E2E" <<'PY'
import json, sys
from pathlib import Path
dossier = Path(sys.argv[1])
echecs = 0
for phase in ("parcours", "couche-utilisateur"):
    rapport = json.loads((dossier / f"rapport-{phase}.json").read_text(encoding="utf-8"))
    for c in rapport["controles"]:
        print(f"[{'OK' if c['ok'] else 'ÉCHEC'}] {phase} : {c['nom']}" + ("" if c["ok"] else f" ({c['detail']})"))
        echecs += not c["ok"]
    for e in rapport["erreurs"]:
        print(f"[ERREUR] {phase} : {e['etape']}\n{e['trace']}")
        echecs += 1
print(f"Captures : {dossier}")
sys.exit(1 if echecs else 0)
PY
