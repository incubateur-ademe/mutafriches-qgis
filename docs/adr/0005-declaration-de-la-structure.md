# ADR-0005 : Déclaration de la structure au registre des intégrateurs

- Statut : accepté (amende l'ADR-0003 et l'ADR-0004), amendé le 2026-11-25 (consentement séparé)
- Date : 2026-11-20

## Contexte

Jusqu'à la version 0.3.x, toutes les installations envoyaient la même origine conventionnelle,
`https://qgis.mutafriches.beta.gouv.fr` (ADR-0003). Mutafriches ne distinguait aucune structure,
et les informations saisies à l'accueil (facultatives) restaient dans le profil QGIS.

Mutafriches tient désormais un registre des intégrateurs (ADR-0055 du dépôt Mutafriches) :
`POST /api/integrateurs/declarations`, route ouverte limitée à 5 appels par heure et par IP,
déclare un domaine pour un canal (`qgis` ici). Le domaine est actif tout de suite et sert
d'origine ; l'en-tête `X-Mutafriches-Client: qgis/<version>` distingue l'extension de l'API d'une
même structure. Prénom, nom et e-mail sont obligatoires et partent chez Brevo, jamais en base.

## Décision

- **Accueil = formulaire de déclaration**, aux libellés et à l'ordre du formulaire web :
  structure, type de structure, domaine, prénom, nom, e-mail, tous obligatoires. Contrôle
  local identique au web (`hoteDeDomaineDeclare` porté dans `core/declaration.py`, comparé à
  ses cas de test par `tests/test_miroirs.py`). La case de consentement disparaît, comme sur le
  web : une mention renvoie à la politique de confidentialité.
- **Déclaration à la validation de l'accueil** en mode réel, sinon à la première analyse.
  L'origine renvoyée est mémorisée par adresse d'API (staging et production ont chacun leur
  registre), avec une empreinte de la saisie : une saisie inchangée n'est jamais redéclarée,
  une saisie modifiée (options) l'est à l'analyse suivante.
- **Appels d'analyse** avec l'origine déclarée et `X-Mutafriches-Client: qgis/<version>`.
- **Repli** : une API sans registre (404, production avant déploiement) rend l'origine
  historique, toujours acceptée ; rien n'est mémorisé et la déclaration est retentée ensuite.
- **Refus** : un 403 pendant l'analyse oublie l'origine mémorisée (domaine révoqué, registre
  vidé), la suivante redéclare. Un domaine révoqué est expliqué, avec l'adresse de contact.
- Le réglage « Origine envoyée » du mode développeur est retiré : l'origine vient du registre.

## Amendement du 2026-11-25 : consentement séparé de l'e-mail

L'e-mail étant obligatoire, sa saisie ne peut pas valoir accord pour être sollicité. L'API
distingue désormais les deux (PR 285 de Mutafriches) : l'e-mail sert au suivi de l'accès et aux
échanges sur le fonctionnement du service ; un champ facultatif `accepteContact` (booléen strict)
pose l'attribut Brevo `ACCEPTE_CONTACT`, qu'une déclaration ultérieure ne remet jamais à faux.

- **Case** sous l'e-mail, à l'accueil et dans les options, libellé du formulaire web (comparé
  par `tests/test_miroirs.py`). Décochée par défaut, facultative, sans effet sur l'accès.
  Mémorisée dans `plugins/mutafriches/utilisateur/accepte_contact`. Le consentement des 0.3.x
  (libellé et finalité différents) n'est pas repris.
- **Envoi** : la clé `accepteContact: true` n'entre dans le corps que si la case est cochée.
  Toujours l'envoyer aurait changé l'empreinte de chaque déclaration existante et redéclaré tous
  les utilisateurs à leur analyse suivante (5 déclarations par heure et par IP).
- **Empreinte** : cocher la case change l'empreinte, donc renvoie la déclaration une fois. Une
  empreinte mémorisée avec accord reste valable case décochée : la décocher ne renvoie rien,
  puisque l'API ne retire pas un accord (le retrait passe par la désinscription des e-mails).
- **Publication** : tant que la PR 285 n'est pas en production, l'API accepte le champ mais
  l'ignore ; une version qui l'envoie ne doit pas être publiée avant.

## Conséquences

- Mutafriches sait qui utilise l'extension, par structure, sans donnée personnelle en base.
- Un utilisateur d'une version précédente sans informations complètes est renvoyé à l'accueil
  à sa première analyse réelle ; la démonstration ne demande rien d'autre que l'accueil.
- Le domaine n'est pas vérifié : rien n'empêche une fausse saisie (même limite que le web).
- `tests/serveur_factice.py` tient un registre factice (révocation, absence de registre) pour
  les tests unitaires et l'E2E.
