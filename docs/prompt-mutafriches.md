# Prompt pour le dépôt Mutafriches (volet M1 à M4)

À coller dans une session Claude Code ouverte dans `../mutafriches`.

```
Contexte : le plugin QGIS Mutafriches (dépôt voisin mutafriches-qgis, prototype V0, ADR-0002)
doit passer en implémentation réelle. Le plan complet est dans
../mutafriches-qgis/docs/plan-implementation-reelle.md, volet « Mutafriches » (M1 à M4). Lis-le
d'abord, puis CLAUDE.md et .claude/context/*.md de ce dépôt.

Objectif de cette session : M1, « clients d'intégration et clé d'API », puis M2 « tracking ».

1. Rédige un ADR (docs/adr, numéro suivant) : table integrateurs_clients, route
   POST /api/clients/inscription, guard X-API-Key en alternative à Origin, nouvelle valeur
   SourceUtilisation.API_CLIENT, integrateur = qgis:<id>, données personnelles (finalité,
   conservation 36 mois, purge), impact Metabase. Options envisagées et écartées : clé par
   origine (ADR-0011), partenaire_sites.
2. Implémente M1 : schéma Drizzle + migration, DTO class-validator, service, contrôleur avec
   Swagger, guard, tests unitaires et e2e, docs/integration/README.md et
   docs/acces-api-integrateur.md mis à jour, page /documentation-integration.
3. Implémente M2 : OriginGuard de POST /evenements ouvert aux clés d'API, integrateur lu depuis
   la clé, nouveaux TypeEvenement qgis_* avec migration de l'enum, mise à jour de
   docs/analytics-tracking.md et du bloc CASE Metabase.
4. Respecte le workflow du dépôt : branche dédiée, commits atomiques, pas de push.

Contraintes : ne pas casser le guard Origin existant pour les intégrateurs iframe ; ne pas
ajouter de dépendance ; conserver le rate limit global ; ne rien exposer d'une clé en clair
dans les logs ou Swagger.
```
