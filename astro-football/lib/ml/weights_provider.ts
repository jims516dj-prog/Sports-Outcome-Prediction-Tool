// Applies the current model's learned weights to a new analysis (spec 12.4 / 8.2).
import { prisma } from "@/lib/prisma";
import { conditionHolds, type Features } from "./feature_extractor";

export type CurrentModel = Awaited<ReturnType<typeof getCurrentModel>>;

export async function getCurrentModel() {
  const version = await prisma.mLModelVersion.findFirst({
    where: { isCurrent: true },
    include: { combinations: { where: { active: true } } },
  });
  const cold = !version || version.sampleSize < 30;
  return {
    version,
    cold,
    engineWeights: (cold ? { rao: 1, chokoisky: 1, frawley: 1 } : (version!.engineWeights as Record<string, number>)),
    combinations: version?.combinations ?? [],
  };
}

export function matchCombinations(features: Features, model: CurrentModel) {
  return model.combinations.filter((c) => {
    const fv = c.featureValues as { values: Record<string, unknown>; columns: Record<string, string> };
    return c.featureKeys.every((k) => conditionHolds(features, k, fv.columns?.[k] ?? k, fv.values?.[k]));
  });
}

export function applyWeights(synthesis: any, features: Features, model: CurrentModel) {
  const matched = model.cold ? [] : matchCombinations(features, model);
  const sumW = matched.reduce((s, c) => s + c.weight, 0);
  const multiplier = matched.length ? Math.min(2, 1 + sumW / 3) : 1;
  const base = synthesis.base_confidence ?? 0;
  const finalConfidence = Math.max(0, Math.min(100, Math.round(base * multiplier)));
  const avgAcc = matched.length ? matched.reduce((s, c) => s + c.accuracy, 0) / matched.length : null;
  const insights = matched
    .slice()
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 3)
    .map((c) => ({
      id: c.id,
      text: `${c.description} - ${c.correctCount} of ${c.sampleSize} correct (${Math.round(c.accuracy * 100)}%)`,
      accuracy: c.accuracy,
      sampleSize: c.sampleSize,
      favouriteBaseline: c.favouriteBaseline,
      holdoutAccuracy: c.holdoutAccuracy,
      holdoutSize: c.holdoutSize,
    }));
  return {
    multiplier,
    finalConfidence,
    matchedIds: matched.map((c) => c.id),
    banner: matched.length
      ? `Historical pattern: ${matched.length} matching combination${matched.length > 1 ? "s" : ""}, combined weight ${sumW.toFixed(1)}, average historical accuracy ${Math.round((avgAcc ?? 0) * 100)}%.`
      : model.cold
        ? "ML cold start - equal weights."
        : null,
    insights,
    modelVersion: model.version?.versionNumber ?? null,
    engineWeights: model.engineWeights,
  };
}
