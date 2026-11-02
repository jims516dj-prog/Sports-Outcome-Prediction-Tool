// ML features (spec 12.2) are computed by the Python service at analysis time and stored
// on Match.mlFeatures. These helpers read them back and evaluate discovered conditions.

export type Features = Record<string, string | number | boolean | null>;

export function readFeatures(raw: unknown): Features {
  return raw && typeof raw === "object" ? (raw as Features) : {};
}

/** Condition keys produced by ml_pipeline.build_conditions:
 *  "col=value" (categorical), "col" (boolean true), "<name>>N" (|numeric| > N). */
export function conditionHolds(f: Features, key: string, column: string, value: unknown): boolean {
  if (typeof value === "string" && value.startsWith(">")) {
    const v = Number(f[column]);
    return Number.isFinite(v) && Math.abs(v) > Number(value.slice(1));
  }
  if (value === true) return f[column] === true;
  return String(f[column]) === String(value);
}

export const FEATURE_LABELS: Record<string, string> = {
  rao_verdict: "Rao verdict", chokoisky_verdict: "Chokoisky verdict", frawley_verdict: "Frawley verdict",
  engine_agreement_count: "Engines agreeing", agreement_pattern: "Agreement pattern",
  rao_point_differential: "Rao point differential", chokoisky_total: "Chokoisky total",
  chokoisky_sublord_dominance: "Sublord dominance", frawley_testimony_count: "Frawley testimonies",
  moon_final_aspect_to: "Moon's final aspect to", major_tara_on_significator: "Major tara",
  planetary_war_winner_team: "Planetary war winner", sandhi_window_active: "Sandhi window",
  odds_differential: "Odds differential",
};
