#!/usr/bin/env bash
# Parcours du prototype dans une vraie session QGIS, sur un profil isolé (le profil de
# l'utilisateur n'est pas touché) : accueil, fichier CNIG refusé puis accepté, analyse,
# couches, tables et tableau de bord. Captures et rapports dans dist/e2e/.
# L'ancien parcours site à site (tests/e2e/parcours_qgis.py) n'est plus joué.
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
E2E="$RACINE/dist/e2e"
CAPTURES="$RACINE/captures"
PROFILS="$E2E/profils"
PROFIL="$PROFILS/profiles/default"

"$RACINE/scripts/package.sh" > /dev/null

# API factice locale : le parcours joue le mode réel sans dépendre de la production
PORT_API="${MF_E2E_PORT_API:-8799}"
python3 "$RACINE/tests/serveur_factice.py" "$PORT_API" &
PID_API=$!
rm -rf "$E2E" "$CAPTURES"
mkdir -p "$CAPTURES"
# Sous macOS, QSettings range les réglages sous le domaine de l'organisation (qgis.org)
mkdir -p "$PROFIL/python/plugins" "$PROFIL/qgis.org"
unzip -q "$RACINE"/dist/mutafriches-*.zip -d "$PROFIL/python/plugins"
cat > "$PROFIL/qgis.org/QGIS3.ini" <<INI
[PythonPlugins]
mutafriches=true

[locale]
overrideFlag=true
userLocale=fr_FR

[mutafriches]
api\\url=http://127.0.0.1:$PORT_API
api\\intervalle_ms=100

[qgis]
checkVersion=false
showTips=false
dockAttributeTable=true
INI

# Apparence claire pour QGIS seulement, le temps du parcours (captures en mode clair).
# Un réglage déjà posé par l'utilisateur est laissé tel quel.
if ! defaults read org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1; then
  defaults write org.qgis.qgis3 NSRequiresAquaSystemAppearance -bool true
  trap 'kill $PID_API 2>/dev/null || true; defaults delete org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1 || true' EXIT
else
  trap 'kill $PID_API 2>/dev/null || true' EXIT
fi

for PHASE in prototype; do
  echo "Phase $PHASE…"
  MF_E2E_SORTIE="$E2E" MF_E2E_CAPTURES="$CAPTURES" MF_E2E_PHASE="$PHASE" \
    "$QGIS_APP/Contents/MacOS/QGIS" --profiles-path "$PROFILS" --noversioncheck --nologo \
    --code "$RACINE/tests/e2e/prototype_qgis.py" > "$E2E/qgis-$PHASE.log" 2>&1 || true
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
for phase in ("prototype",):
    rapport = json.loads((dossier / f"rapport-{phase}.json").read_text(encoding="utf-8"))
    for c in rapport["controles"]:
        print(f"[{'OK' if c['ok'] else 'ÉCHEC'}] {phase} : {c['nom']}" + ("" if c["ok"] else f" ({c['detail']})"))
        echecs += not c["ok"]
    for e in rapport["erreurs"]:
        print(f"[ERREUR] {phase} : {e['etape']}\n{e['trace']}")
        echecs += 1
print("Captures : " + str(dossier.parent.parent / "captures"))
sys.exit(1 if echecs else 0)
PY
