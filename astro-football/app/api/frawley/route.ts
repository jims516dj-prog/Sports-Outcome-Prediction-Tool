import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { getCurrentModel } from "@/lib/ml/weights_provider";
import { getSettings } from "@/lib/settings";

// Runs only the frawley engine for a service-format payload (see lib/analysis.ts buildServiceInput).
export async function POST(req: Request) {
  return handle(async () => {
    const body = await req.json();
    const [s, model] = await Promise.all([getSettings(), getCurrentModel()]);
    return astro.engine("frawley", { toggles: s.toggles, engine_weights: model.engineWeights, ...body });
  });
}
