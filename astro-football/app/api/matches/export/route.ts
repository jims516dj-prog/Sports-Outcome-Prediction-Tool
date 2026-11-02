import { handle, isAdmin } from "@/lib/api";
import { INCLUDE } from "@/lib/dataset/crud";
import { listMatches, parseFilters } from "@/lib/dataset/query";
import { prisma } from "@/lib/prisma";

const csvCell = (v: unknown) => {
  const s = v === null || v === undefined ? "" : v instanceof Date ? v.toISOString() : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

// ?format=csv (filtered rows) | json (full records incl. chart snapshots, for backup)
export async function GET(req: Request) {
  return handle(async () => {
    const sp = new URL(req.url).searchParams;
    const { rows } = await listMatches(parseFilters(sp, isAdmin(req)), true);
    const stamp = new Date().toISOString().slice(0, 10);
    if (sp.get("format") === "json") {
      const full = await prisma.match.findMany({ where: { id: { in: rows.map((r) => r.id) } }, include: INCLUDE, orderBy: { kickoffGMT: "asc" } });
      return new Response(JSON.stringify(full, null, 1), {
        headers: { "content-type": "application/json", "content-disposition": `attachment; filename="astro-football-${stamp}.json"` },
      });
    }
    const cols = ["id", "kickoffGMT", "kickoffLocal", "teamA", "teamB", "scoreA", "scoreB", "status", "sport", "context", "venue",
      "oddsA", "oddsB", "oddsDraw", "predicted", "actual", "agreement", "pattern", "confidence", "mlCount", "hasCaptainData",
      "postHoc", "stale", "notes"] as const;
    const lines = [cols.join(","), ...rows.map((r) => cols.map((c) => csvCell((r as any)[c])).join(","))];
    return new Response(lines.join("\n"), {
      headers: { "content-type": "text/csv", "content-disposition": `attachment; filename="astro-football-${stamp}.csv"` },
    });
  });
}
