// Match record operations: create (new / historical), edit with audit, re-analysis
// versions, mark result, soft delete (spec 9.3, 9.4, 12.7 - 12.11).
import { Prisma } from "@prisma/client";
import { analyzeMatch } from "@/lib/analysis";
import { prisma } from "@/lib/prisma";

export type FoundingInput = {
  date?: string | null; time?: string | null; place?: string | null;
  lat?: number | null; long?: number | null; tz?: string | null;
};
export type VenueInput = {
  name: string; lat: number; long: number; source?: string; pageId?: number | null;
  canonicalName?: string | null; timezone?: string | null;
};
export type MatchInput = {
  sport: string; context: string; teamA: string; teamB: string; kickoffGMT: string;
  venue: VenueInput; oddsA: number; oddsB: number; oddsDraw?: number | null;
  foundingA?: FoundingInput | null; foundingB?: FoundingInput | null;
  teamAType?: string; teamBType?: string;
  hasCaptainData?: boolean; captainAJersey?: number | null; captainBJersey?: number | null;
  teamAJerseyColor?: string | null; teamBJerseyColor?: string | null;
  scoreA?: number | null; scoreB?: number | null; status?: string; notes?: string | null;
  externalId?: string | null; league?: string | null; source?: string | null;
};

export const INCLUDE = { teamA: true, teamB: true, venue: true } as const;
const INPUT_FIELDS = ["sport", "context", "kickoffGMT", "teamAId", "teamBId", "venueId", "oddsA", "oddsB", "oddsDraw",
  "hasCaptainData", "captainAJersey", "captainBJersey", "teamAJerseyColor", "teamBJerseyColor"] as const;

export class CrudError extends Error {
  constructor(message: string, public status = 400) { super(message); }
}

const utc = (s: string) => new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");

async function upsertTeam(name: string, f?: FoundingInput | null, type?: string) {
  const data: Prisma.TeamUpdateInput = {};
  if (f && f.date) {
    data.foundingDate = new Date(f.date.slice(0, 10) + "T00:00:00Z");
    data.foundingTime = f.time || null;
    data.foundingPlace = f.place || null;
    data.foundingLat = f.lat ?? null;
    data.foundingLong = f.long ?? null;
    data.foundingTz = f.tz || null;
  }
  const existing = await prisma.team.findUnique({ where: { name } });
  if (existing) return Object.keys(data).length ? prisma.team.update({ where: { id: existing.id }, data }) : existing;
  return prisma.team.create({
    data: { ...(data as Prisma.TeamCreateInput), name, displayName: name, nationOrClub: type || "club" },
  });
}

async function upsertVenue(v: VenueInput) {
  const existing = await prisma.venue.findUnique({ where: { name: v.name } });
  const data = {
    lat: v.lat, long: v.long, coordinateSource: v.source || "manual", timezone: v.timezone ?? undefined,
    canonicalName: v.canonicalName ?? undefined, wikipediaPageId: v.pageId ?? undefined, lastVerifiedAt: new Date(),
  };
  if (existing) {
    const moved = Math.abs(existing.lat - v.lat) > 1e-6 || Math.abs(existing.long - v.long) > 1e-6;
    return moved ? prisma.venue.update({ where: { id: existing.id }, data }) : existing;
  }
  return prisma.venue.create({ data: { name: v.name, ...data } });
}

function validate(i: MatchInput, historical: boolean) {
  if (!i.teamA || !i.teamB) throw new CrudError("Both teams are required");
  if (i.teamA === i.teamB) throw new CrudError("Team A and Team B must differ");
  if (!i.kickoffGMT) throw new CrudError("Kickoff date and time (GMT) are required");
  if (!i.venue?.name || !Number.isFinite(i.venue.lat) || !Number.isFinite(i.venue.long))
    throw new CrudError("Venue name and coordinates are required (lookup or manual entry)");
  if (!(i.oddsA > 1) || !(i.oddsB > 1)) throw new CrudError("Decimal odds for both teams are required (> 1.0)");
  if (historical && (i.scoreA == null || i.scoreB == null) && (i.status ?? "completed") === "completed")
    throw new CrudError("A historical match needs the final scoreline");
}

export async function createMatch(i: MatchInput, opts: { historical: boolean }) {
  validate(i, opts.historical);
  const [teamA, teamB, venue] = await Promise.all([
    upsertTeam(i.teamA, i.foundingA, i.teamAType),
    upsertTeam(i.teamB, i.foundingB, i.teamBType),
    upsertVenue(i.venue),
  ]);
  const scored = i.scoreA != null && i.scoreB != null;
  const created = await prisma.match.create({
    data: {
      sport: i.sport || "football", context: i.context || "league", kickoffGMT: utc(i.kickoffGMT),
      kickoffLocal: i.kickoffGMT, teamAId: teamA.id, teamBId: teamB.id, venueId: venue.id,
      oddsA: i.oddsA, oddsB: i.oddsB, oddsDraw: i.oddsDraw ?? null,
      hasCaptainData: !!i.hasCaptainData,
      captainAJersey: i.hasCaptainData ? i.captainAJersey ?? null : null,
      captainBJersey: i.hasCaptainData ? i.captainBJersey ?? null : null,
      teamAJerseyColor: i.hasCaptainData ? i.teamAJerseyColor ?? null : null,
      teamBJerseyColor: i.hasCaptainData ? i.teamBJerseyColor ?? null : null,
      scoreA: opts.historical ? i.scoreA ?? null : null,
      scoreB: opts.historical ? i.scoreB ?? null : null,
      status: opts.historical ? (i.status || (scored ? "completed" : "pending")) : "pending",
      notes: i.notes ?? null,
      postHocAnalysis: opts.historical,
      externalId: i.externalId ?? null,
      league: i.league ?? null,
      source: i.source ?? null,
    },
    include: INCLUDE,
  });
  try {
    const { data } = await analyzeMatch(created, opts.historical ? "post-hoc analysis" : "initial analysis");
    return prisma.match.update({ where: { id: created.id }, data, include: INCLUDE });
  } catch (e) {
    await prisma.match.delete({ where: { id: created.id } });
    throw e;
  }
}

export async function reanalyze(id: string, reason = "re-analysis") {
  const m = await prisma.match.findUniqueOrThrow({ where: { id }, include: INCLUDE });
  const { data } = await analyzeMatch(m, reason);
  return prisma.match.update({ where: { id }, data, include: INCLUDE });
}

const str = (v: unknown) => (v === null || v === undefined ? null : v instanceof Date ? v.toISOString() : String(v));

/** Edit a record. rerun: "yes" re-runs the engines if inputs changed; "no" marks the analysis stale. */
export async function updateMatch(id: string, i: Partial<MatchInput>, opts: { rerun?: "yes" | "no"; admin?: boolean; editedBy?: string }) {
  const m = await prisma.match.findUniqueOrThrow({ where: { id }, include: INCLUDE });
  const patch: Record<string, unknown> = {};
  if (i.teamA !== undefined && i.teamA !== m.teamA.name) patch.teamAId = (await upsertTeam(i.teamA, i.foundingA, i.teamAType)).id;
  else if (i.foundingA) await upsertTeam(m.teamA.name, i.foundingA);
  if (i.teamB !== undefined && i.teamB !== m.teamB.name) patch.teamBId = (await upsertTeam(i.teamB, i.foundingB, i.teamBType)).id;
  else if (i.foundingB) await upsertTeam(m.teamB.name, i.foundingB);
  if (i.venue) {
    const v = await upsertVenue(i.venue);
    if (v.id !== m.venueId || v.lat !== m.venue.lat || v.long !== m.venue.long) patch.venueId = v.id;
  }
  if (i.kickoffGMT !== undefined && utc(i.kickoffGMT).getTime() !== m.kickoffGMT.getTime()) patch.kickoffGMT = utc(i.kickoffGMT);
  for (const k of ["sport", "context", "oddsA", "oddsB", "oddsDraw", "hasCaptainData", "captainAJersey", "captainBJersey",
    "teamAJerseyColor", "teamBJerseyColor", "notes"] as const) {
    if (i[k] !== undefined && (i[k] ?? null) !== ((m as any)[k] ?? null)) patch[k] = i[k] ?? null;
  }
  const wasCompleted = m.status === "completed";
  for (const k of ["scoreA", "scoreB", "status"] as const) {
    if (i[k] !== undefined && (i[k] ?? null) !== ((m as any)[k] ?? null)) {
      if (wasCompleted && !opts.admin)
        throw new CrudError("Completed records are immutable: scoreline and status cannot be changed (spec 12.11)", 403);
      patch[k] = i[k] ?? null;
    }
  }
  const sA = patch.scoreA !== undefined ? patch.scoreA : m.scoreA;
  const sB = patch.scoreB !== undefined ? patch.scoreB : m.scoreB;
  if (m.scoreA == null && m.scoreB == null && sA != null && sB != null && patch.status === undefined) patch.status = "completed";
  if (Object.keys(patch).length === 0) return { match: m, rerun: false, inputChanged: false };

  const inputChanged = Object.keys(patch).some((k) => (INPUT_FIELDS as readonly string[]).includes(k));
  await prisma.$transaction([
    ...Object.entries(patch).map(([fieldName, nv]) =>
      prisma.editAudit.create({
        data: { matchId: id, fieldName, oldValue: str((m as any)[fieldName]), newValue: str(nv), editedBy: opts.editedBy ?? "user" },
      }),
    ),
    prisma.match.update({ where: { id }, data: { ...(patch as Prisma.MatchUncheckedUpdateInput), staleAnalysis: inputChanged && opts.rerun !== "yes" ? true : undefined } }),
  ]);
  if (inputChanged && opts.rerun === "yes") {
    const captainAdded = patch.hasCaptainData === true;
    const match = await reanalyze(id, captainAdded ? "revised: captain/jersey data added" : "revised: inputs edited");
    return { match, rerun: true, inputChanged };
  }
  return { match: await prisma.match.findUniqueOrThrow({ where: { id }, include: INCLUDE }), rerun: false, inputChanged };
}

export async function softDelete(id: string, admin: boolean) {
  if (!admin) throw new CrudError("Only an admin can delete records (enable admin mode in Settings)", 403);
  await prisma.editAudit.create({ data: { matchId: id, fieldName: "deleted", oldValue: "false", newValue: "true", editedBy: "admin" } });
  return prisma.match.update({ where: { id }, data: { deleted: true } });
}
