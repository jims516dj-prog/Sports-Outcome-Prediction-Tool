// Combination discovery runs in the Python service (ml_pipeline.py, spec 12.3/12.6);
// this module triggers it and reads the results.
import { astro } from "@/lib/astro";
import { prisma } from "@/lib/prisma";
import { getSettings } from "@/lib/settings";

export async function retrain() {
  const s = await getSettings();
  return astro.train({
    post_hoc_weight: s.ml.post_hoc_weight,
    min_sample: s.ml.min_sample,
    min_accuracy: s.ml.min_accuracy,
    max_combo_length: s.ml.max_combo_length,
    p_threshold: s.ml.p_threshold,
  });
}

export async function rollback(versionNumber: number) {
  const target = await prisma.mLModelVersion.findUnique({ where: { versionNumber } });
  if (!target) throw new Error(`Model version ${versionNumber} not found`);
  await prisma.$transaction([
    prisma.mLModelVersion.updateMany({ data: { isCurrent: false } }),
    prisma.mLModelVersion.update({ where: { id: target.id }, data: { isCurrent: true } }),
    // later versions stay stored (audit) but their combinations are deactivated
    prisma.mLCombination.updateMany({
      where: { modelVersion: { versionNumber: { gt: versionNumber } } },
      data: { active: false },
    }),
    prisma.mLCombination.updateMany({ where: { modelVersionId: target.id }, data: { active: true } }),
  ]);
  return target;
}
