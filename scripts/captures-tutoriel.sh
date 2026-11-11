#!/usr/bin/env bash
# Captures du tutoriel web de l'extension, jouées dans QGIS contre une API réelle (staging par
# défaut), en WebP 1600 px. Sortie par défaut : la page tutoriel du dépôt voisin Mutafriches.
# Attention : chaque passage analyse 32 sites sur l'API visée (quota BDNB, table attributaire).
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
API="${MF_TUTORIEL_API:-https://mutafriches.incubateur.ademe.dev}"
SORTIE="${MF_TUTORIEL_SORTIE:-$RACINE/../mutafriches/apps/ui/public/images/tutoriel-qgis}"
TRAVAIL="$RACINE/dist/tutoriel"
PROFILS="$TRAVAIL/profils"
PROFIL="$PROFILS/profiles/default"

"$RACINE/scripts/package.sh" > /dev/null
rm -rf "$TRAVAIL"
mkdir -p "$PROFIL/python/plugins" "$PROFIL/qgis.org" "$SORTIE"
unzip -q "$RACINE"/dist/mutafriches-*.zip -d "$PROFIL/python/plugins"
cat > "$PROFIL/qgis.org/QGIS3.ini" <<INI
[PythonPlugins]
mutafriches=true

[locale]
overrideFlag=true
userLocale=fr_FR

[mutafriches]
api\\url=$API

[qgis]
checkVersion=false
showTips=false
dockAttributeTable=true
INI

if ! defaults read org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1; then
  defaults write org.qgis.qgis3 NSRequiresAquaSystemAppearance -bool true
  trap 'defaults delete org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1 || true' EXIT
fi

MF_TUTORIEL_SORTIE="$SORTIE" MF_TUTORIEL_RAPPORT="$TRAVAIL/rapport.json" MF_TUTORIEL_ETAPES="${MF_TUTORIEL_ETAPES:-}" \
  "$QGIS_APP/Contents/MacOS/QGIS" --profiles-path "$PROFILS" --noversioncheck --nologo \
  --code "$RACINE/tests/e2e/tutoriel_qgis.py" > "$TRAVAIL/qgis.log" 2>&1 || true

python3 - "$TRAVAIL/rapport.json" "$SORTIE" <<'PY'
import json, sys
from pathlib import Path
rapport = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for note in rapport["notes"]:
    print("Note :", note)
for erreur in rapport["erreurs"]:
    print(f"[ERREUR] {erreur['etape']}\n{erreur['trace']}")
print(f"{len(rapport['captures'])} captures dans {sys.argv[2]}")
sys.exit(1 if rapport["erreurs"] else 0)
PY
