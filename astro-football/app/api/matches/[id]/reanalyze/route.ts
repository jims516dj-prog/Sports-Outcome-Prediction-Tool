import { handle } from "@/lib/api";
import { reanalyze } from "@/lib/dataset/crud";

export async function POST(_req: Request, ctx: RouteContext<"/api/matches/[id]/reanalyze">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const m = await reanalyze(id, "re-analysis (manual)");
    return { id: m.id };
  });
}
