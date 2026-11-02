import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

export async function PATCH(req: Request, ctx: RouteContext<"/api/venues/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const b = await req.json();
    return prisma.venue.update({
      where: { id },
      data: { name: b.name, canonicalName: b.canonicalName ?? undefined, lat: Number(b.lat), long: Number(b.long),
        timezone: b.timezone ?? undefined, coordinateSource: b.coordinateSource || "manual", lastVerifiedAt: new Date() },
    });
  });
}

export async function DELETE(_req: Request, ctx: RouteContext<"/api/venues/[id]">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const used = await prisma.match.count({ where: { venueId: id } });
    if (used) return Response.json({ error: `Venue is used by ${used} matches` }, { status: 409 });
    await prisma.venue.delete({ where: { id } });
    return { ok: true };
  });
}
