"""Tableau de bord territorial : page HTML autonome (DSFR + dsfr-chart), ouverte dans le navigateur.

QGIS 3.44 macOS n'embarque pas QtWebEngine et son QtWebKit ne sait pas exécuter dsfr-chart
(ADR-0001) : la page est écrite sur disque et ouverte par le navigateur du poste.
"""

import html
import json
from pathlib import Path

from ..core.attributaire import (
    NIVEAUX_FIABILITE,
    ORDRE_USAGES,
    PROFILS_ECART,
    SiteAttributaire,
    Synthese,
    libelle_usage,
)
from ..core.referentiel import formater_note

VENDOR = Path(__file__).resolve().parent / "vendor"
LOGO = Path(__file__).resolve().parent.parent / "icons" / "logo-mutafriches.png"

COULEURS_FIABILITE: dict[str, str] = {
    "Très fiable": "#18753c",
    "Fiable": "#27a658",
    "Moyennement fiable": "#c3992a",
    "Peu fiable": "#e4794a",
    "Très peu fiable": "#ce0500",
}


def _js(valeur: object) -> str:
    return html.escape(json.dumps(valeur, ensure_ascii=False), quote=True)


def _h(texte: object) -> str:
    return html.escape(str(texte))


def _jauges(synthese: Synthese) -> str:
    total = max(1, synthese.nombre_sites)
    blocs = []
    for usage in ORDRE_USAGES:
        nombre = synthese.par_usage.get(usage, 0)
        part = round(100 * nombre / total)
        blocs.append(
            f"""<div class="fr-col-12 fr-col-md-6 fr-col-lg-4">
  <div class="fr-card fr-p-3w mf-jauge">
    <p class="fr-text--sm fr-mb-1v"><strong>{_h(libelle_usage(usage))}</strong></p>
    <p class="fr-h4 fr-mb-1w">{nombre} site{'s' if nombre > 1 else ''} <span class="fr-text--sm fr-text--regular">({part} %)</span></p>
    <gauge-chart value="{nombre}" init="0" target="{synthese.nombre_sites}" percent="{part}" legend="false" height="1rem"></gauge-chart>
    <p class="fr-text--xs fr-mb-0">Indice moyen sur la commune : {formater_note(synthese.indice_moyen_par_usage.get(usage, 0.0))} %</p>
  </div>
</div>"""
        )
    return "\n".join(blocs)


def _tableau_profils(synthese: Synthese) -> str:
    total = max(1, synthese.nombre_sites)
    lignes = []
    for seuil, libelle, lecture in PROFILS_ECART:
        nombre = synthese.par_profil.get(libelle, 0)
        borne = "30 points et plus" if seuil == float("inf") else f"moins de {int(seuil)} points"
        lignes.append(
            f"<tr><td>{_h(libelle)}</td><td>{_h(borne)}</td><td>{nombre}</td><td>{round(100 * nombre / total)} %</td><td>{_h(lecture)}</td></tr>"
        )
    return "\n".join(lignes)


def _tableau_sites(sites: list[SiteAttributaire]) -> str:
    lignes = []
    for site in sites:
        lignes.append(
            "<tr>"
            f"<td><strong>{_h(site.nom)}</strong><br><span class='fr-text--xs'>{_h(site.site_id or site.cle)}</span></td>"
            f"<td>{_h(libelle_usage(site.usage_prioritaire))}</td>"
            f"<td>{round(site.indice_max)} %</td>"
            f"<td>{formater_note(site.fiabilite)} / 10</td>"
            f"<td>{_h(site.profil)}</td>"
            f"<td>{len(site.parcelles)}</td>"
            "</tr>"
        )
    return "\n".join(lignes) or "<tr><td colspan='6'>Aucun site</td></tr>"


def generer_html(synthese: Synthese, sites: list[SiteAttributaire], avertissement: str) -> str:
    usages_x = [libelle_usage(u) for u in ORDRE_USAGES]
    usages_y = [synthese.par_usage.get(u, 0) for u in ORDRE_USAGES]
    fiabilite_x = [n for n in NIVEAUX_FIABILITE if synthese.par_fiabilite.get(n, 0)]
    fiabilite_y = [synthese.par_fiabilite[n] for n in fiabilite_x]
    compat_x = list(synthese.par_compatibilite.keys())
    compat_y = list(synthese.par_compatibilite.values())
    a_attention = len(synthese.sites_a_qualifier)
    dominant = max(synthese.par_usage.items(), key=lambda kv: kv[1])[0] if synthese.nombre_sites else None
    return f"""<!doctype html>
<html lang="fr" data-fr-scheme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mutafriches — Tableau de bord territorial — {_h(synthese.commune)}</title>
<link rel="stylesheet" href="{VENDOR.as_uri()}/dsfr.min.css">
<link rel="stylesheet" href="{VENDOR.as_uri()}/DSFRChart.css">
<style>
  body {{ background: #f6f6f6; }}
  .mf-entete {{ background: #fff; border-bottom: 1px solid #ddd; }}
  .mf-demo {{ background: #fef7da; color: #716043; font-weight: 700; padding: .5rem 1rem; }}
  .mf-chiffre {{ background: #fff; border: 1px solid #e5e5e5; padding: 1rem 1.25rem; height: 100%; }}
  .mf-chiffre .fr-h2 {{ color: #000091; margin-bottom: 0; }}
  .fr-card, .mf-bloc {{ background: #fff; border: 1px solid #e5e5e5; }}
  .mf-bloc {{ padding: 1.25rem; height: 100%; }}
  .mf-alerte {{ border-left: 4px solid #ce0500; background: #ffe9e9; padding: .75rem 1rem; }}
  .mf-pastille {{ display:inline-block; width:.8rem; height:.8rem; border-radius:50%; margin-right:.4rem; vertical-align:middle; }}
  table.fr-table--mf td, table.fr-table--mf th {{ padding: .5rem .75rem; }}
</style>
</head>
<body>
<div class="mf-demo">Mode démonstration — prototype : données figées de la table attributaire Mutafriches, saisie déclarative non vérifiée</div>
<header class="mf-entete fr-py-2w">
  <div class="fr-container">
    <div class="fr-grid-row fr-grid-row--middle">
      <div class="fr-col-auto fr-mr-3w"><img src="{LOGO.as_uri()}" alt="Mutafriches" height="48"></div>
      <div class="fr-col">
        <h1 class="fr-h3 fr-mb-0">Tableau de bord territorial — {_h(synthese.commune)} ({_h(synthese.code_insee)})</h1>
        <p class="fr-text--sm fr-mb-0">{synthese.nombre_sites} sites analysés · algorithme {_h(synthese.version_algorithme)} · table figée le {_h(synthese.date_table)}</p>
      </div>
    </div>
  </div>
</header>

<main class="fr-container fr-py-4w">
  <div class="fr-grid-row fr-grid-row--gutters">
    <div class="fr-col-6 fr-col-md-3"><div class="mf-chiffre"><p class="fr-text--sm fr-mb-1v">Sites analysés</p><p class="fr-h2">{synthese.nombre_sites}</p></div></div>
    <div class="fr-col-6 fr-col-md-3"><div class="mf-chiffre"><p class="fr-text--sm fr-mb-1v">Usage qui ressort le plus</p><p class="fr-h2">{_h(libelle_usage(dominant))}</p><p class="fr-text--xs fr-mb-0">{synthese.par_usage.get(dominant or '', 0)} sites</p></div></div>
    <div class="fr-col-6 fr-col-md-3"><div class="mf-chiffre"><p class="fr-text--sm fr-mb-1v">Fiabilité moyenne</p><p class="fr-h2">{formater_note(synthese.fiabilite_moyenne)} / 10</p><p class="fr-text--xs fr-mb-0">{synthese.par_fiabilite.get('Très fiable', 0)} sites très fiables</p></div></div>
    <div class="fr-col-6 fr-col-md-3"><div class="mf-chiffre"><p class="fr-text--sm fr-mb-1v">Sites à forte compatibilité</p><p class="fr-h2">{len(synthese.sites_forte_compatibilite)}</p><p class="fr-text--xs fr-mb-0">indice de l'usage prioritaire supérieur ou égal à 70 %</p></div></div>
  </div>

  <h2 class="fr-h4 fr-mt-5w fr-mb-2w">Usage le plus compatible, site par site</h2>
  <div class="fr-grid-row fr-grid-row--gutters">
    {_jauges(synthese)}
  </div>

  <div class="fr-grid-row fr-grid-row--gutters fr-mt-3w">
    <div class="fr-col-12 fr-col-lg-6">
      <div class="mf-bloc">
        <h2 class="fr-h5">Répartition des usages les plus compatibles</h2>
        <pie-chart x="{_js([usages_x])}" y="{_js([usages_y])}" name="{_js(usages_x)}" unit-tooltip=" sites" selected-palette="categorical"></pie-chart>
      </div>
    </div>
    <div class="fr-col-12 fr-col-lg-6">
      <div class="mf-bloc">
        <h2 class="fr-h5">Indice moyen par usage sur la commune</h2>
        <p class="fr-text--xs">Moyenne des indices de mutabilité des {synthese.nombre_sites} sites, par usage. Un indice n'est pas une probabilité de réussite.</p>
        <bar-chart x="{_js([usages_x])}" y="{_js([[synthese.indice_moyen_par_usage.get(u, 0.0) for u in ORDRE_USAGES]])}" name="{_js(['Indice moyen'])}" horizontal="true" unit-tooltip="%" selected-palette="default"></bar-chart>
      </div>
    </div>
  </div>

  <div class="fr-grid-row fr-grid-row--gutters fr-mt-3w">
    <div class="fr-col-12 fr-col-lg-5">
      <div class="mf-bloc">
        <h2 class="fr-h5">Qualité des résultats</h2>
        <pie-chart x="{_js([fiabilite_x])}" y="{_js([fiabilite_y])}" name="{_js(fiabilite_x)}" unit-tooltip=" sites" selected-palette="sequentialDescending"></pie-chart>
        <ul class="fr-text--sm fr-mt-2w">
          {''.join(f'<li><span class="mf-pastille" style="background:{COULEURS_FIABILITE.get(n, "#999")}"></span>{_h(n)} : {synthese.par_fiabilite.get(n, 0)} sites</li>' for n in NIVEAUX_FIABILITE if synthese.par_fiabilite.get(n, 0))}
        </ul>
        {f'<div class="mf-alerte fr-mt-2w"><strong>{a_attention} site{"s" if a_attention > 1 else ""} jamais qualifié{"s" if a_attention > 1 else ""}</strong> : mutabilité calculée avec « Ne sait pas » pour les 9 critères terrain. Compléter la qualification améliorerait la fiabilité.</div>' if a_attention else ''}
      </div>
    </div>
    <div class="fr-col-12 fr-col-lg-7">
      <div class="mf-bloc">
        <h2 class="fr-h5">Profils de sites</h2>
        <p class="fr-text--xs">Écart entre le meilleur et le moins bon usage d'un même site. Grille de lecture du prototype, à valider.</p>
        <div class="fr-table fr-table--sm fr-table--no-caption">
        <table class="fr-table--mf">
          <thead><tr><th>Profil</th><th>Écart (n°1 − n°7)</th><th>Sites</th><th>Part</th><th>Lecture</th></tr></thead>
          <tbody>{_tableau_profils(synthese)}</tbody>
        </table>
        </div>
        <h3 class="fr-h6 fr-mt-2w">Niveau de compatibilité de l'usage prioritaire</h3>
        <bar-chart x="{_js([compat_x])}" y="{_js([compat_y])}" name="{_js(['Sites'])}" unit-tooltip=" sites" selected-palette="sequentialDescending"></bar-chart>
      </div>
    </div>
  </div>

  <div class="mf-bloc fr-mt-3w">
    <h2 class="fr-h5">Sites à forte compatibilité ({len(synthese.sites_forte_compatibilite)})</h2>
    <p class="fr-text--xs">Indice de l'usage prioritaire supérieur ou égal à 70 % (palier « Excellent » de l'application web). Les sites sont repérables sur la carte QGIS par leur nom.</p>
    <div class="fr-table fr-table--sm fr-table--no-caption">
    <table class="fr-table--mf">
      <thead><tr><th>Site</th><th>Usage le plus compatible</th><th>Indice</th><th>Fiabilité</th><th>Profil</th><th>Parcelles</th></tr></thead>
      <tbody>{_tableau_sites(synthese.sites_forte_compatibilite)}</tbody>
    </table>
    </div>
  </div>

  <p class="fr-text--xs fr-mt-4w">{_h(avertissement)}</p>
</main>
<script src="{VENDOR.as_uri()}/DSFRChart.umd.cjs"></script>
</body>
</html>
"""


def ecrire_dashboard(dossier: Path, synthese: Synthese, sites: list[SiteAttributaire], avertissement: str) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"mutafriches-tableau-de-bord-{synthese.code_insee}.html"
    chemin.write_text(generer_html(synthese, sites, avertissement), encoding="utf-8")
    return chemin
