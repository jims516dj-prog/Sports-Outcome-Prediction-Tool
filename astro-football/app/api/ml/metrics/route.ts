import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

export async function GET() {
  return handle(async () => {
    const [versions, byStatus, completedAnalysed] = await Promise.all([
      prisma.mLModelVersion.findMany({ orderBy: { versionNumber: "desc" }, take: 10 }),
      prisma.match.groupBy({ by: ["status"], where: { deleted: false }, _count: true }),
      prisma.match.count({ where: { deleted: false, status: "completed", NOT: { mlFeatures: { equals: null as any } } } }),
    ]);
    return { versions, byStatus: Object.fromEntries(byStatus.map((s) => [s.status, s._count])), completedAnalysed };
  });
}
