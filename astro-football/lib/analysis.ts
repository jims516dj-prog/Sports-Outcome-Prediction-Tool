// Builds the Python-service request from a match record, runs the three engines and
// applies the current ML weights. Returns the Match columns to persist.
import { Prisma, type Match, type Team, type Venue } from "@prisma/client";
import { astro } from "@/lib/astro";
import { applyWeights, getCurrentModel } from "@/lib/ml/weights_provider";
import { getSettings } from "@/lib/settings";

export type MatchWithRefs = Match & { teamA: Team; teamB: Team; venue: Venue };

const iso = (d: Date) => d.toISOString().slice(0, 16);

function founding(t: Team) {
  if (!t.foundingDate) return null;
  return {
    date: t.foundingDate.toISOString().slice(0, 10),
    time: t.foundingTime || null,
    lat: t.foundingLat,
    long: t.foundingLong,
    tz: t.foundingTz || null,
  };
}

export async function buildServiceInput(m: MatchWithRefs, engineWeights?: Record<string, number>) {
  const s = await getSettings();
  return {
    team_a: m.teamA.displayName,
    team_b: m.teamB.displayName,
    kickoff_gmt: iso(m.kickoffGMT),
    lat: m.venue.lat,
    long: m.venue.long,
    sport: m.sport,
    context: m.context,
    odds_a: m.oddsA,
    odds_b: m.oddsB,
    odds_draw: m.oddsDraw,
    founding_a: founding(m.teamA),
    founding_b: founding(m.teamB),
    has_captain_data: m.hasCaptainData,
    captain_a_jersey: m.captainAJersey,
    captain_b_jersey: m.captainBJersey,
    team_a_jersey_color: m.teamAJerseyColor,
    team_b_jersey_color: m.teamBJerseyColor,
    toggles: s.toggles,
    engine_weights: engineWeights ?? {},
  };
}

const J = (v: unknown) => (v === null || v === undefined ? Prisma.DbNull : (v as Prisma.InputJsonValue));

export async function analyzeMatch(m: MatchWithRefs, reason: string) {
  const model = await getCurrentModel();
  const body = await buildServiceInput(m, model.engineWeights);
  const res = await astro.analyze(body);
  const ml = applyWeights(res.synthesis, res.ml_features, model);
  const synthesis = {
    ...res.synthesis,
    ml,
    warnings: res.warnings,
    sandhi: res.sandhi,
    local: res.local,
    frawley_notice: res.frawley_notice,
    input: res.input,
    post_hoc: m.postHocAnalysis,
  };
  const version = {
    timestamp: new Date().toISOString(),
    reason,
    hasCaptainData: m.hasCaptainData,
    postHoc: m.postHocAnalysis,
    verdicts: { rao: res.rao, chokoisky: res.chokoisky, frawley: res.frawley },
    synthesis,
  };
  const prior = Array.isArray(m.analysisVersions) ? (m.analysisVersions as unknown[]) : [];
  return {
    data: {
      kickoffLocal: res.local.local,
      timezone: res.local.timezone,
      chartD1Rao: J(res.charts.rao),
      chartD1Chokoisky: J(res.charts.chokoisky),
      chartD9Chokoisky: J(res.charts.chokoisky_d9),
      chartD1Frawley: J(res.charts.frawley),
      verdictRao: J(res.rao),
      verdictChokoisky: J(res.chokoisky),
      verdictFrawley: J(res.frawley),
      synthesis: J(synthesis),
      mlFeatures: J(res.ml_features),
      mlPatternMatches: J(ml.matchedIds),
      mlConfidenceMultiplier: ml.multiplier,
      analysisVersions: J([...prior, version]),
      staleAnalysis: false,
    } satisfies Prisma.MatchUpdateInput,
    res,
    ml,
  };
}
