import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

export async function GET(_req: Request, ctx: RouteContext<"/api/ml/combination/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const rows = await prisma.mLCombinationMatch.findMany({
      where: { combinationId: id },
      take: 200,
      orderBy: { match: { kickoffGMT: "desc" } },
      include: { match: { select: { id: true, kickoffGMT: true, scoreA: true, scoreB: true, teamA: { select: { displayName: true } }, teamB: { select: { displayName: true } } } } },
    });
    const total = await prisma.mLCombinationMatch.count({ where: { combinationId: id } });
    return { rows, total };
  });
}
