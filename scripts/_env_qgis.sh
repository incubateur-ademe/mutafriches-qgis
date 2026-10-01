# Environnement pour lancer le Python embarqué de QGIS hors de l'application (macOS).
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
QGIS_RES="$QGIS_APP/Contents/Resources"
# Dossier nommé python3.11 alors que l'interpréteur est en 3.12 (build officiel 3.44)
QGIS_PYHOME="$(ls -d "$QGIS_RES"/python3.* | head -1)"
QGIS_PYTHON="$(ls "$QGIS_APP"/Contents/MacOS/python3.* | head -1)"
export PYTHONHOME="$QGIS_PYHOME"
export PYTHONPATH="$QGIS_PYHOME:$QGIS_PYHOME/site-packages:$QGIS_PYHOME/lib-dynload"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
