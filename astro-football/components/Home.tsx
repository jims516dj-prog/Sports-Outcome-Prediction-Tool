"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Spinner, pct } from "@/components/ui";
import { ENGINE_META, api, fmtDate } from "@/lib/client";

const LEAGUE_NAMES: Record<string, string> = {
  "en.1": "Premier League", "de.1": "Bundesliga", "es.1": "La Liga", "it.1": "Serie A", "fr.1": "Ligue 1",
  "en.2": "Championship", "nl.1": "Eredivisie", "pt.1": "Primeira Liga",
};

export function Home() {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api("/api/stats").then(setS).catch((e) => setErr(e.message)); }, []);
  const total = s ? Object.values<number>(s.byStatus).reduce((a, b) => a + b, 0) : 0;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap justify-between items-end gap-3">
        <div>
          <h1 className="text-3xl font-semibold">Astrological Football Match Analyzer</h1>
          <p className="text-slate-600 mt-1 max-w-3xl">Three classical methods, one chart moment: Rao&apos;s Inclusive Methodology, Chokoisky&apos;s Gambler&apos;s Dharma and Frawley&apos;s event chart — reconciled into a comparative outlook, and tested against a growing historical dataset.</p>
        </div>
        <div className="flex gap-2"><Link href="/analyze"><Button>Analyze a match</Button></Link><Link href="/dataset/new"><Button variant="teal">Add historical match</Button></Link></div>
      </div>
      {err ? <Alert tone="red">{err}</Alert> : null}
      {s && s.service && !s.service.ok ? <Alert tone="red">Astrology service offline: {s.service.error}</Alert> : null}
      {!s ? <Spinner label="Loading…" /> : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Card className="p-4"><div className="label">Matches</div><div className="text-2xl font-semibold num">{total.toLocaleString()}</div><div className="font-sans text-xs text-slate-500">{Object.entries(s.byStatus).map(([k, v]) => `${k} ${v}`).join(" · ") || "none yet"}</div></Card>
            <Card className="p-4"><div className="label">ML model</div><div className="text-2xl font-semibold num">{s.model ? `v${s.model.versionNumber}` : "cold start"}</div><div className="font-sans text-xs text-slate-500">{s.model ? `consensus ${pct(s.model.overallAccuracy, 1)} · favourite ${pct(s.model.engineAccuracies?.favourite_baseline, 1)} · ${s.model.combinationCount} combinations` : "equal engine weights"}</div></Card>
            <Card className="p-4"><div className="label">Reference data</div><div className="text-2xl font-semibold num">{s.teams} / {s.venues}</div><div className="font-sans text-xs text-slate-500">teams / venues</div></Card>
            <Card className="p-4"><div className="label">Astrology service</div><div className="text-2xl font-semibold">{s.service?.ok ? "online" : "offline"}</div><div className="font-sans text-xs text-slate-500">Swiss Ephemeris {s.service?.swisseph ?? ""}</div></Card>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            {Object.entries(ENGINE_META).map(([k, m]) => (
              <Card key={k} accent={m.color} className="p-4">
                <div className="font-semibold" style={{ color: m.color }}>{m.title}</div>
                <div className="text-sm italic text-slate-600">{m.book}</div>
                <div className="text-xs font-sans text-slate-500 mt-1">{m.author}</div>
              </Card>
            ))}
          </div>
          <Card>
            <div className="px-4 py-2.5 border-b border-rule font-sans font-semibold text-sm flex justify-between">Upcoming matches <Link href="/sync" className="underline font-normal">Data sync →</Link></div>
            <table className="w-full text-sm">
              <tbody>
                {s.upcoming.map((u: any) => {
                  const pick = u.synthesis?.winner === "A" ? u.teamA.displayName : u.synthesis?.winner === "B" ? u.teamB.displayName : u.synthesis?.winner === "draw" ? "Draw" : "—";
                  return (
                    <tr key={u.id} className="border-b border-rule">
                      <td className="px-4 py-1.5 num text-xs whitespace-nowrap">{fmtDate(u.kickoffGMT)} GMT</td>
                      <td><Link className="hover:underline" href={`/dataset/${u.id}`}>{u.teamA.displayName} vs {u.teamB.displayName}</Link></td>
                      <td className="text-xs text-slate-500">{LEAGUE_NAMES[u.league] ?? ""}</td>
                      <td className="text-xs">astrology consensus: <strong>{pick}</strong>{u.synthesis?.confidence != null ? ` (${u.synthesis.confidence}%)` : ""}</td>
                    </tr>
                  );
                })}
                {s.upcoming.length === 0 ? <tr><td className="p-4 text-slate-500">No upcoming matches yet — open <Link className="underline" href="/sync">Data sync</Link> and click Refresh now.</td></tr> : null}
              </tbody>
            </table>
          </Card>
          <Card>
            <div className="px-4 py-2.5 border-b border-rule font-sans font-semibold text-sm flex justify-between">Recently added <Link href="/dataset" className="underline font-normal">all matches →</Link></div>
            <table className="w-full text-sm">
              <tbody>
                {s.recent.map((r: any) => (
                  <tr key={r.id} className="border-b border-rule">
                    <td className="px-4 py-1.5 num text-xs">{fmtDate(r.kickoffGMT)}</td>
                    <td><Link className="hover:underline" href={`/dataset/${r.id}`}>{r.teamA.displayName} vs {r.teamB.displayName}</Link></td>
                    <td className="num">{r.scoreA == null ? <Badge tone="amber">pending</Badge> : `${r.scoreA}–${r.scoreB}`}</td>
                    <td className="text-xs">{r.synthesis?.headline}</td>
                    <td className="num text-xs">{r.synthesis?.confidence != null ? `${r.synthesis.confidence}%` : ""}</td>
                  </tr>
                ))}
                {s.recent.length === 0 ? <tr><td className="p-4 text-slate-500">No matches yet — analyze one, or import history (see README).</td></tr> : null}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
