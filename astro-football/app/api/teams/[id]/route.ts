import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";
import { teamData } from "@/lib/dataset/teams";

export async function PATCH(req: Request, ctx: RouteContext<"/api/teams/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    return prisma.team.update({ where: { id }, data: teamData(await req.json()) as any });
  });
}

export async function DELETE(_req: Request, ctx: RouteContext<"/api/teams/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const used = await prisma.match.count({ where: { OR: [{ teamAId: id }, { teamBId: id }] } });
    if (used) return Response.json({ error: `Team is used by ${used} matches` }, { status: 409 });
    await prisma.team.delete({ where: { id } });
    return { ok: true };
  });
}
