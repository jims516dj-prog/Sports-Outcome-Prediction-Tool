import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { prisma } from "@/lib/prisma";

export async function GET() {
  return handle(async () => {
    const [byStatus, recent, model, teams, venues, upcoming] = await Promise.all([
      prisma.match.groupBy({ by: ["status"], where: { deleted: false }, _count: true }),
      prisma.match.findMany({
        where: { deleted: false }, orderBy: { createdAt: "desc" }, take: 8,
        select: { id: true, kickoffGMT: true, status: true, scoreA: true, scoreB: true, synthesis: true,
          teamA: { select: { displayName: true } }, teamB: { select: { displayName: true } } },
      }),
      prisma.mLModelVersion.findFirst({ where: { isCurrent: true } }),
      prisma.team.count(),
      prisma.venue.count(),
      prisma.match.findMany({
        where: { deleted: false, status: "pending", kickoffGMT: { gte: new Date(Date.now() - 3 * 3600000) } },
        orderBy: { kickoffGMT: "asc" }, take: 12,
        select: { id: true, kickoffGMT: true, kickoffLocal: true, league: true, synthesis: true, goalsPrediction: true,
          teamA: { select: { displayName: true } }, teamB: { select: { displayName: true } } },
      }),
    ]);
    let service: unknown = null;
    try {
      service = await astro.health();
    } catch (e: any) {
      service = { ok: false, error: e.message };
    }
    return {
      byStatus: Object.fromEntries(byStatus.map((s) => [s.status, s._count])),
      recent: recent.map((r) => ({ ...r, synthesis: r.synthesis ? { winner: (r.synthesis as any).winner, headline: (r.synthesis as any).headline, confidence: (r.synthesis as any).ml?.finalConfidence } : null })),
      upcoming: upcoming.map((u) => ({ ...u, synthesis: u.synthesis ? { winner: (u.synthesis as any).winner, confidence: (u.synthesis as any).ml?.finalConfidence } : null })),
      model, teams, venues, service,
    };
  });
}
