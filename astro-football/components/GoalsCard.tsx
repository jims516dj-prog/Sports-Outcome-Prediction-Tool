"use client";
// Goal markets for one match: the statistical model's over/under 2.5 and both-teams-to-score
// prediction next to what the astrology engines' scoreline implies, and the result once played.
import { useEffect, useState } from "react";
import { Badge, Card, pct } from "@/components/ui";
import { api } from "@/lib/client";

const parseScore = (s?: string | null) => {
  const m = s?.match(/^(\d+)\s*[–-]\s*(\d+)$/);
  return m ? [Number(m[1]), Number(m[2])] : null;
};

export function GoalsCard({ match }: { match: any }) {
  const [metrics, setMetrics] = useState<any>(null);
  useEffect(() => { api("/api/ml/goals").then((r) => setMetrics(r.goals)).catch(() => setMetrics(null)); }, []);
  if (match.sport !== "football") return null;
  const gp = match.goalsPrediction;
  const likely = gp?.astrology?.likely_score ?? match.synthesis?.goal_range?.likely;
  const ls = parseScore(likely);
  const played = match.scoreA != null && match.scoreB != null;
  const actual = played ? { over25: match.scoreA + match.scoreB >= 3, btts: match.scoreA > 0 && match.scoreB > 0 } : null;
  const astro = ls ? { over25: ls[0] + ls[1] >= 3, btts: ls[0] > 0 && ls[1] > 0 } : null;
  const rows = [
    { key: "over25", label: "Over / under 2.5 goals", yes: "Over 2.5", no: "Under 2.5" },
    { key: "btts", label: "Both teams to score", yes: "Yes", no: "No" },
  ] as const;
  const mark = (pick: boolean | undefined, key: "over25" | "btts") =>
    actual && pick !== undefined ? (pick === actual[key] ? <Badge tone="green">✓</Badge> : <Badge tone="red">✗</Badge>) : null;

  return (
    <Card accent="#2a78d6">
      <div className="px-5 py-3 border-b border-rule flex flex-wrap justify-between gap-2">
        <h2 className="font-semibold text-lg">Goals: over/under 2.5 &amp; both teams to score</h2>
        {played ? <span className="font-sans text-sm">Result {match.scoreA}–{match.scoreB}: <strong>{actual!.over25 ? "over" : "under"} 2.5</strong>, both scored: <strong>{actual!.btts ? "yes" : "no"}</strong></span> : null}
      </div>
      <div className="p-5 grid md:grid-cols-2 gap-6">
        <div>
          <div className="label mb-1">Statistical model {gp?.trained === false ? "(Poisson only — not enough history to train yet)" : gp?.model_version ? `(model v${gp.model_version})` : ""}</div>
          {gp ? (
            <>
              <table className="w-full text-sm">
                <tbody>
                  {rows.map((r) => {
                    const g = gp[r.key];
                    return (
                      <tr key={r.key} className="border-t border-rule">
                        <td className="py-1.5">{r.label}</td>
                        <td className="font-semibold">{g.pick ? r.yes : r.no}</td>
                        <td className="num">{pct(g.pick ? g.p : 1 - g.p)}</td>
                        <td>{g.strong ? <Badge tone="teal">strong pick</Badge> : null} {mark(g.pick, r.key)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="font-sans text-xs text-slate-600 mt-2">Expected goals {gp.xg_home}–{gp.xg_away}. Built from both teams&apos; recent scoring and conceding and a Poisson goals model, learned from every finished match in the dataset.</p>
            </>
          ) : (
            <p className="text-sm text-slate-600">{played ? "This match was added after it was played, so no pre-match goals prediction was made." : "No prediction yet — retrain the model on the ML Training page."}</p>
          )}
        </div>
        <div>
          <div className="label mb-1">Astrology (from the engines&apos; most likely scoreline)</div>
          {astro ? (
            <table className="w-full text-sm">
              <tbody>
                <tr className="border-t border-rule"><td className="py-1.5">Most likely score</td><td className="num font-semibold" colSpan={2}>{likely}</td></tr>
                {rows.map((r) => (
                  <tr key={r.key} className="border-t border-rule">
                    <td className="py-1.5">{r.label}</td>
                    <td className="font-semibold">{astro[r.key] ? r.yes : r.no}</td>
                    <td>{mark(astro[r.key], r.key)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-sm text-slate-600">No scoreline in the synthesis.</p>}
        </div>
      </div>
      {metrics?.markets ? (
        <div className="px-5 pb-4 font-sans text-xs text-slate-600 border-t border-rule pt-3">
          On {metrics.markets.over25.n_test.toLocaleString()} recent matches the models never trained on, the statistical model was right {pct(metrics.markets.over25.methods[metrics.markets.over25.chosen].accuracy)} on over/under and {pct(metrics.markets.btts.methods[metrics.markets.btts.chosen].accuracy)} on both-teams-to-score; the astrology scoreline was right {pct(metrics.markets.over25.methods.astrology_scoreline_rule.accuracy)} and {pct(metrics.markets.btts.methods.astrology_scoreline_rule.accuracy)}. Always picking the more common outcome scored {pct(metrics.markets.over25.methods.always_more_common.accuracy)} and {pct(metrics.markets.btts.methods.always_more_common.accuracy)}.
        </div>
      ) : null}
    </Card>
  );
}
