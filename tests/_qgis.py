"""Initialise une application QGIS sans interface, partagée par les tests."""

import sys
from pathlib import Path

from qgis.core import QgsApplication

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

_APP = QgsApplication.instance()
if _APP is None:
    _APP = QgsApplication([], False)
    _APP.initQgis()
