// Fige les réponses simulées du plugin en exécutant le calcul Mutafriches sur les
// scénarios fictifs. Le plugin n'embarque que le JSON produit, jamais l'algorithme.
//
// Usage (depuis la racine du dépôt plugin) : ./outils/figer-reponses.sh
// Prérequis : dépôt mutafriches voisin avec node_modules installés et shared-types compilé.

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";

const RACINE_PLUGIN = resolve(__dirname, "..");
const MUTAFRICHES = resolve(process.env.MUTAFRICHES_DIR ?? join(RACINE_PLUGIN, "..", "mutafriches"));
const API = join(MUTAFRICHES, "apps", "api");
const SOURCES = join(RACINE_PLUGIN, "outils", "sources-scenarios");
const SORTIE = join(RACINE_PLUGIN, "mutafriches", "demo", "scenarios");

interface Variante {
  id: string;
  titre: string;
  reponses: Record<string, string>;
}

interface SourceScenario {
  id: string;
  titre: string;
  description: string;
  nomSuggere: string;
  parcelles: string[];
  echecsAvantSucces: number;
  enrichissement: Record<string, unknown>;
  variantes: Variante[];
}

async function main(): Promise<void> {
  createRequire(join(API, "package.json"))("reflect-metadata");
  const { CalculService } = (await import(
    join(API, "src", "evaluation", "services", "calcul.service.ts")
  )) as typeof import("../../mutafriches/apps/api/src/evaluation/services/calcul.service");
  const { FiabiliteCalculator } = (await import(
    join(API, "src", "evaluation", "services", "algorithme", "fiabilite.calculator.ts")
  )) as typeof import("../../mutafriches/apps/api/src/evaluation/services/algorithme/fiabilite.calculator");
  const { Site } = (await import(join(API, "src", "evaluation", "entities", "site.entity.ts"))) as typeof import("../../mutafriches/apps/api/src/evaluation/entities/site.entity");
  const { VERSION_COURANTE } = (await import(
    join(API, "src", "evaluation", "services", "algorithme", "versions", "index.ts")
  )) as { VERSION_COURANTE: string };
  const sharedTypes = (await import(join(MUTAFRICHES, "packages", "shared-types", "dist", "index.js"))) as {
    deriverRaccordementEau: (surfaceBati?: number) => string;
  };

  const calcul = new CalculService(new FiabiliteCalculator());
  // Étiquettes du podium calculées par le code de l'interface web, pas recopiées dans le plugin
  const { getPodiumTags } = (await import(
    join(MUTAFRICHES, "apps", "ui", "src", "features", "resultats", "utils", "podiumTags.ts")
  )) as {
    getPodiumTags: (resultat: unknown, enrichissement: unknown, complementaires: unknown) => string[];
  };

  const evaluer = async (
    enrichissement: Record<string, unknown>,
    variantes: Variante[],
  ): Promise<Record<string, unknown>[]> => {
    const raccordementEau = sharedTypes.deriverRaccordementEau(
      enrichissement.surfaceBati as number | undefined,
    );
    const evaluations = [];
    for (const variante of variantes) {
      const donneesComplementaires = { ...variante.reponses, raccordementEau };
      const site = Site.fromEnrichissement(enrichissement as never, donneesComplementaires as never);
      const resultat = await calcul.calculer(site, { modeDetaille: true });
      for (const usage of resultat.resultats as unknown as Record<string, unknown>[]) {
        usage.tags = getPodiumTags(usage, enrichissement, donneesComplementaires);
      }
      evaluations.push({
        id: variante.id,
        titre: variante.titre,
        reponses: variante.reponses,
        donneesComplementaires,
        resultat,
      });
    }
    return evaluations;
  };

  // Profil générique : une série d'évaluations par point de la grille de surfaces
  const generique = JSON.parse(readFileSync(join(SOURCES, "generique.json"), "utf-8")) as {
    gabarit: Record<string, unknown>;
    points: { surfaceSite: number; surfaceBati: number }[];
    variantes: Variante[];
  };
  const points = [];
  for (const point of generique.points) {
    const enrichissement = { ...generique.gabarit, ...point };
    points.push({ ...point, evaluations: await evaluer(enrichissement, generique.variantes) });
  }
  writeFileSync(
    join(SORTIE, "..", "generique.json"),
    `${JSON.stringify(
      {
        avertissement:
          "Données fictives. Réponses figées par outils/figer-reponses.ts, ne pas éditer à la main.",
        versionAlgorithme: VERSION_COURANTE,
        figeLe: new Date().toISOString().slice(0, 10),
        gabarit: generique.gabarit,
        points,
      },
      // Compact : ce fichier dépasse sinon plusieurs Mo pour 54 évaluations
    )}\n`,
    "utf-8",
  );
  console.log(`generique (${VERSION_COURANTE}) -> ${points.length} points de grille`);

  for (const fichier of readdirSync(SOURCES)
    .filter((f) => f.endsWith(".json") && f !== "generique.json")
    .sort()) {
    const source = JSON.parse(readFileSync(join(SOURCES, fichier), "utf-8")) as SourceScenario;
    const enrichissement = source.enrichissement;
    const evaluations = (await evaluer(enrichissement, source.variantes)) as {
      id: string;
      resultat: { fiabilite: { note: number } };
    }[];

    const scenario = {
      avertissement:
        "Données fictives. Réponses figées par outils/figer-reponses.ts, ne pas éditer à la main.",
      versionAlgorithme: VERSION_COURANTE,
      figeLe: new Date().toISOString().slice(0, 10),
      id: source.id,
      titre: source.titre,
      description: source.description,
      nomSuggere: source.nomSuggere,
      parcelles: source.parcelles,
      echecsAvantSucces: source.echecsAvantSucces,
      enrichissement,
      evaluations,
    };
    writeFileSync(join(SORTIE, fichier), `${JSON.stringify(scenario, null, 2)}\n`, "utf-8");
    const resume = evaluations
      .map((e) => `${e.id}: fiabilité ${e.resultat.fiabilite.note}`)
      .join(", ");
    console.log(`${source.id} (${VERSION_COURANTE}) -> ${resume}`);
  }
}

main().catch((erreur: unknown) => {
  console.error(erreur);
  process.exit(1);
});
