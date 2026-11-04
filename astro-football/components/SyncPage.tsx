"use client";
// Data sync: import past seasons, add upcoming fixtures automatically, refresh results.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Select, Spinner } from "@/components/ui";
import { api, fmtDate } from "@/lib/client";

type Job = {
  id: string; mode: "history" | "refresh"; trigger: string; state: "running" | "done" | "error"; step: string;
  startedAt: string; finishedAt?: string; leagues: string[]; seasons?: string; sources: string[]; total: number;
  done: number; created: number; results: number; rescheduled: number; postponed: number; linked: number;
  skipped: number; awaitingTime: number; failed: number; failures: string[]; warnings: string[];
  retrained?: number | null; error?: string;
};

const seasonsBetween = (first: string, last: string) => {
  const out: string[] = [];
  for (let y = Number(first.slice(0, 4)); y <= Number(last.slice(0, 4)); y++) out.push(`${y}-${String(y + 1).slice(2)}`);
  return out;
};

export function SyncPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [cfg, setCfg] = useState<any>(null);
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  const [hist, setHist] = useState<{ leagues: string[]; from: string; to: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await api("/api/sync");
      setData(d);
      setCfg((c: any) => c ?? d.settings);
      if (d.info?.last_complete_season)
        setHist((h) => h ?? { leagues: d.settings.leagues, from: seasonsBetween("2010-11", d.info.last_complete_season).slice(-3)[0], to: d.info.last_complete_season });
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const running = data?.job?.state === "running";
  useEffect(() => {
    if (!running) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [running, load]);

  async function start(body: any) {
    setError(null);
    try {
      await api("/api/sync", { method: "POST", body: JSON.stringify(body) });
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  }
  async function saveCfg() {
    const sync: any = { ...cfg };
    if (apiKey === "-") sync.api_key = "";
    else if (apiKey) sync.api_key = apiKey.trim();
    else delete sync.api_key;
    try {
      const s = await api("/api/settings", { method: "PUT", body: JSON.stringify({ sync }) });
      setCfg({ ...s.sync, api_key: s.sync.api_key ? "set" : "" });
      setApiKey("");
      setSaved("Saved");
      setTimeout(() => setSaved(null), 2500);
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (!data) return error ? <Alert tone="red">{error}</Alert> : <Spinner label="Loading…" />;
  const leagues: any[] = data.info?.leagues ?? [];
  const job: Job | null = data.job;
  const current = data.info?.current_season;
  const lastComplete = data.info?.last_complete_season;
  const toggle = (list: string[], code: string) => (list.includes(code) ? list.filter((x) => x !== code) : [...list, code]);
  const histSeasons = hist ? seasonsBetween(hist.from, hist.to).length : 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Data sync</h1>
        <p className="text-slate-600 mt-1 max-w-3xl">Bring past games into the dataset for the ML model to learn from, add upcoming fixtures automatically, and record results when games finish. Every match is analysed by the three engines exactly like one you enter by hand.</p>
      </div>
      {data.info?.error ? <Alert tone="red">Astrology service offline — start it first. ({data.info.error})</Alert> : null}
      {error ? <Alert tone="red">{error}</Alert> : null}

      {job ? <JobPanel job={job} /> : null}

      <Card className="p-5" accent="#0f766e">
        <div className="flex flex-wrap justify-between items-start gap-3">
          <div>
            <h2 className="text-lg font-semibold">Upcoming games &amp; results</h2>
            <p className="text-sm text-slate-600 max-w-2xl">Adds fixtures in the next <strong>{cfg.days_ahead} days</strong> as pending matches (analysed straight away), records the score of any pending match that has finished, moves rescheduled games, and adds finished games from the last {cfg.days_back} days that are missing. Season {current}.</p>
          </div>
          <Button variant="teal" disabled={running || !!data.info?.error} onClick={() => start({ mode: "refresh" })}>{running && job?.mode === "refresh" ? "Refreshing…" : "Refresh now"}</Button>
        </div>
        <div className="mt-4 grid md:grid-cols-2 gap-5">
          <div>
            <div className="label mb-1">Leagues</div>
            <div className="grid sm:grid-cols-2 gap-x-4">
              {leagues.map((l) => (
                <label key={l.code} className="font-sans text-sm flex gap-1.5 items-center py-0.5">
                  <input type="checkbox" checked={cfg.leagues.includes(l.code)} onChange={() => setCfg({ ...cfg, leagues: toggle(cfg.leagues, l.code) })} /> {l.name}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            <label className="font-sans text-sm flex gap-1.5 items-center">
              <input type="checkbox" checked={cfg.auto} onChange={(e) => setCfg({ ...cfg, auto: e.target.checked })} />
              Refresh automatically every
              <Select className="w-20" value={cfg.interval_hours} onChange={(e) => setCfg({ ...cfg, interval_hours: Number(e.target.value) })}>
                {[1, 3, 6, 12, 24].map((h) => <option key={h} value={h}>{h} h</option>)}
              </Select>
              while the app is running
            </label>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Days ahead"><Input type="number" min={1} max={60} value={cfg.days_ahead} onChange={(e) => setCfg({ ...cfg, days_ahead: Number(e.target.value) })} /></Field>
              <Field label="Days back"><Input type="number" min={1} max={365} value={cfg.days_back} onChange={(e) => setCfg({ ...cfg, days_back: Number(e.target.value) })} /></Field>
            </div>
            <label className="font-sans text-sm flex gap-1.5 items-center">
              <input type="checkbox" checked={cfg.retrain_after} onChange={(e) => setCfg({ ...cfg, retrain_after: e.target.checked })} /> Retrain the ML model after each sync that adds results
            </label>
          </div>
        </div>
        <div className="mt-4 border-t border-rule pt-4 grid md:grid-cols-[1fr_auto] gap-3 items-end">
          <Field
            label={<>football-data.org API key {cfg.api_key ? <Badge tone="green">saved</Badge> : <Badge>not set</Badge>}</>}
            hint={<>Optional but recommended: results within minutes and exact kickoff times. Free key at <a className="underline" href="https://www.football-data.org/client/register" target="_blank" rel="noreferrer">football-data.org/client/register</a>. Without it the app uses openfootball, which can be several weeks behind. Type <code>-</code> to remove a saved key.</>}
          >
            <Input type="password" placeholder={cfg.api_key ? "•••••••• (saved)" : "paste your key"} value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
          </Field>
          <div className="flex gap-2 items-center">
            <Button onClick={saveCfg}>Save settings</Button>
            {saved ? <span className="font-sans text-sm text-green-700">{saved}</span> : null}
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap justify-between items-start gap-3">
          <div>
            <h2 className="text-lg font-semibold">Past games</h2>
            <p className="text-sm text-slate-600 max-w-2xl">Imports finished matches with real kickoff times from openfootball, as historical (post-hoc) records the ML model can learn from. Matches already in the dataset are skipped, so running it again is safe. Roughly 1,700 matches per season for the five big leagues; allow a minute or two per season.</p>
          </div>
          <Button disabled={running || !hist || !hist.leagues.length || !!data.info?.error} onClick={() => start({ mode: "history", leagues: hist!.leagues, fromSeason: hist!.from, toSeason: hist!.to })}>
            {running && job?.mode === "history" ? "Importing…" : `Import ${histSeasons} season${histSeasons === 1 ? "" : "s"}`}
          </Button>
        </div>
        {hist ? (
          <div className="mt-4 grid md:grid-cols-[1fr_auto_auto] gap-5 items-start">
            <div>
              <div className="label mb-1">Leagues</div>
              <div className="grid sm:grid-cols-2 gap-x-4">
                {leagues.map((l) => (
                  <label key={l.code} className="font-sans text-sm flex gap-1.5 items-center py-0.5">
                    <input type="checkbox" checked={hist.leagues.includes(l.code)} onChange={() => setHist({ ...hist, leagues: toggle(hist.leagues, l.code) })} /> {l.name} <span className="text-xs text-slate-500">from {l.first}</span>
                  </label>
                ))}
              </div>
            </div>
            <Field label="From season"><Select className="w-32" value={hist.from} onChange={(e) => setHist({ ...hist, from: e.target.value, to: e.target.value > hist.to ? e.target.value : hist.to })}>{seasonsBetween("2010-11", lastComplete).map((x) => <option key={x}>{x}</option>)}</Select></Field>
            <Field label="To season"><Select className="w-32" value={hist.to} onChange={(e) => setHist({ ...hist, to: e.target.value })}>{seasonsBetween(hist.from, lastComplete).map((x) => <option key={x}>{x}</option>)}</Select></Field>
          </div>
        ) : null}
        <p className="font-sans text-xs text-slate-500 mt-3">The source has no bookmaker odds, so each match gets odds derived from an Elo rating; the notes say so. Then retrain on the <Link className="underline" href="/ml">ML Training</Link> page (done automatically if the box above is ticked).</p>
      </Card>

      {data.runs?.length ? (
        <Card>
          <div className="px-4 py-2.5 border-b border-rule font-sans font-semibold text-sm">Recent syncs</div>
          <table className="w-full text-sm">
            <thead><tr className="label text-left"><th className="px-4 py-1.5">Finished</th><th>Type</th><th>Source</th><th>Added</th><th>Results</th><th>Rescheduled</th><th>Awaiting time</th><th>Failed</th><th>Model</th></tr></thead>
            <tbody>
              {data.runs.map((r: Job) => (
                <tr key={r.id} className="border-t border-rule">
                  <td className="px-4 py-1.5 num text-xs">{r.finishedAt ? fmtDate(r.finishedAt) : "—"}</td>
                  <td>{r.mode === "history" ? `Past games ${r.seasons ?? ""}` : "Refresh"} {r.trigger === "auto" ? <Badge tone="teal">auto</Badge> : null} {r.state === "error" ? <Badge tone="red">error</Badge> : null}</td>
                  <td className="text-xs">{r.sources?.join(", ") || "—"}</td>
                  <td className="num">{r.created}</td><td className="num">{r.results}</td><td className="num">{r.rescheduled}</td>
                  <td className="num">{r.awaitingTime}</td><td className="num">{r.failed}</td>
                  <td className="text-xs">{r.retrained ? `v${r.retrained}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  );
}

function JobPanel({ job }: { job: Job }) {
  const pctDone = job.total ? Math.round((job.done / job.total) * 100) : job.state === "running" ? 0 : 100;
  return (
    <Card className="p-5" accent={job.state === "error" ? "#b91c1c" : job.state === "done" ? "#15803d" : "#0f766e"}>
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <h2 className="font-semibold">
          {job.mode === "history" ? "Importing past games" : "Refreshing upcoming games & results"}{" "}
          {job.state === "running" ? <Spinner label={job.step} /> : <Badge tone={job.state === "done" ? "green" : "red"}>{job.state === "done" ? "finished" : "failed"}</Badge>}
        </h2>
        <span className="font-sans text-xs text-slate-500">started {fmtDate(job.startedAt)}{job.sources.length ? ` · source: ${job.sources.join(", ")}` : ""}</span>
      </div>
      {job.total ? (
        <div className="mt-3">
          <div className="h-2.5 rounded bg-slate-200 overflow-hidden"><div className="h-full bg-teal-ml transition-all" style={{ width: `${pctDone}%` }} /></div>
          <div className="font-sans text-xs text-slate-600 mt-1">{job.done.toLocaleString()} of {job.total.toLocaleString()} ({pctDone}%)</div>
        </div>
      ) : null}
      <div className="font-sans text-sm mt-3 flex flex-wrap gap-x-5 gap-y-1">
        <span>Added <strong>{job.created}</strong></span>
        <span>Results recorded <strong>{job.results}</strong></span>
        <span>Rescheduled <strong>{job.rescheduled}</strong></span>
        <span>Postponed <strong>{job.postponed}</strong></span>
        <span>Already in dataset <strong>{job.skipped + job.linked}</strong></span>
        {job.awaitingTime ? <span>Waiting for a kickoff time <strong>{job.awaitingTime}</strong></span> : null}
        {job.failed ? <span className="text-red-700">Failed <strong>{job.failed}</strong></span> : null}
        {job.retrained ? <span>Model retrained → <strong>v{job.retrained}</strong></span> : null}
      </div>
      {job.awaitingTime ? <p className="font-sans text-xs text-slate-500 mt-1">Fixtures without a published kickoff time are added on a later refresh, once the time is known (the chart is cast for the kickoff minute).</p> : null}
      {job.error ? <div className="mt-3"><Alert tone="red">{job.error}</Alert></div> : null}
      {job.warnings.length ? <div className="mt-3"><Alert tone="amber"><ul className="list-disc pl-5">{job.warnings.map((w) => <li key={w}>{w}</li>)}</ul></Alert></div> : null}
      {job.failures.length ? <details className="mt-2 font-sans text-xs"><summary className="cursor-pointer text-red-700">Show failures</summary><ul className="list-disc pl-5 mt-1">{job.failures.map((f, i) => <li key={i}>{f}</li>)}</ul></details> : null}
    </Card>
  );
}
