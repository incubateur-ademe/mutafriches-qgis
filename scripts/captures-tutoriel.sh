#!/usr/bin/env bash
# Captures du tutoriel web de l'extension, jouées dans QGIS contre une API réelle (staging par
# défaut), en WebP 1600 px. Sortie par défaut : la page tutoriel du dépôt voisin Mutafriches.
# Attention : chaque passage analyse 28 sites sur l'API visée (quota BDNB, table attributaire).
# Deux captures du bandeau de staging, hors tutoriel, vont dans captures/ (local, ignoré).
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
STAGING="https://mutafriches.incubateur.ademe.dev"
API="${MF_TUTORIEL_API:-$STAGING}"
# Le staging se choisit comme environnement, pour montrer son bandeau ; toute autre API par son adresse
if [ "$API" = "$STAGING" ]; then SERVICE='mutafriches\api\environnement=staging'; else SERVICE="mutafriches\\api\\url=$API"; fi
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

[plugins]
mutafriches\\dev=true
$SERVICE

[qgis]
checkVersion=false
showTips=false
dockAttributeTable=true
INI

if ! defaults read org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1; then
  defaults write org.qgis.qgis3 NSRequiresAquaSystemAppearance -bool true
  trap 'defaults delete org.qgis.qgis3 NSRequiresAquaSystemAppearance >/dev/null 2>&1 || true' EXIT
fi

MF_TUTORIEL_HORS_PAGE="$RACINE/captures" MF_TUTORIEL_SORTIE="$SORTIE" MF_TUTORIEL_RAPPORT="$TRAVAIL/rapport.json" MF_TUTORIEL_ETAPES="${MF_TUTORIEL_ETAPES:-}" \
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
