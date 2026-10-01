"""Couleurs et feuille de style du panneau, inspirées du DSFR (sans conformité validée)."""

from qgis.PyQt.QtGui import QFontDatabase

BLEU_FRANCE = "#000091"
BLEU_SURVOL = "#1212ff"
BLEU_CLAIR = "#e3e3fd"
BLEU_INFO_FOND = "#e8edff"
TEXTE = "#161616"
TEXTE_SECONDAIRE = "#666666"
BORDURE = "#dddddd"
FOND_GRIS = "#f6f6f6"
SUCCES = "#18753c"
SUCCES_FOND = "#b8fec9"
AVERTISSEMENT = "#b34000"
AVERTISSEMENT_FOND = "#ffe9e6"
ERREUR = "#ce0500"
ERREUR_FOND = "#ffe9e9"
DEMO_FOND = "#fef7da"
DEMO_TEXTE = "#716043"

# Couleurs des badges, d'après les variantes DSFR utilisées par l'application web
BADGES = {
    "enrichi": ("#00744c", "#c3fad5"),
    "non-accessible": ("#716043", "#feecc2"),
    "alerte": ("#ce0500", "#ffe9e9"),
    "tag": ("#000091", "#e3e3fd"),
    "automatique": ("#18753c", "#b8fec9"),
    "manuelle": ("#716043", "#feecc2"),
    "source": ("#3a3a3a", "#eeeeee"),
    "tres-positif": ("#00744c", "#c3fad5"),
    "positif": ("#18753c", "#b8fec9"),
    "neutre": ("#716043", "#feecc2"),
    "negatif": ("#ce0500", "#ffe9e9"),
    "tres-negatif": ("#ce0500", "#ffe9e9"),
    "bloquant": ("#755348", "#fee9e5"),
}
FOND_BLEU_ALT = "#f5f5fe"
AVANTAGES = "#B8FEC9"
CONTRAINTES = "#FFBDBE"

NIVEAUX = {
    "info": (BLEU_FRANCE, BLEU_INFO_FOND),
    "succes": (SUCCES, "#e7f6ec"),
    "avertissement": (AVERTISSEMENT, AVERTISSEMENT_FOND),
    "erreur": (ERREUR, ERREUR_FOND),
}


def famille_police() -> str:
    # Marianne n'est utilisée que si elle est installée sur le poste
    familles = set(QFontDatabase().families())
    return "Marianne" if "Marianne" in familles else ""


def feuille_de_style() -> str:
    police = famille_police()
    declaration_police = f'font-family: "{police}";' if police else ""
    return f"""
#mfRacine {{ background: #ffffff; {declaration_police} font-size: 13px; color: {TEXTE}; }}
#mfRacine QLabel {{ color: {TEXTE}; }}
#mfRacine QScrollArea, #mfPages, #mfPages > QWidget {{ background: #ffffff; border: none; }}

QLabel#mfDemo {{
  background: {DEMO_FOND}; color: {DEMO_TEXTE}; font-weight: bold; font-size: 12px;
  padding: 6px 12px; border-bottom: 1px solid #e9d99f;
}}
QLabel#mfTitre {{ color: {BLEU_FRANCE}; font-size: 22px; font-weight: bold; }}
QLabel#mfSousTitre {{ color: {BLEU_FRANCE}; font-size: 14px; }}
QLabel#mfH2 {{ font-size: 17px; font-weight: bold; color: {TEXTE}; }}
QLabel#mfH3 {{ font-size: 14px; font-weight: bold; color: {TEXTE}; }}
QLabel#mfSurTitre {{ font-size: 11px; font-weight: bold; color: {TEXTE_SECONDAIRE}; }}
QLabel#mfNomSite {{ font-size: 18px; font-weight: bold; color: {BLEU_FRANCE}; }}
QLabel#mfAide {{ color: {TEXTE_SECONDAIRE}; font-size: 12px; }}
QLabel#mfValeur {{ font-weight: bold; }}
QLabel#mfIndisponible {{ color: {AVERTISSEMENT}; font-weight: bold; }}

QFrame#mfSeparateur {{ background: {BORDURE}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#mfPied {{ background: #ffffff; border-top: 1px solid {BORDURE}; }}

QPushButton#mfPrimaire, QPushButton#mfSecondaire {{
  border-radius: 0; padding: 8px 14px; font-weight: bold; min-height: 20px;
}}
QPushButton#mfPrimaire {{ background: {BLEU_FRANCE}; color: #ffffff; border: 1px solid {BLEU_FRANCE}; }}
QPushButton#mfPrimaire:hover {{ background: {BLEU_SURVOL}; border-color: {BLEU_SURVOL}; }}
QPushButton#mfPrimaire:disabled {{ background: #e5e5e5; color: #929292; border-color: #e5e5e5; }}
QPushButton#mfSecondaire {{ background: #ffffff; color: {BLEU_FRANCE}; border: 1px solid {BLEU_FRANCE}; }}
QPushButton#mfSecondaire:hover {{ background: {BLEU_CLAIR}; }}
QPushButton#mfSecondaire:disabled {{ color: #929292; border-color: #e5e5e5; }}
QPushButton#mfSecondaire:checked {{ background: {BLEU_CLAIR}; }}
QPushButton#mfLien {{
  background: transparent; border: none; color: {BLEU_FRANCE}; text-decoration: underline;
  text-align: left; padding: 2px 0;
}}
QPushButton#mfLien:hover {{ color: {BLEU_SURVOL}; }}
QPushButton#mfRetirer {{
  background: transparent; border: none; color: {TEXTE_SECONDAIRE}; font-size: 15px; padding: 0 6px;
}}
QPushButton#mfRetirer:hover {{ color: {ERREUR}; }}
QPushButton#mfPrimaire:focus, QPushButton#mfSecondaire:focus, QPushButton#mfLien:focus {{ outline: 2px solid #0a76f6; }}


QComboBox, QLineEdit {{
  background: #eeeeee; border: none; border-bottom: 2px solid #3a3a3a; border-radius: 0;
  padding: 6px 8px; min-height: 18px; color: {TEXTE};
}}
QComboBox:focus, QLineEdit:focus {{ border-bottom-color: {BLEU_FRANCE}; }}

QToolButton#mfAide {{
  border: 1px solid {BLEU_FRANCE}; border-radius: 9px; color: {BLEU_FRANCE};
  font-weight: bold; font-size: 11px; min-width: 16px; max-width: 16px; min-height: 16px; max-height: 16px;
  padding: 0; background: #ffffff;
}}
QToolButton#mfAide:hover {{ background: {BLEU_CLAIR}; }}
QLabel#mfErreurChamp {{ color: {ERREUR}; font-size: 12px; }}
QComboBox[erreur="true"] {{ border-bottom-color: {ERREUR}; }}
QFrame#mfCartePodium {{ background: #ffffff; border: 1px solid #e5e5e5; }}
QFrame#mfBandeauSite {{ background: {FOND_BLEU_ALT}; border-radius: 8px; }}
QFrame#mfLigneTableau {{ background: #ffffff; border: none; border-bottom: 1px solid {BORDURE}; }}
QFrame#mfLigneTableau:hover {{ background: {FOND_GRIS}; }}

QProgressBar#mfChargement {{ background: #eeeeee; border: none; max-height: 4px; min-height: 4px; }}
QProgressBar#mfChargement::chunk {{ background: {BLEU_FRANCE}; }}
"""
