"""Historical dataset ML subsystem (spec section 12).

Transparent combination discovery: conditional accuracy of the synthesised verdict
inside feature combinations, chi-squared filtered, weighted 1 + (acc - 0.5) * 2.

Two safeguards are added on top of the specification and shown on the dashboard,
never hidden:
  * favourite baseline - how often simply backing the favourite was right in the
    same matches (a pattern that only selects heavy favourites is not astrology)
  * holdout accuracy - discovery is re-run on the oldest 70% of matches and every
    pattern is scored on the newest 30% it never saw
"""
from __future__ import annotations

import itertools
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import psycopg
from scipy.stats import chi2_contingency

MODEL_DIR = os.environ.get("ML_MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))

DEFAULT_CONFIG = {"post_hoc_weight": 0.5, "min_sample": None, "min_accuracy": None, "max_combo_length": 3,
                  "p_threshold": 0.05}

BOOL_FEATURES = {
    "chokoisky_d9_cusp_strong_planet_present": "D9 cusp planet present",
    "chokoisky_sky_present": "SKY present",
    "frawley_lord_on_enemy_cusp": "Frawley: lord on enemy cusp",
    "frawley_moon_final_aspect_late": "Frawley: Moon's final aspect late (late-goal flag)",
    "frawley_pluto_on_1st_cusp": "Frawley: Pluto on 1st cusp",
    "d9_jupiter_on_favorite_cusp": "D9 Jupiter on favourite's cusp",
    "d9_saturn_on_favorite_cusp": "D9 Saturn on favourite's cusp",
    "d9_mars_on_either_cusp": "D9 Mars on either cusp",
    "lord_1_on_7th_cusp_tropical": "Lord 1 on 7th cusp (Frawley strong testimony)",
    "lord_7_on_1st_cusp_tropical": "Lord 7 on 1st cusp",
    "antiscion_fortuna_on_1st_or_7th_cusp": "Antiscion of Fortuna on 1st/7th cusp",
    "rao_saturn_in_8th_nation_chart": "Rao: Saturn on 8th of nation chart",
    "rao_planetary_influence_included": "Rao: captain data included",
    "nama_pad_fav_match": "Nama pada matches favourite",
    "nama_pad_und_match": "Nama pada matches underdog",
    "sandhi_window_active": "Sandhi window active",
}
CAT_FEATURES = {
    "rao_pick": "Rao picks", "chokoisky_pick": "Chokoisky picks", "frawley_pick": "Frawley picks",
    "agreement_pattern": "Agreement", "engine_agreement_count": "Engines agreeing",
    "moon_final_aspect_to": "Moon's final aspect to", "rao_captain_jersey_match_date_relation": "Captain jersey vs date",
    "planetary_war_winner_rel": "Planetary war won by", "major_tara_rel": "Major tara on", "context": "Context",
}
THRESHOLDS = {"sublord_dominance>9": ("chokoisky_sublord_dominance", 9, "Sublord dominance > 9"),
              "rao_point_diff>8": ("rao_point_differential", 8, "Rao point diff > 8"),
              "rao_point_diff>5": ("rao_point_differential", 5, "Rao point diff > 5"),
              "chokoisky_total>9": ("chokoisky_total", 9, "Chokoisky total beyond ±9")}


# ------------------------------------------------------------------ feature extraction (12.2)
def extract_features(res: dict, inp: dict) -> dict:
    r, k, f, s, syn = res.get("rao"), res.get("chokoisky"), res.get("frawley"), res["sandhi"], res["synthesis"]
    fav = inp["fav_side"]
    rel = lambda v: {"A": "fav" if fav == "A" else "und", "B": "fav" if fav == "B" else "und"}.get(v, v)
    v = syn["verdicts"]
    jersey_rel = "none"
    if r and r.get("planetary_influence_included"):
        jersey_rel = res.get("jersey_relation", "neutral")
    tara = "none"
    if k and k.get("tara_hits"):
        for h in k["tara_hits"]:
            star = h.split(" ")[0]
            if star in ("Regulus", "Pollux", "Vega"):
                side = "fav" if "(fav" in h else "und"
                tara = f"{star}_{'A' if (side == 'fav') == (fav == 'A') else 'B'}"
                break
    pwar = k.get("planetary_war_winner") if k else None
    feats = {
        "rao_verdict": v.get("rao", "disabled"), "chokoisky_verdict": v.get("chokoisky", "disabled"),
        "frawley_verdict": v.get("frawley", "disabled"),
        "rao_pick": rel(v.get("rao", "disabled")), "chokoisky_pick": rel(v.get("chokoisky", "disabled")),
        "frawley_pick": rel(v.get("frawley", "disabled")),
        "engine_agreement_count": syn["agreement"], "agreement_pattern": syn["pattern"],
        "rao_point_differential": r["diff"] if r else 0.0,
        "chokoisky_total": k["total"] if k else 0.0,
        "chokoisky_d9_cusp_strong_planet_present": bool(k and k["d9_cusp_planet"]),
        "chokoisky_sky_present": bool(k and k["sky"]),
        "chokoisky_sublord_dominance": k["sublord_diff"] if k else 0.0,
        "frawley_testimony_count": f["n_testimonies"] if f else 0,
        "frawley_lord_on_enemy_cusp": bool(f and any(t["kind"] == "placement" and t["strength"] != "weak"
                                                     for t in f["testimonies"])),
        "frawley_moon_final_aspect_late": bool(f and f["late_goal"]),
        "frawley_pluto_on_1st_cusp": bool(f and f["pluto_on_1st"]),
        "d9_jupiter_on_favorite_cusp": bool(k and k["d9_jupiter_on_fav_cusp"]),
        "d9_saturn_on_favorite_cusp": bool(k and k["d9_saturn_on_fav_cusp"]),
        "d9_mars_on_either_cusp": bool(k and k["d9_mars_on_cusp"]),
        "lord_1_on_7th_cusp_tropical": bool(f and f["lord1_on_7th"]),
        "lord_7_on_1st_cusp_tropical": bool(f and f["lord7_on_1st"]),
        "antiscion_fortuna_on_1st_or_7th_cusp": bool(f and f["antiscion_fortuna_on_1_or_7"]),
        "moon_final_aspect_to": f["moon_final_aspect_to"] if f else "none",
        "rao_saturn_in_8th_nation_chart": bool(r and r["saturn_8th"]),
        "rao_planetary_influence_included": bool(r and r["planetary_influence_included"]),
        "rao_captain_jersey_match_date_relation": jersey_rel,
        "nama_pad_a_match": bool(k and (k["nama_pada_fav"] if fav == "A" else k["nama_pada_und"])),
        "nama_pad_b_match": bool(k and (k["nama_pada_und"] if fav == "A" else k["nama_pada_fav"])),
        "nama_pad_fav_match": bool(k and k["nama_pada_fav"]), "nama_pad_und_match": bool(k and k["nama_pada_und"]),
        "planetary_war_winner_team": ("none" if not pwar else (fav if pwar == "fav" else ("B" if fav == "A" else "A"))),
        "planetary_war_winner_rel": pwar or "none",
        "major_tara_on_significator": tara,
        "major_tara_rel": "none" if tara == "none" else ("fav" if tara.endswith("_" + fav) else "und"),
        "sandhi_window_active": bool(s["any"]),
        "sport": inp["sport"], "context": inp["context"], "draw_possible": inp["draw_possible"],
        "odds_differential": round(abs(inp["odds_a"] - inp["odds_b"]), 3),
        "favourite_side": fav, "consensus_winner": syn["winner"],
    }
    return feats


# ------------------------------------------------------------------ conditions
def build_conditions(F: pd.DataFrame):
    conds = {}
    for col, label in CAT_FEATURES.items():
        if col not in F:
            continue
        for val in F[col].dropna().unique():
            if str(val) in ("none", "disabled"):
                continue
            conds[f"{col}={val}"] = ((F[col] == val).values, f"{label}: {val}", col, val)
    for col, label in BOOL_FEATURES.items():
        if col in F:
            m = F[col].fillna(False).astype(bool).values
            if m.any():
                conds[col] = (m, label, col, True)
    for key, (col, thr, label) in THRESHOLDS.items():
        if col in F:
            conds[key] = ((F[col].abs() > thr).values, label, col, f">{thr}")
    return conds


def milestone(n, cfg):
    if n < 30:
        return None
    if n < 100:
        ms = dict(max_len=1, min_n=10, min_acc=0.65)
    elif n < 500:
        ms = dict(max_len=2, min_n=15, min_acc=0.70)
    else:
        ms = dict(max_len=3, min_n=20, min_acc=0.75)
    ms["max_len"] = min(ms["max_len"], cfg.get("max_combo_length") or 3)
    if cfg.get("min_sample"):
        ms["min_n"] = int(cfg["min_sample"])
    if cfg.get("min_accuracy"):
        ms["min_acc"] = float(cfg["min_accuracy"])
    return ms


def discover(F, correct, weights, idx, ms, p_thr=0.05):
    """Apriori-style search over 1..max_len feature combinations within rows `idx`."""
    conds = build_conditions(F)
    keys = [k for k, (m, *_rest) in conds.items() if (m & idx).sum() >= ms["min_n"]]
    found, acc_of = [], {}

    def evaluate(combo):
        m = idx.copy()
        for kk in combo:
            m &= conds[kk][0]
        n = int(m.sum())
        if n < ms["min_n"]:
            return None, m
        w = weights[m]
        acc = float((correct[m] * w).sum() / w.sum())
        return (n, acc), m

    level = [(k,) for k in keys]
    for L in range(1, ms["max_len"] + 1):
        nxt = []
        for combo in level:
            if len({conds[k][2] for k in combo}) < len(combo):
                continue                                  # two values of the same feature
            res, m = evaluate(combo)
            if res is None:
                continue
            n, acc = res
            acc_of[combo] = acc
            nxt.append(combo)
            if acc < ms["min_acc"]:
                continue
            if L > 1 and acc <= max(acc_of.get((k,), 0) for k in combo):
                continue                                  # must improve on its components
            k_in, rest = int(correct[m].sum()), idx & ~m
            if rest.sum() == 0:
                continue
            k_out = int(correct[rest].sum())
            p = chi2_contingency([[k_in, n - k_in], [k_out, int(rest.sum()) - k_out]])[1]
            if p < p_thr:
                found.append({"keys": combo, "n": n, "correct": k_in, "accuracy": acc, "p": float(p), "mask": m})
        if L < ms["max_len"]:
            level = sorted({tuple(sorted(set(a) | {b})) for a in nxt for b in keys
                            if b not in a and len(set(a) | {b}) == L + 1})
    return found, conds


# ------------------------------------------------------------------ data access
def load_dataset(conn):
    rows = conn.execute("""
        SELECT m.id, m."kickoffGMT", m."scoreA", m."scoreB", m."postHocAnalysis", m."mlFeatures", m.synthesis,
               m."hasCaptainData"
        FROM "Match" m
        WHERE m.status = 'completed' AND NOT m.deleted AND m."mlFeatures" IS NOT NULL
          AND m."scoreA" IS NOT NULL AND m."scoreB" IS NOT NULL
        ORDER BY m."kickoffGMT" """).fetchall()
    recs = []
    for mid, ko, sa, sb, ph, feats, syn, cap in rows:
        feats = feats if isinstance(feats, dict) else json.loads(feats)
        actual = "A" if sa > sb else ("B" if sb > sa else "draw")
        recs.append({"id": mid, "kickoff": ko, "post_hoc": ph, "actual": actual, **feats})
    return pd.DataFrame(recs)


def train(db_url: str, config: dict | None = None) -> dict:
    cfg = DEFAULT_CONFIG | (config or {})
    with psycopg.connect(db_url) as conn:
        F = load_dataset(conn)
        prev = conn.execute('SELECT id, "overallAccuracy", "versionNumber" FROM "MLModelVersion" '
                            'ORDER BY "versionNumber" DESC LIMIT 1').fetchone()
        prev_combos = {}
        if prev:
            for desc, acc in conn.execute('SELECT description, accuracy FROM "MLCombination" WHERE "modelVersionId"=%s',
                                          (prev[0],)).fetchall():
                prev_combos[desc] = acc
        n = len(F)
        now = datetime.now(timezone.utc)
        summary = {"matchesTrained": n, "previousAccuracy": prev[1] if prev else None}
        if n == 0:
            return summary | {"coldStart": True, "message": "No completed matches with analyses yet."}
        weights = np.where(F.post_hoc.values, cfg["post_hoc_weight"], 1.0)
        pred = F.consensus_winner.values
        correct = (pred == F.actual.values).astype(float)
        wacc = lambda m: float((correct[m] * weights[m]).sum() / weights[m].sum()) if m.any() else None
        all_rows = np.ones(n, bool)
        fav_hit = (F.favourite_side.values == F.actual.values).astype(float)

        def eng_acc(col, m=all_rows):
            mm = m & (F[col].values != "disabled")
            if not mm.any():
                return None
            c = (F[col].values[mm] == F.actual.values[mm]).astype(float)
            return float((c * weights[mm]).sum() / weights[mm].sum())

        engine_acc = {"rao": eng_acc("rao_verdict"), "chokoisky": eng_acc("chokoisky_verdict"),
                      "frawley": eng_acc("frawley_verdict"), "consensus": wacc(all_rows),
                      "favourite_baseline": float(fav_hit.mean())}
        cold = n < 30
        engine_weights = {e: (1.0 if cold or engine_acc[e] is None else
                              float(np.clip(1 + (engine_acc[e] - 0.5) * 2, 0.1, 3.0)))
                          for e in ("rao", "chokoisky", "frawley")}
        # time windows (30/60/90 days before now, and all time)
        ko = pd.to_datetime(F.kickoff, utc=True)
        windows = {}
        for d in (30, 60, 90):
            m = (ko >= now - timedelta(days=d)).values
            windows[f"last_{d}_days"] = {"n": int(m.sum()), **{e: eng_acc(f"{e}_verdict", m) for e in
                                                             ("rao", "chokoisky", "frawley")},
                                         "consensus": wacc(m), "favourite_baseline":
                                             float(fav_hit[m].mean()) if m.any() else None}
        windows["all_time"] = {"n": n, **{e: engine_acc[e] for e in ("rao", "chokoisky", "frawley")},
                               "consensus": engine_acc["consensus"], "favourite_baseline": engine_acc["favourite_baseline"]}
        post_hoc_split = {"post_hoc": wacc(F.post_hoc.values.astype(bool)),
                          "real_time": wacc(~F.post_hoc.values.astype(bool))}

        ms = milestone(n, cfg)
        found, conds, holdout = [], {}, None
        if ms:
            found, conds = discover(F, correct, weights, all_rows, ms, cfg["p_threshold"])
            # holdout: discover on oldest 70%, score on newest 30%
            cut = int(n * 0.7)
            old, new = np.zeros(n, bool), np.zeros(n, bool)
            old[:cut], new[cut:] = True, True
            ms_old = milestone(cut, cfg)
            ho = {}
            if ms_old and new.sum() >= 10:
                found_old, _ = discover(F, correct, weights, old, ms_old, cfg["p_threshold"])
                flagged = np.zeros(n, bool)
                for c in found_old:
                    m = new.copy()
                    for kk in c["keys"]:
                        m &= conds[kk][0] if kk in conds else np.zeros(n, bool)
                    ho[c["keys"]] = (wacc(m), int(m.sum()))
                    flagged |= m
                holdout = {"patterns_found_on_older_70pct": len(found_old),
                           "mean_accuracy_when_found": float(np.mean([c["accuracy"] for c in found_old])) if found_old else None,
                           "newer_30pct_matches_flagged": int(flagged.sum()),
                           "newer_30pct_accuracy": wacc(flagged) if flagged.any() else None,
                           "newer_30pct_favourite_baseline": float(fav_hit[flagged].mean()) if flagged.any() else None}
            for c in found:
                c["holdout"] = ho.get(c["keys"], (None, None))

        version = (prev[2] + 1) if prev else 1
        vid = "mv_" + uuid.uuid4().hex[:20]
        os.makedirs(MODEL_DIR, exist_ok=True)
        artifact = os.path.join(MODEL_DIR, f"model_v{version}.joblib")
        combos_out = []
        for c in sorted(found, key=lambda x: -x["accuracy"]):
            desc = " AND ".join(conds[k][1] for k in c["keys"])
            w = float(min(3.0, 1 + (c["accuracy"] - 0.5) * 2))
            pa = prev_combos.get(desc)
            trend = None if pa is None else ("up" if c["accuracy"] > pa + 0.005 else
                                             ("down" if c["accuracy"] < pa - 0.005 else "flat"))
            combos_out.append({"id": "mc_" + uuid.uuid4().hex[:20], "description": desc, "keys": list(c["keys"]),
                               "values": {k: (conds[k][3] if not isinstance(conds[k][3], (np.generic,))
                                              else conds[k][3].item()) for k in c["keys"]},
                               "featureColumns": {k: conds[k][2] for k in c["keys"]},
                               "n": c["n"], "correct": c["correct"], "accuracy": c["accuracy"], "weight": w,
                               "p": c["p"], "fav_base": float(fav_hit[c["mask"]].mean()),
                               "holdout_acc": c["holdout"][0], "holdout_n": c["holdout"][1], "trend": trend,
                               "mask": c["mask"]})
        joblib.dump({"version": version, "combinations": [{k: v for k, v in x.items() if k != "mask"}
                                                         for x in combos_out],
                     "engine_weights": engine_weights, "config": cfg, "trained_at": now.isoformat()}, artifact)
        metrics = {"windows": windows, "holdout": holdout, "post_hoc_split": post_hoc_split, "milestone": ms,
                   "cold_start": cold}
        with conn.transaction():
            conn.execute('UPDATE "MLModelVersion" SET "isCurrent" = false')
            conn.execute('INSERT INTO "MLModelVersion" (id, "versionNumber", "trainedAt", "overallAccuracy", '
                         '"engineAccuracies", "engineWeights", metrics, "combinationCount", "sampleSize", '
                         '"isCurrent", "modelArtifactPath") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s)',
                         (vid, version, now, engine_acc["consensus"] or 0.0, json.dumps(engine_acc),
                          json.dumps(engine_weights), json.dumps(metrics, default=float), len(combos_out), n, artifact))
            ids, preds, acts = F.id.values, F.consensus_winner.values, F.actual.values
            for c in combos_out:
                conn.execute('INSERT INTO "MLCombination" (id, "modelVersionId", description, "featureKeys", '
                             '"featureValues", "sampleSize", "correctCount", accuracy, weight, "pValue", '
                             '"favouriteBaseline", "holdoutAccuracy", "holdoutSize", trend, "lastTrainedAt", active) '
                             'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)',
                             (c["id"], vid, c["description"], c["keys"],
                              json.dumps({"values": c["values"], "columns": c["featureColumns"]}, default=str),
                              c["n"], c["correct"], c["accuracy"], c["weight"], c["p"], c["fav_base"],
                              c["holdout_acc"], c["holdout_n"], c["trend"], now))
                with conn.cursor() as cur:
                    cur.executemany('INSERT INTO "MLCombinationMatch" (id, "combinationId", "matchId", predicted, '
                                    'actual, correct) VALUES (%s,%s,%s,%s,%s,%s)',
                                    [("cm_" + uuid.uuid4().hex[:20], c["id"], ids[i], preds[i], acts[i],
                                      bool(preds[i] == acts[i])) for i in np.flatnonzero(c["mask"])])
        return summary | {"version": version, "combinationsDiscovered": len(combos_out),
                          "overallAccuracy": engine_acc["consensus"], "engineAccuracies": engine_acc,
                          "engineWeights": engine_weights, "holdout": holdout, "coldStart": cold,
                          "milestone": ms}
