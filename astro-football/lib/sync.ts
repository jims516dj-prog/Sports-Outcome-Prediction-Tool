// Data sync: import past seasons, add upcoming fixtures, and record results when games finish.
// Fixtures come from the Python service (/sources/plan); every match is created through the same
// createMatch / updateMatch path as a hand-entered one, so it is analysed, audited and versioned.
import { astro } from "@/lib/astro";
import { createMatch, updateMatch, type MatchInput } from "@/lib/dataset/crud";
import { retrain } from "@/lib/ml/combination_discoverer";
import { prisma } from "@/lib/prisma";
import { getSettings } from "@/lib/settings";

export type SyncMode = "history" | "refresh";
export type SyncJob = {
  id: string; mode: SyncMode; trigger: "manual" | "auto"; state: "running" | "done" | "error";
  step: string; startedAt: string; finishedAt?: string; leagues: string[]; seasons?: string;
  sources: string[]; total: number; done: number;
  created: number; results: number; rescheduled: number; postponed: number; linked: number;
  skipped: number; awaitingTime: number; failed: number;
  failures: string[]; warnings: string[]; retrained?: number | null; error?: string;
};
type PlanMatch = {
  id: string; league: string; season: string; date: string; kickoff_utc: string | null; home: string; away: string;
  score: [number, number] | null; status: "finished" | "scheduled" | "postponed" | "cancelled" | "live";
  round: string; source: string; odds: [number, number, number];
  venue: { name: string; lat: number; long: number; source: string };
};

const LEAGUE_NAMES: Record<string, string> = {
  "en.1": "Premier League", "de.1": "Bundesliga", "es.1": "La Liga", "it.1": "Serie A", "fr.1": "Ligue 1",
  "en.2": "Championship", "nl.1": "Eredivisie", "pt.1": "Primeira Liga",
};
const g = globalThis as unknown as { __astroSync?: { job: SyncJob | null } };
const state = (g.__astroSync ??= { job: null });

export const currentJob = () => state.job;

export async function recentRuns(): Promise<SyncJob[]> {
  const row = await prisma.setting.findUnique({ where: { key: "sync_runs" } });
  return Array.isArray(row?.value) ? (row!.value as unknown as SyncJob[]) : [];
}

async function persist(job: SyncJob) {
  const runs = (await recentRuns()).filter((r) => r.id !== job.id);
  const slim = { ...job, failures: job.failures.slice(0, 20), warnings: job.warnings.slice(0, 20) };
  const value = [slim, ...runs].slice(0, 10) as any;
  await prisma.setting.upsert({ where: { key: "sync_runs" }, create: { key: "sync_runs", value }, update: { value } });
}

export function startSync(mode: SyncMode, opts: { leagues?: string[]; fromSeason?: string; toSeason?: string; trigger?: "manual" | "auto" }) {
  if (state.job?.state === "running") throw new Error("A sync is already running - wait for it to finish");
  const job: SyncJob = {
    id: `sync_${Date.now()}`, mode, trigger: opts.trigger ?? "manual", state: "running", step: "Starting",
    startedAt: new Date().toISOString(), leagues: opts.leagues ?? [], seasons: mode === "history" ? `${opts.fromSeason}–${opts.toSeason}` : undefined,
    sources: [], total: 0, done: 0, created: 0, results: 0, rescheduled: 0, postponed: 0, linked: 0, skipped: 0,
    awaitingTime: 0, failed: 0, failures: [], warnings: [],
  };
  state.job = job;
  run(job, opts).catch(async (e) => {
    job.state = "error";
    job.error = e?.message ?? String(e);
    job.finishedAt = new Date().toISOString();
    await persist(job).catch(() => {});
  });
  return job;
}

async function pool<T>(items: T[], n: number, fn: (t: T) => Promise<void>) {
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, async () => {
    while (i < items.length) await fn(items[i++]);
  }));
}

const day = (d: Date) => d.toISOString().slice(0, 10);
const shift = (iso: string, days: number) => day(new Date(Date.parse(iso + "T12:00:00Z") + days * 86400000));

async function run(job: SyncJob, opts: { leagues?: string[]; fromSeason?: string; toSeason?: string }) {
  const s = await getSettings();
  job.leagues = opts.leagues?.length ? opts.leagues : s.sync.leagues;
  job.step = job.mode === "history" ? "Downloading past seasons" : "Downloading fixtures and results";
  const plan = await astro.sourcesPlan({
    mode: job.mode, leagues: job.leagues, from_season: opts.fromSeason, to_season: opts.toSeason,
    api_key: job.mode === "refresh" ? s.sync.api_key || null : null,
  });
  job.sources = plan.sources;
  job.warnings.push(...plan.warnings);

  job.step = "Comparing with the dataset";
  const existing = await prisma.match.findMany({
    select: { id: true, externalId: true, status: true, kickoffGMT: true, notes: true,
      teamA: { select: { name: true } }, teamB: { select: { name: true } } },
  });
  const byExt = new Map(existing.filter((m) => m.externalId).map((m) => [m.externalId!, m]));
  const byPair = new Map<string, (typeof existing)[number]>();
  for (const m of existing) byPair.set(`${m.teamA.name}|${m.teamB.name}|${day(m.kickoffGMT)}`, m);
  const find = (p: PlanMatch) => {
    const hit = byExt.get(p.id);
    if (hit) return hit;
    for (const d of [0, -1, 1]) {
      const m = byPair.get(`${p.home}|${p.away}|${shift(p.kickoff_utc?.slice(0, 10) ?? p.date, d)}`);
      if (m) return m;
    }
    return null;
  };
  const teams = await prisma.team.findMany({ where: { defaultVenue: { not: null } }, select: { name: true, defaultVenue: true } });
  const venues = new Map((await prisma.venue.findMany()).map((v) => [v.name, v]));
  const defaultVenue = new Map(teams.flatMap((t) => (venues.has(t.defaultVenue!) ? [[t.name, venues.get(t.defaultVenue!)!] as const] : [])));

  const now = Date.now();
  const ahead = now + s.sync.days_ahead * 86400000;
  const back = now - s.sync.days_back * 86400000;
  const tasks: (() => Promise<void>)[] = [];
  const claimed = new Set<string>();

  for (const p of plan.matches as PlanMatch[]) {
    const ex = find(p);
    const ko = p.kickoff_utc ? Date.parse(p.kickoff_utc + "Z") : null;
    if (ex) {
      if (!ex.externalId && !claimed.has(p.id)) {
        claimed.add(p.id);
        tasks.push(async () => {
          await prisma.match.update({ where: { id: ex.id }, data: { externalId: p.id, league: p.league, source: p.source } });
          job.linked++;
        });
      }
      if (job.mode === "history" || ex.status !== "pending") {
        job.skipped++;
        continue;
      }
      if (p.status === "finished" && p.score) {
        tasks.push(async () => {
          await updateMatch(ex.id, { scoreA: p.score![0], scoreB: p.score![1], status: "completed" }, { editedBy: `auto-sync (${p.source})` });
          job.results++;
        });
      } else if (ko && Math.abs(ko - ex.kickoffGMT.getTime()) > 5 * 60000 && p.status === "scheduled") {
        tasks.push(async () => {
          await updateMatch(ex.id, { kickoffGMT: p.kickoff_utc! }, { rerun: "yes", editedBy: `auto-sync (${p.source})` });
          job.rescheduled++;
        });
      } else if (p.status === "postponed" && !(ex.notes ?? "").includes("Postponed")) {
        tasks.push(async () => {
          await updateMatch(ex.id, { notes: `${ex.notes ? ex.notes + " · " : ""}Postponed (per ${p.source})` }, { editedBy: "auto-sync" });
          job.postponed++;
        });
      } else job.skipped++;
      continue;
    }
    if (claimed.has(p.id)) continue;
    if (!ko) {
      if (p.status === "scheduled" && Date.parse(p.date + "T12:00:00Z") <= ahead) job.awaitingTime++;
      continue;
    }
    const finished = p.status === "finished" && !!p.score;
    const wanted = job.mode === "history" ? finished
      : (finished && ko >= back) || (p.status === "scheduled" && ko > now && ko <= ahead);
    if (!wanted) continue;
    claimed.add(p.id);
    tasks.push(async () => {
      const v = defaultVenue.get(p.home);
      const input: MatchInput = {
        sport: "football", context: "league", teamA: p.home, teamB: p.away, kickoffGMT: p.kickoff_utc!,
        venue: v ? { name: v.name, lat: v.lat, long: v.long, source: v.coordinateSource } : p.venue,
        oddsA: p.odds[0], oddsDraw: p.odds[1], oddsB: p.odds[2],
        scoreA: finished ? p.score![0] : null, scoreB: finished ? p.score![1] : null,
        status: finished ? "completed" : "pending",
        notes: `${LEAGUE_NAMES[p.league] ?? p.league} ${p.season}${p.round ? `, ${p.round}` : ""}. From ${p.source}; odds derived from Elo ratings, not bookmaker odds.`,
        externalId: p.id, league: p.league, source: p.source,
      };
      await createMatch(input, { historical: finished });
      job.created++;
    });
  }

  job.total = tasks.length;
  job.step = tasks.length ? `Analysing and saving ${tasks.length.toLocaleString()} changes` : "Nothing new";
  await pool(tasks, 6, async (t) => {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        await t();
        break;
      } catch (e: any) {
        // two parallel creations of the same new team can collide once; retry
        if (attempt === 0 && e?.code === "P2002") continue;
        job.failed++;
        if (job.failures.length < 50) job.failures.push(e?.message?.slice(0, 200) ?? String(e));
        break;
      }
    }
    job.done++;
  });

  if (s.sync.retrain_after && job.created + job.results > 0) {
    job.step = "Retraining the ML model";
    try {
      const r = await retrain();
      job.retrained = r.version ?? null;
    } catch (e: any) {
      job.warnings.push(`Retraining failed: ${e.message}`);
    }
  }
  job.state = "done";
  job.step = "Finished";
  job.finishedAt = new Date().toISOString();
  await persist(job);
}
