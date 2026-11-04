import { prisma } from "./prisma";

export const DEFAULT_SETTINGS = {
  toggles: {
    engines: { rao: true, chokoisky: true, frawley: true },
    rao: { nation_charts: true, planetary_influence: true },
    chokoisky: {
      victory_houses: true, sky_pky: true, d1_cusps: true, d9_cusps: true,
      nama_pada: true, sublords: true, nakshatra_tara: true, planetary_war: true,
    },
    frawley: {
      house_placement: true, antiscia: true, moon_placement: true, fortuna: true,
      moon_aspects: true, dispositor: true, misc: true,
    },
  },
  ml: {
    post_hoc_weight: 0.5,
    min_sample: null as number | null,      // null = milestone defaults (10 / 15 / 20)
    min_accuracy: null as number | null,    // null = milestone defaults (65% / 70% / 75%)
    max_combo_length: 3,
    p_threshold: 0.05,
    nightly: true,
    nightly_timezone: "UTC",
  },
  sync: {
    leagues: ["en.1", "de.1", "es.1", "it.1", "fr.1"] as string[],
    auto: true,              // refresh upcoming games and results while the app runs
    interval_hours: 6,
    days_ahead: 14,          // add upcoming fixtures this far ahead
    days_back: 45,           // add finished games not yet in the dataset from this far back
    retrain_after: true,     // retrain the ML model when a sync adds results
    api_key: "",             // optional football-data.org key (faster results, exact kickoff times)
  },
  ayanamsha: { rao: "lahiri", chokoisky: "lahiri", chokoisky_sublords: "krishnamurti", frawley: "tropical" },
  sport_presets: {} as Record<string, unknown>,
};
export type Settings = typeof DEFAULT_SETTINGS;

function merge<T>(base: T, over: any): T {
  if (!over || typeof over !== "object" || Array.isArray(over)) return (over ?? base) as T;
  const out: any = Array.isArray(base) ? [...(base as any)] : { ...(base as any) };
  for (const [k, v] of Object.entries(over)) {
    out[k] = v && typeof v === "object" && !Array.isArray(v) && (base as any)?.[k] && typeof (base as any)[k] === "object"
      ? merge((base as any)[k], v)
      : v;
  }
  return out;
}

export async function getSettings(): Promise<Settings> {
  const rows = await prisma.setting.findMany();
  let s: Settings = DEFAULT_SETTINGS;
  for (const r of rows) s = merge(s, { [r.key]: r.value });
  return s;
}

export async function saveSettings(patch: Partial<Settings>) {
  const current = await getSettings();
  for (const [key, value] of Object.entries(patch)) {
    const merged = merge((current as any)[key], value);
    await prisma.setting.upsert({ where: { key }, create: { key, value: merged as any }, update: { value: merged as any } });
  }
  return getSettings();
}
