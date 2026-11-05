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

[qgis]
checkVersion=false
showTips=false
dockAttributeTable=true
INI

# Apparence claire pour QGIS seulement, le temps du parcours (captures en mode clair).
# Un réglage déjà posé par l'utilisateur est laissé tel quel.
if ! defaults read org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1; then
  defaults write org.qgis.qgis3 NSRequiresAquaSystemAppearance -bool true
  trap 'defaults delete org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1 || true' EXIT
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

# Tableaux de bord générés, copiés avec des chemins relatifs vers les ressources du dépôt
copier_tdb() {
  if [ -n "$1" ] && [ -f "$1" ]; then
    sed -e "s#file://.*/dashboard/vendor#../mutafriches/dashboard/vendor#g" \
        -e "s#file://.*/logo-mutafriches.png#../mutafriches/icons/logo-mutafriches.png#g" "$1" > "$CAPTURES/$2"
  fi
}
copier_tdb "$(python3 -c "import json;print(json.load(open('$E2E/rapport-prototype.json')).get('dashboard',''))")" "tableau-de-bord.html"
copier_tdb "$(python3 -c "import json;print(json.load(open('$E2E/rapport-prototype.json')).get('dashboard_alertes',''))")" "tableau-de-bord-avec-alertes.html"

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
