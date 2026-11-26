# ADR-0006 : Production seule, déclarant verrouillé, accord de contact exigé

- Statut : accepté (amende l'ADR-0003, l'ADR-0004 et l'ADR-0005)
- Date : 2026-11-26

## Contexte

Jusqu'à la version 0.4.x, la page d'options proposait trois environnements (production, staging,
démonstration sur une table figée) et un mode développeur (adresse d'API libre, délai entre deux
sites). Ces choix servaient à l'équipe, mais ils étaient visibles de tous les utilisateurs et le
tutoriel web devait les expliquer. Les coordonnées déclarées à l'accueil (ADR-0005) restaient
modifiables et effaçables à tout moment, alors que le domaine déclaré identifie la structure dans
les statistiques de Mutafriches.

L'écran de contrôle du fichier résumait les lignes en un seul encadré (« 4 sites OK, 6 sites KO »),
de couleur d'avertissement, qui mêlait ce qui part à l'analyse et ce qui doit être corrigé.

## Décision

- **Une seule API : la production.** Plus d'environnement, plus de démonstration, plus de mode
  développeur, ni dans l'interface ni dans les réglages. Les clés correspondantes sont effacées
  au démarrage (`migrer_anciens_reglages`).
- **Tests et captures par variable d'environnement.** `MUTAFRICHES_API_URL`, lue au lancement de
  QGIS, désigne une autre API ; `MUTAFRICHES_INTERVALLE_MS` raccourcit le délai entre deux sites,
  et n'est lue que face à une API de test. Le panneau affiche alors un bandeau « Environnement
  de test », que le script de captures du tutoriel masque. Ce n'est pas un réglage : rien ne
  l'enregistre, et un utilisateur ne la rencontre pas.
- **Coordonnées verrouillées après la déclaration.** Structure, type, domaine, prénom, nom et
  e-mail se saisissent à l'accueil, qui prévient qu'ils ne seront plus modifiables. Une fois la
  structure déclarée à l'API, le lien « Modifier » disparaît et la page d'options les affiche en
  lecture seule. Le bouton « Effacer mes informations » est retiré.
- **Une exception au verrou.** Un refus d'accès de l'API (403) oublie la déclaration : le lien
  « Modifier » revient, pour corriger un domaine refusé.
- **Accord de contact exigé.** La case « J'accepte d'être contacté·e… », facultative depuis
  l'amendement de l'ADR-0005, devient obligatoire pour utiliser l'extension : l'accueil ne se
  valide pas sans elle, et `accepteContact: true` part avec chaque déclaration. Elle reste
  décochée par défaut. La page d'options affiche l'accord sans permettre de le retirer : le
  retrait passe par la désinscription des e-mails, comme pour le site. Une structure déclarée
  par une version antérieure sans accord est renvoyée à l'accueil à son analyse suivante, avec
  ses coordonnées verrouillées et la seule case à cocher.
- **Deux encadrés au contrôle du fichier**, chacun affiché seulement s'il a des sites : les sites
  KO (erreur, avec la marche à suivre), puis les sites OK (succès).
- **Jeux d'essai hors du ZIP.** La table attributaire figée de Montereau et les deux inventaires
  CNIG ne servent plus qu'aux tests, au serveur factice et aux captures : ils vont dans
  `tests/donnees/`. Seul le modèle de fichier vide reste dans l'extension (`mutafriches/modeles/`).

## Options écartées

- **Garder le staging dans les options** : c'est ce qui obligeait le tutoriel à parler
  d'environnements, et un utilisateur resté sur le staging analysait ses sites pour rien.
- **Remise à zéro par désinstallation de l'extension** : QGIS décharge l'extension et supprime
  son dossier, sans toucher aux réglages du profil (`pyplugin_installer`, QGIS 3.44). Les
  coordonnées survivent donc à une réinstallation. Les ranger dans le dossier du plugin ne
  convient pas non plus : une mise à jour par ZIP remplace ce dossier et redemanderait la
  déclaration à chaque version.
- **Garder l'accord facultatif**, comme sur les formulaires du site : écarté par décision de
  l'équipe (2026-11-26).

## Conséquences

- Le tutoriel web n'a plus à décrire ni service ni mode ; sa page de réglages se réduit aux
  informations déclarées et au fond de carte.
- Une erreur de saisie à l'accueil ne se corrige plus dans l'extension une fois la structure
  déclarée : il faut écrire à contact@mutafriches.beta.gouv.fr. `scripts/reinitialiser.sh` reste
  l'outil de l'équipe (QGIS fermé).
- L'équipe lance QGIS avec `MUTAFRICHES_API_URL` pour viser le staging ou le serveur factice. Les
  captures du tutoriel ne doivent jamais viser la production (table attributaire publique,
  statistiques, quota BDNB).
- L'accord exigé diverge des formulaires du site, où la case reste facultative. Un accord posé
  comme condition d'accès n'est pas un consentement libre au sens du RGPD : la base légale des
  sollicitations adressées aux utilisateurs de l'extension, le libellé de la case et la politique
  de confidentialité du site sont à faire valider par le délégué à la protection des données de
  l'ADEME. L'attribut Brevo `ACCEPTE_CONTACT` vaut désormais « vrai » pour tout utilisateur de
  l'extension : il ne distingue plus un accord donné librement.
- Le parcours site à site et son service simulé (ADR-0001), hors panneau, restent dans le code et
  dans le ZIP : leur retrait est une décision à part.
