# ADR-0001 : Interface Qt native plutôt que HTML dans QWebEngineView

- Statut : accepté
- Date : 2026-09-30

## Contexte

Le panneau doit être soigné et inspiré du DSFR : bleu France, boutons rectangulaires,
formulaires accessibles, états explicites. Deux pistes :

- **A. Qt natif (PyQGIS)** : widgets Qt et feuille de style QSS.
- **B. HTML/CSS/JS (voire React) dans `QWebEngineView`** : réutilisation des compétences et
  composants web, pont JS ↔ Python par `QWebChannel`.

Installation réellement inspectée : QGIS 3.44.14 officiel, macOS 26.6 arm64, Qt 5.15.19,
PyQt 5.15.10, Python 3.12.11.

## Constat

- `PyQt5.QtWebEngineWidgets` est **absent** : aucune bibliothèque QtWebEngine dans le bundle,
  et `qgis.PyQt.QtWebEngineWidgets` échoue à l'import (`ModuleNotFoundError`). Le test de bout
  en bout prévu (page locale → Python → carte → page) n'a donc pas pu être réalisé.
- Seul **QtWebKit 5.212** est présent (avec `QtWebChannel`). Moteur non maintenu, CSS/JS
  datés, et retiré de Qt6 : il n'existera pas sous QGIS 4.
- Des distributions Windows/OSGeo4W présentent aussi des manques de WebEngine selon les
  versions ; on ne peut pas le supposer disponible chez les utilisateurs.
- L'obtenir imposerait d'installer des paquets dans le Python embarqué de QGIS : fragile et
  invasif, exclu.

## Décision

Interface **Qt native** : widgets Qt, styles centralisés dans `ui/style.py`, composants
réutilisables dans `ui/widgets.py`. Imports via `qgis.PyQt` et énumérations qualifiées, pour
préparer un portage Qt6 (non testé à ce jour).

## Conséquences

- Pas de réutilisation directe des composants React ni du DSFR web. L'inspiration DSFR est
  reproduite à la main (couleurs, hiérarchie, boutons) ; **aucune conformité n'est revendiquée**.
- Police Marianne utilisée seulement si elle est installée sur le poste.
- Fonctionne partout où QGIS fonctionne, sans dépendance supplémentaire.
- Si un contenu riche devient nécessaire (fiches explicatives longues), `QTextBrowser` avec du
  HTML limité reste possible sans WebEngine.
- À réévaluer si QGIS 4 embarque QtWebEngine de façon fiable sur toutes les plateformes cibles.
