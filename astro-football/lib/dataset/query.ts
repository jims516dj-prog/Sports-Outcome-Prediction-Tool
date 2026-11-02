// Server-side filtering for the dataset browser and exports (spec 9.3).
import { Prisma } from "@prisma/client";
import { prisma } from "@/lib/prisma";

export type DatasetFilters = {
  q?: string; from?: string; to?: string; sport?: string; status?: string;
  agreement?: "all3" | "two" | "none"; correct?: "correct" | "incorrect" | "pending";
  mlPattern?: "yes" | "no"; captain?: "yes" | "no"; showDeleted?: boolean;
  sort?: string; dir?: "asc" | "desc"; page?: number; pageSize?: number;
};

export function parseFilters(sp: URLSearchParams, admin: boolean): DatasetFilters {
  const g = (k: string) => sp.get(k) || undefined;
  return {
    q: g("q"), from: g("from"), to: g("to"), sport: g("sport"), status: g("status"),
    agreement: g("agreement") as DatasetFilters["agreement"], correct: g("correct") as DatasetFilters["correct"],
    mlPattern: g("mlPattern") as DatasetFilters["mlPattern"], captain: g("captain") as DatasetFilters["captain"],
    showDeleted: admin && sp.get("showDeleted") === "1",
    sort: g("sort"), dir: sp.get("dir") === "asc" ? "asc" : "desc",
    page: Math.max(1, Number(sp.get("page") ?? 1)), pageSize: Math.min(500, Math.max(5, Number(sp.get("pageSize") ?? 25))),
  };
}

const ACTUAL = Prisma.sql`CASE WHEN m."scoreA" IS NULL OR m."scoreB" IS NULL THEN NULL
  WHEN m."scoreA" > m."scoreB" THEN 'A' WHEN m."scoreA" < m."scoreB" THEN 'B' ELSE 'draw' END`;

function where(f: DatasetFilters) {
  const c: Prisma.Sql[] = [];
  if (!f.showDeleted) c.push(Prisma.sql`NOT m.deleted`);
  if (f.q) c.push(Prisma.sql`(ta.name ILIKE ${"%" + f.q + "%"} OR tb.name ILIKE ${"%" + f.q + "%"} OR v.name ILIKE ${"%" + f.q + "%"})`);
  if (f.from) c.push(Prisma.sql`m."kickoffGMT" >= ${new Date(f.from)}`);
  if (f.to) c.push(Prisma.sql`m."kickoffGMT" < ${new Date(new Date(f.to).getTime() + 86400000)}`);
  if (f.sport) c.push(Prisma.sql`m.sport = ${f.sport}`);
  if (f.status) c.push(Prisma.sql`m.status = ${f.status}`);
  if (f.agreement === "all3") c.push(Prisma.sql`(m.synthesis->>'agreement')::int = 3`);
  if (f.agreement === "two") c.push(Prisma.sql`(m.synthesis->>'agreement')::int = 2`);
  if (f.agreement === "none") c.push(Prisma.sql`(m.synthesis->>'agreement')::int <= 1`);
  if (f.correct === "pending") c.push(Prisma.sql`(m."scoreA" IS NULL OR m."scoreB" IS NULL)`);
  if (f.correct === "correct") c.push(Prisma.sql`m.synthesis->>'winner' = (${ACTUAL})`);
  if (f.correct === "incorrect") c.push(Prisma.sql`m.synthesis->>'winner' <> (${ACTUAL})`);
  if (f.mlPattern === "yes") c.push(Prisma.sql`jsonb_array_length(coalesce(m."mlPatternMatches", '[]'::jsonb)) > 0`);
  if (f.mlPattern === "no") c.push(Prisma.sql`jsonb_array_length(coalesce(m."mlPatternMatches", '[]'::jsonb)) = 0`);
  if (f.captain === "yes") c.push(Prisma.sql`m."hasCaptainData"`);
  if (f.captain === "no") c.push(Prisma.sql`NOT m."hasCaptainData"`);
  return c.length ? Prisma.sql`WHERE ${Prisma.join(c, " AND ")}` : Prisma.empty;
}

const SORTS: Record<string, Prisma.Sql> = {
  date: Prisma.sql`m."kickoffGMT"`, teamA: Prisma.sql`ta.name`, teamB: Prisma.sql`tb.name`, status: Prisma.sql`m.status`,
  venue: Prisma.sql`v.name`, agreement: Prisma.sql`(m.synthesis->>'agreement')::int`,
};

export type DatasetRow = {
  id: string; kickoffGMT: Date; kickoffLocal: string; teamA: string; teamB: string; scoreA: number | null;
  scoreB: number | null; status: string; sport: string; context: string; venue: string; predicted: string | null;
  actual: string | null; agreement: number | null; pattern: string | null; mlCount: number; notes: string | null;
  hasCaptainData: boolean; postHoc: boolean; stale: boolean; deleted: boolean; confidence: number | null;
  oddsA: number; oddsB: number; oddsDraw: number | null;
};

export async function listMatches(f: DatasetFilters, all = false) {
  const w = where(f);
  const order = SORTS[f.sort ?? "date"] ?? SORTS.date;
  const dir = f.dir === "asc" ? Prisma.sql`ASC` : Prisma.sql`DESC`;
  const page = all ? Prisma.empty : Prisma.sql`LIMIT ${f.pageSize ?? 25} OFFSET ${((f.page ?? 1) - 1) * (f.pageSize ?? 25)}`;
  const base = Prisma.sql`FROM "Match" m JOIN "Team" ta ON ta.id = m."teamAId" JOIN "Team" tb ON tb.id = m."teamBId"
    JOIN "Venue" v ON v.id = m."venueId" ${w}`;
  const [rows, count] = await Promise.all([
    prisma.$queryRaw<DatasetRow[]>`SELECT m.id, m."kickoffGMT", m."kickoffLocal", ta."displayName" AS "teamA",
        tb."displayName" AS "teamB", m."scoreA", m."scoreB", m.status, m.sport, m.context, v.name AS venue,
        m.synthesis->>'winner' AS predicted, ${ACTUAL} AS actual, (m.synthesis->>'agreement')::int AS agreement,
        m.synthesis->>'pattern' AS pattern,
        jsonb_array_length(coalesce(m."mlPatternMatches", '[]'::jsonb))::int AS "mlCount", m.notes,
        m."hasCaptainData", m."postHocAnalysis" AS "postHoc", m."staleAnalysis" AS stale, m.deleted,
        (m.synthesis->'ml'->>'finalConfidence')::int AS confidence, m."oddsA", m."oddsB", m."oddsDraw"
      ${base} ORDER BY ${order} ${dir}, m.id ${page}`,
    prisma.$queryRaw<{ n: bigint }[]>`SELECT count(*) AS n ${base}`,
  ]);
  return { rows, total: Number(count[0]?.n ?? 0) };
}
