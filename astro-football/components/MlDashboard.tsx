"use client";
// ML Training Dashboard (spec 9.5 / 12.10).
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Alert, Badge, Button, Card, Select, Spinner, pct } from "@/components/ui";
import { api, fmtDate } from "@/lib/client";

// Categorical palette validated (scripts/validate_palette.js, light surface): fixed order, never cycled.
const ENGINE_COLORS = { consensus: "#2a78d6", rao: "#eda100", frawley: "#008300", chokoisky: "#6250d6" };
const COMBO_COLORS = { accuracy: "#2a78d6", favourite: "#eb6834", holdout: "#1baf7a" };
const AXIS = { stroke: "#94a3b8", fontSize: 11, fontFamily: "ui-sans-serif" };

type SortKey = "accuracy" | "sampleSize" | "weight";

export function MlDashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [weights, setWeights] = useState<any>(null);
  const [schedule, setSchedule] = useState<any>(null);
  const [training, setTraining] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("weight");
  const [open, setOpen] = useState<Record<string, any>>({});
  const [rb, setRb] = useState("");

  const load = useCallback(async () => {
    try {
      const [m, w] = await Promise.all([api("/api/ml/metrics"), api("/api/ml/weights")]);
      setMetrics(m);
      setWeights(w);
      api("/api/ml/schedule").then(setSchedule).catch(() => setSchedule({ enabled: false, error: true }));
    } catch (e: any) {
      setError(e.message);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const current = metrics?.versions?.find((v: any) => v.isCurrent) ?? null;
  const previous = current ? metrics.versions.find((v: any) => v.versionNumber < current.versionNumber) : null;
  const acc = current?.engineAccuracies ?? {};
  const windows = current?.metrics?.windows ?? {};
  const holdout = current?.metrics?.holdout;
  const total = metrics ? Object.values<number>(metrics.byStatus).reduce((a, b) => a + b, 0) : 0;
  const n = metrics?.completedAnalysed ?? 0;

  const windowData = ["last_30_days", "last_60_days", "last_90_days", "all_time"].map((k) => ({
    window: k === "all_time" ? "All time" : k.replace("last_", "Last ").replace("_days", " days"),
    n: windows[k]?.n ?? 0,
    consensus: windows[k]?.consensus, rao: windows[k]?.rao, frawley: windows[k]?.frawley, chokoisky: windows[k]?.chokoisky,
    favourite: windows[k]?.favourite_baseline,
  }));
  const combos = useMemo(() => [...(weights?.combinations ?? [])].sort((a, b) => b[sort] - a[sort]), [weights, sort]);
  const comboChart = combos.slice(0, 10).map((c: any, i: number) => ({
    name: `#${i + 1}`, description: c.description, accuracy: c.accuracy, favourite: c.favouriteBaseline, holdout: c.holdoutAccuracy, n: c.sampleSize,
  }));

  async function retrain() {
    setTraining(true);
    setError(null);
    setSummary(null);
    try {
      setSummary(await api("/api/ml/train", { method: "POST" }));
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  }

  async function toggleNightly(enabled: boolean) {
    try { setSchedule(await api("/api/ml/schedule", { method: "POST", body: JSON.stringify({ enabled }) })); } catch (e: any) { setError(e.message); }
  }

  async function expand(id: string) {
    if (open[id]) return setOpen((o) => { const c = { ...o }; delete c[id]; return c; });
    setOpen((o) => ({ ...o, [id]: "loading" }));
    try { const r = await api(`/api/ml/combination/${id}`); setOpen((o) => ({ ...o, [id]: r })); } catch (e: any) { setOpen((o) => ({ ...o, [id]: { error: e.message } })); }
  }

  if (!metrics) return error ? <Alert tone="red">{error}</Alert> : <Spinner label="Loading ML state…" />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <h1 className="text-2xl font-semibold">ML Training Dashboard</h1>
        <div className="flex gap-2 items-center flex-wrap font-sans text-sm">
          <Button variant="teal" onClick={retrain} disabled={training}>{training ? "Training…" : "Retrain now"}</Button>
          <label className="flex items-center gap-1.5"><input type="checkbox" checked={!!schedule?.enabled} onChange={(e) => toggleNightly(e.target.checked)} /> Nightly retrain (02:00)</label>
          {schedule?.next_run ? <span className="text-xs text-slate-500">next {fmtDate(schedule.next_run)}</span> : null}
          <Select value={rb} onChange={(e) => setRb(e.target.value)} className="w-72">
            <option value="">Rollback to…</option>
            {metrics.versions.map((v: any) => <option key={v.id} value={v.versionNumber} disabled={v.isCurrent}>v{v.versionNumber} · {fmtDate(v.trainedAt)} · {pct(v.overallAccuracy, 1)}{v.isCurrent ? " (current)" : ""}</option>)}
          </Select>
          <Button variant="secondary" disabled={!rb} onClick={async () => {
            if (!confirm(`Make v${rb} the current model? Later versions are kept for audit but deactivated.`)) return;
            try { await api("/api/ml/rollback", { method: "POST", body: JSON.stringify({ versionNumber: Number(rb) }) }); setRb(""); await load(); } catch (e: any) { setError(e.message); }
          }}>Apply</Button>
        </div>
      </div>
      {training ? <Spinner label="Training: extracting features, mining 1–3 feature combinations, chi-squared filtering, holdout validation…" /> : null}
      {error ? <Alert tone="red">{error}</Alert> : null}
      {summary ? (
        <Alert tone="teal">
          Trained v{summary.version} on {summary.matchesTrained} matches · {summary.combinationsDiscovered ?? 0} combinations ·
          consensus accuracy {pct(summary.overallAccuracy, 1)} (previous {pct(summary.previousAccuracy, 1)})
          {summary.coldStart ? " · cold start: equal engine weights" : ""}
        </Alert>
      ) : null}
      {n < 30 ? <Alert tone="amber">Dataset has {n} completed, analysed matches. Need 30 to start ML training. Currently in equal-weight mode.</Alert> : null}

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Matches in dataset" value={total.toLocaleString()} sub={Object.entries(metrics.byStatus).map(([k, v]) => `${k} ${v}`).join(" · ")} />
        <Stat label="Consensus accuracy" value={pct(current?.overallAccuracy, 1)} sub={`favourite baseline ${pct(acc.favourite_baseline, 1)}`} />
        <Stat label="Engine accuracy" value={`${pct(acc.rao, 0)} / ${pct(acc.chokoisky, 0)} / ${pct(acc.frawley, 0)}`} sub="Rao / Chokoisky / Frawley" />
        <Stat label="Last training" value={current ? `v${current.versionNumber}` : "—"} sub={current ? `${fmtDate(current.trainedAt)} · ${current.sampleSize} matches` : "never trained"} />
      </div>

      {current ? (
        <Card className="p-4">
          <h2 className="font-sans font-semibold">Engine weights used by the synthesis</h2>
          <p className="font-sans text-xs text-slate-500 mb-2">weight = 1 + (accuracy − 0.5) × 2, clipped to 0.1–3.0 · equal (1.0) until 30 matches</p>
          <div className="flex gap-4 font-sans text-sm">{Object.entries<number>(current.engineWeights).map(([k, w]) => <span key={k}><strong className="capitalize">{k}</strong> <span className="num">{w.toFixed(2)}</span></span>)}</div>
        </Card>
      ) : null}

      {holdout ? (
        <Card className="p-4" accent="#0f766e">
          <h2 className="font-sans font-semibold">Out-of-sample check (added safeguard)</h2>
          <p className="text-sm mt-1">
            Patterns mined on the oldest 70% of matches: <strong>{holdout.patterns_found_on_older_70pct}</strong> (average {pct(holdout.mean_accuracy_when_found)} when found).
            On the newest 30% they never saw, they flagged <strong>{holdout.newer_30pct_matches_flagged}</strong> matches and were right <strong>{pct(holdout.newer_30pct_accuracy)}</strong> of the time,
            vs <strong>{pct(holdout.newer_30pct_favourite_baseline)}</strong> for simply backing the favourite in those same matches.
          </p>
          <p className="font-sans text-xs text-slate-500 mt-1">A pattern only carries information if it holds on matches it was not discovered from and beats the favourite baseline.</p>
        </Card>
      ) : null}

      <Card className="p-4">
        <h2 className="font-sans font-semibold">Accuracy by engine over time</h2>
        <p className="font-sans text-xs text-slate-500 mb-2">Share of completed matches each engine called correctly (home/draw/away). Windows count back from today.</p>
        {current ? (
          <>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={windowData} barGap={2} barCategoryGap="22%">
                  <CartesianGrid vertical={false} stroke="#eef0f3" />
                  <XAxis dataKey="window" tick={AXIS} axisLine={{ stroke: "#cbd5e1" }} tickLine={false} />
                  <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} domain={[0, 1]} tick={AXIS} axisLine={false} tickLine={false} width={40} />
                  <Tooltip formatter={(v: any, k: any) => [pct(v, 1), k]} cursor={{ fill: "#f1f5f9" }} contentStyle={{ fontFamily: "ui-sans-serif", fontSize: 12 }} />
                  <Legend itemSorter={null} wrapperStyle={{ fontFamily: "ui-sans-serif", fontSize: 12 }} />
                  {acc.favourite_baseline != null ? <ReferenceLine y={acc.favourite_baseline} stroke="#475569" strokeDasharray="0" label={{ value: `pick the favourite (all time) ${pct(acc.favourite_baseline)}`, position: "insideTopRight", fill: "#475569", fontSize: 11 }} /> : null}
                  {(["consensus", "rao", "frawley", "chokoisky"] as const).map((k) => (
                    <Bar key={k} dataKey={k} name={k === "consensus" ? "Consensus" : k[0].toUpperCase() + k.slice(1)} fill={ENGINE_COLORS[k]} maxBarSize={24} radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
            <table className="w-full text-xs mt-2 font-sans">
              <thead><tr className="label text-left"><th>Window</th><th>Matches</th><th>Consensus</th><th>Rao</th><th>Chokoisky</th><th>Frawley</th><th>Favourite baseline</th></tr></thead>
              <tbody>{windowData.map((w) => <tr key={w.window} className="border-t border-rule"><td>{w.window}</td><td className="num">{w.n}</td><td className="num">{pct(w.consensus, 1)}</td><td className="num">{pct(w.rao, 1)}</td><td className="num">{pct(w.chokoisky, 1)}</td><td className="num">{pct(w.frawley, 1)}</td><td className="num">{pct(w.favourite, 1)}</td></tr>)}</tbody>
            </table>
          </>
        ) : <p className="text-sm text-slate-500">No model trained yet.</p>}
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap justify-between items-center gap-2 mb-2">
          <div>
            <h2 className="font-sans font-semibold">Discovered combinations {weights?.version ? `(model v${weights.version})` : ""}</h2>
            <p className="font-sans text-xs text-slate-500">Accuracy of the synthesised verdict inside each pattern; weight = 1 + (accuracy − 0.5) × 2, capped at 3.0. Click a row for its matches.</p>
          </div>
          <div className="flex gap-1 font-sans text-xs items-center">sort by
            {(["weight", "accuracy", "sampleSize"] as SortKey[]).map((k) => <Button key={k} variant={sort === k ? "primary" : "secondary"} onClick={() => setSort(k)}>{k === "sampleSize" ? "sample size" : k}</Button>)}
          </div>
        </div>
        {comboChart.length ? (
          <div className="h-64 mb-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comboChart} barGap={2} barCategoryGap="25%">
                <CartesianGrid vertical={false} stroke="#eef0f3" />
                <XAxis dataKey="name" tick={AXIS} axisLine={{ stroke: "#cbd5e1" }} tickLine={false} />
                <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} domain={[0, 1]} tick={AXIS} axisLine={false} tickLine={false} width={40} />
                <Tooltip
                  cursor={{ fill: "#f1f5f9" }}
                  contentStyle={{ fontFamily: "ui-sans-serif", fontSize: 12, maxWidth: 360, whiteSpace: "normal" }}
                  labelFormatter={(_l, p: any) => (p?.[0] ? `${p[0].payload.description} (n=${p[0].payload.n})` : "")}
                  formatter={(v: any, k: any) => [v == null ? "not validated" : pct(v, 1), k]}
                />
                <Legend itemSorter={null} wrapperStyle={{ fontFamily: "ui-sans-serif", fontSize: 12 }} />
                <Bar dataKey="accuracy" name="Historical accuracy" fill={COMBO_COLORS.accuracy} maxBarSize={24} radius={[4, 4, 0, 0]} />
                <Bar dataKey="favourite" name="Picking the favourite, same matches" fill={COMBO_COLORS.favourite} maxBarSize={24} radius={[4, 4, 0, 0]} />
                <Bar dataKey="holdout" name="Holdout (newer 30%)" fill={COMBO_COLORS.holdout} maxBarSize={24} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="label text-left border-b border-rule [&>th]:px-2"><th className="py-1.5">#</th><th>Combination</th><th>Sample size</th><th>Historical accuracy</th><th>Favourite baseline</th><th>Holdout</th><th>p</th><th>Weight</th><th>Trend</th></tr></thead>
            <tbody>
              {combos.map((c: any, i: number) => (
                <Fragment key={c.id}>
                  <tr className="border-b border-rule hover:bg-slate-50 cursor-pointer [&>td]:px-2" onClick={() => expand(c.id)}>
                    <td className="py-1.5 num text-xs">{i + 1}</td>
                    <td>{c.description}</td>
                    <td className="num">{c.sampleSize}</td>
                    <td className="num">{pct(c.accuracy, 1)}</td>
                    <td className="num">{pct(c.favouriteBaseline, 1)}</td>
                    <td className="num whitespace-nowrap">{c.holdoutAccuracy == null ? <span className="text-xs text-slate-500">not found in older data</span> : `${pct(c.holdoutAccuracy, 1)} (n=${c.holdoutSize})`}</td>
                    <td className="num text-xs whitespace-nowrap">{c.pValue?.toExponential?.(1)}</td>
                    <td className="num font-semibold">{c.weight.toFixed(2)}</td>
                    <td>{c.trend === "up" ? "↑" : c.trend === "down" ? "↓" : c.trend === "flat" ? "→" : <Badge tone="teal">new</Badge>}</td>
                  </tr>
                  {open[c.id] ? (
                    <tr className="bg-slate-50"><td /><td colSpan={8} className="py-2">
                      {open[c.id] === "loading" ? <Spinner label="Loading matches" /> : open[c.id].error ? <span className="text-red-700">{open[c.id].error}</span> : (
                        <div className="font-sans text-xs">
                          <div className="mb-1 text-slate-600">{open[c.id].total} matches{open[c.id].total > 200 ? " (latest 200 shown)" : ""}</div>
                          <div className="grid md:grid-cols-2 gap-x-6">
                            {open[c.id].rows.map((r: any) => (
                              <a key={r.id} href={`/dataset/${r.match.id}`} className="flex justify-between border-b border-rule py-0.5 hover:underline">
                                <span>{fmtDate(r.match.kickoffGMT).slice(0, 10)} {r.match.teamA.displayName} {r.match.scoreA}–{r.match.scoreB} {r.match.teamB.displayName}</span>
                                <span>predicted {r.predicted} {r.correct ? "✓" : "✗"}</span>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </td></tr>
                  ) : null}
                </Fragment>
              ))}
              {combos.length === 0 ? <tr><td colSpan={9} className="py-4 text-center text-slate-500">{current ? "No combination met the thresholds (sample size, accuracy, chi-squared p < 0.05)." : "Train a model to discover combinations."}</td></tr> : null}
            </tbody>
          </table>
        </div>
        {current?.metrics?.milestone ? <p className="font-sans text-xs text-slate-500 mt-2">Thresholds in force: up to {current.metrics.milestone.max_len}-feature combinations, n ≥ {current.metrics.milestone.min_n}, accuracy ≥ {pct(current.metrics.milestone.min_acc)}, χ² p &lt; 0.05.</p> : null}
      </Card>

      {previous && current ? <p className="font-sans text-xs text-slate-500">Previous model v{previous.versionNumber}: consensus {pct(previous.overallAccuracy, 1)} on {previous.sampleSize} matches, {previous.combinationCount} combinations.</p> : null}
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="p-4">
      <div className="label">{label}</div>
      <div className="text-2xl font-semibold num mt-1">{value}</div>
      {sub ? <div className="font-sans text-xs text-slate-500 mt-1">{sub}</div> : null}
    </Card>
  );
}
