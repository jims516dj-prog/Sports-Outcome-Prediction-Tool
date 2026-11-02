import { handle, isAdmin } from "@/lib/api";
import { INCLUDE, softDelete, updateMatch, type MatchInput } from "@/lib/dataset/crud";
import { prisma } from "@/lib/prisma";

export async function GET(_req: Request, ctx: RouteContext<"/api/matches/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const match = await prisma.match.findUniqueOrThrow({
      where: { id },
      include: { ...INCLUDE, audits: { orderBy: { editedAt: "desc" } } },
    });
    const combos = Array.isArray(match.mlPatternMatches) && match.mlPatternMatches.length
      ? await prisma.mLCombination.findMany({ where: { id: { in: match.mlPatternMatches as string[] } } })
      : [];
    return { match, combos };
  });
}

// body: { input: Partial<MatchInput>, rerun?: "yes" | "no" }
export async function PATCH(req: Request, ctx: RouteContext<"/api/matches/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const { input, rerun } = (await req.json()) as { input: Partial<MatchInput>; rerun?: "yes" | "no" };
    const r = await updateMatch(id, input, { rerun, admin: isAdmin(req), editedBy: isAdmin(req) ? "admin" : "user" });
    return { id: r.match.id, rerun: r.rerun, inputChanged: r.inputChanged, stale: r.match.staleAnalysis };
  });
}

export async function DELETE(req: Request, ctx: RouteContext<"/api/matches/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    await softDelete(id, isAdmin(req));
    return { ok: true };
  });
}
