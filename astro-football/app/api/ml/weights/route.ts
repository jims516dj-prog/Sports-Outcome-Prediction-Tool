import { handle } from "@/lib/api";
import { getCurrentModel } from "@/lib/ml/weights_provider";

export async function GET() {
  return handle(async () => {
    const m = await getCurrentModel();
    return { version: m.version?.versionNumber ?? null, cold: m.cold, engineWeights: m.engineWeights, combinations: m.combinations };
  });
}
