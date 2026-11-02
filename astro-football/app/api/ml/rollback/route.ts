import { handle } from "@/lib/api";
import { rollback } from "@/lib/ml/combination_discoverer";

export async function POST(req: Request) {
  return handle(async () => {
    const { versionNumber } = await req.json();
    const v = await rollback(Number(versionNumber));
    return { ok: true, versionNumber: v.versionNumber };
  });
}
