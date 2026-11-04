"use client";
// Results dashboard (spec 9.2): sticky overall outlook + three engine cards.
import Link from "next/link";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ChartWheel, wheelFromChart } from "@/components/ChartWheel";
import { GoalsCard } from "@/components/GoalsCard";
import { Alert, Badge, Button, Card, pct } from "@/components/ui";
import { ENGINE_META, api, fmtDate } from "@/lib/client";

type Side = "A" | "B" | "draw" | "disabled";

const METHOD_NOTE = {
  rao: "Paraphrase (not a quotation): the favourite is read from the Lagna and the rival from the 7th. Six parameters per side — Ascendant, Ascendant lord, Score, Game with Coach & Captain, Fans & Odds, Penalties — are scored 0–3 in strict order, then the nations' (or clubs') founding charts are transposed onto the match chart, and finally the captains' jersey numbers, the day and the jersey colours are weighed. The higher total wins.",
  chokoisky: "Paraphrase (not a quotation): a multi-tier points system read from the favourite's Lagna (+) against the underdog's 7th (−). Tier 1: victory houses and navamsha combinations; tier 2: SKY/PKY, D1 cuspal strength, KP sublords, nakshatra taras; tier 3 (most powerful): planets on the D9 cusps and the nama pada syllable. The signed total gives the winner, and |total| / 3 the goal difference.",
  frawley: "Paraphrase (not a quotation): a tropical, Placidus chart for the kick-off. The favourite is Lord 1 with Lord 10, the underdog Lord 7 with Lord 4. Testimonies are weighed in priority order: significators on or just inside cusps (and their antiscia), the Moon's placement, the antiscion of Fortuna, the Moon's last applying aspect within range, aspects to Fortuna, its dispositor and miscellaneous factors. With no testimony the favourite wins.",
};

export function AnalysisView({ match, combos, onReanalyzed }: { match: any; combos: any[]; onReanalyzed?: () => void }) {
  const syn = match.synthesis ?? {};
  const inp = syn.input ?? {};
  const A = match.teamA.displayName as string;
  const B = match.teamB.displayName as string;
  const nm = (s: Side | undefined) => (s === "A" ? A : s === "B" ? B : s === "draw" ? "Draw" : "—");
  const favName = inp.fav_side === "B" ? B : A;
  const rao = match.verdictRao, chok = match.verdictChokoisky, fraw = match.verdictFrawley;
  const v: Record<string, Side> = syn.verdicts ?? {};
  const ml = syn.ml ?? {};
  const actual: Side | null = match.scoreA == null || match.scoreB == null ? null : match.scoreA > match.scoreB ? "A" : match.scoreA < match.scoreB ? "B" : "draw";

  const raoKey = rao
    ? Object.entries<number>(rao.fav)
        .map(([k, x]) => [k, x - (rao.und[k] ?? 0)] as const)
        .filter(([, d]) => Math.abs(d) >= 1.5)
        .map(([k, d]) => `${k.replace(/_/g, " ")} ${d > 0 ? "favours" : "against"} ${favName}`)
        .slice(0, 3)
        .join("; ")
    : "";
  const rows = [
    {
      key: "rao", label: ENGINE_META.rao.title, winner: v.rao,
      score: rao ? `${rao.goal_diff_range[0]}–${rao.goal_diff_range[1]} goal margin (${Math.abs(rao.diff) >= 8 ? "decisive" : Math.abs(rao.diff) <= 3 ? "close" : "moderate"})` : "—",
      conf: rao?.confidence, tests: raoKey || `point difference ${rao?.diff ?? "—"}`,
      cav: (rao?.caveats ?? []).filter((c: string) => !c.startsWith("Debilitated")).join("; "),
    },
    {
      key: "chokoisky", label: ENGINE_META.chokoisky.title, winner: v.chokoisky,
      score: chok ? `${chok.verdict === "draw" ? "level" : `+${chok.goal_diff} goals`} (total ${chok.total > 0 ? "+" : ""}${chok.total})` : "—",
      conf: chok?.confidence, tests: (chok?.decisive ?? []).slice(0, 2).join("; ") || "no tier-3 testimony", cav: "",
    },
    {
      key: "frawley", label: ENGINE_META.frawley.title, winner: fraw ? v.frawley : ("disabled" as Side),
      score: fraw ? (fraw.verdict === "draw" ? "level" : `${fraw.goals.winner}–${fraw.goals.loser}`) : "—",
      conf: fraw?.confidence,
      tests: fraw ? fraw.testimonies.filter((t: any) => t.strength !== "weak").slice(0, 2).map((t: any) => t.text).join("; ") || (fraw.default_rule ? "no testimony — default rule (favourite)" : "weak testimonies only") : "",
      cav: fraw ? "" : syn.frawley_notice ?? "",
    },
  ];
  const confidence = ml.finalConfidence ?? syn.base_confidence;

  return (
    <div className="space-y-5">
      {/* ---------- Overall outlook (sticky) ---------- */}
      <Card className="lg:sticky lg:top-0 z-10">
        <div className="px-5 py-4 border-b border-rule flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="label">{match.sport} · {match.context} · {match.venue.name}</div>
            <h1 className="text-2xl font-semibold mt-0.5">
              {A} <span className="text-slate-400 font-normal">vs</span> {B}
              {actual ? <span className="num text-lg ml-3 text-slate-600">{match.scoreA}–{match.scoreB}</span> : null}
            </h1>
            <div className="font-sans text-xs text-slate-600 mt-1">
              Kick-off {fmtDate(match.kickoffGMT)} GMT · local {match.kickoffLocal?.replace("T", " ")} ({match.timezone}) ·
              favourite <strong>{inp.clear_favourite === false ? "none (equal odds)" : favName}</strong> · odds {match.oddsA} / {match.oddsDraw ?? "–"} / {match.oddsB}
            </div>
          </div>
          <div className="text-right">
            <div className="label">Consensus</div>
            <div className="text-xl font-semibold">{nm(syn.winner)}</div>
            <div className="font-sans text-sm">
              confidence <span className="num font-semibold">{confidence ?? "—"}%</span>
              {ml.multiplier && ml.multiplier !== 1 ? <span className="text-teal-ml"> (base {syn.base_confidence}% × ML {ml.multiplier.toFixed(2)})</span> : null}
            </div>
            {actual ? (
              <Badge tone={syn.winner === actual ? "green" : "red"}>{syn.winner === actual ? "prediction correct" : `actual: ${nm(actual)}`}</Badge>
            ) : <Badge tone="amber">pending result</Badge>}
          </div>
        </div>
        <div className="px-5 py-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left label">
                <th className="py-1.5 pr-3">Methodology</th><th className="pr-3">Predicted winner</th><th className="pr-3">Score / goal diff</th>
                <th className="pr-3">Confidence</th><th className="pr-3">Key testimonies</th><th>Caveats</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-t border-rule align-top">
                  <td className="py-2 pr-3 font-sans font-medium whitespace-nowrap" style={{ color: (ENGINE_META as any)[r.key].color }}>{r.label}</td>
                  <td className="pr-3 py-2 font-semibold">{nm(r.winner)}</td>
                  <td className="pr-3 py-2 num text-xs">{r.score}</td>
                  <td className="pr-3 py-2 capitalize">{r.conf ?? "—"}</td>
                  <td className="pr-3 py-2 text-xs">{r.tests}</td>
                  <td className="py-2 text-xs text-slate-600">{r.cav || "None"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-5 pb-4 grid md:grid-cols-3 gap-4">
          <div>
            <div className="label">Synthesis</div>
            <p className="font-semibold">{syn.headline}</p>
            {(syn.disagreement_analysis ?? []).map((t: string) => <p key={t} className="text-sm text-slate-700 mt-1">{t}</p>)}
          </div>
          <div>
            <div className="label">Combined goal range</div>
            <p>Most likely: <span className="num font-semibold">{syn.goal_range?.likely}</span>. Plausible range: <span className="num">{syn.goal_range?.plausible}</span>.</p>
            <div className="label mt-2">Other observations</div>
            <ul className="text-sm list-disc pl-5">{(syn.observations ?? []).map((o: string) => <li key={o}>{o}</li>)}</ul>
          </div>
          <div className="space-y-2">
            {ml.banner ? (
              <div className="rounded-md border border-teal-300 bg-teal-soft p-3 text-sm font-sans">
                <div className="font-semibold text-teal-ml">📊 {ml.banner}</div>
                {(ml.insights ?? []).map((i: any) => (
                  <div key={i.id} className="mt-1.5 text-[13px] text-teal-950">
                    {i.text}
                    <div className="text-[11.5px] text-teal-800">
                      picking the favourite in these matches: {pct(i.favouriteBaseline)} · on newer matches it never saw: {i.holdoutAccuracy == null ? "not validated" : `${pct(i.holdoutAccuracy)} (n=${i.holdoutSize})`}
                    </div>
                  </div>
                ))}
                <div className="text-[11px] text-teal-800 mt-1.5">Model v{ml.modelVersion ?? "—"} · engine weights {Object.entries(ml.engineWeights ?? {}).map(([k, w]: any) => `${k} ${Number(w).toFixed(2)}`).join(", ")}</div>
              </div>
            ) : null}
            <CautionsBox match={match} syn={syn} />
          </div>
        </div>
      </Card>

      <GoalsCard match={match} />

      {/* ---------- Engine cards ---------- */}
      <RaoCard rao={rao} match={match} nm={nm} winner={v.rao} onReanalyzed={onReanalyzed} />
      <ChokoiskyCard chok={chok} match={match} nm={nm} winner={v.chokoisky} onReanalyzed={onReanalyzed} />
      <FrawleyCard fraw={fraw} notice={syn.frawley_notice} match={match} nm={nm} winner={v.frawley} onReanalyzed={onReanalyzed} />
      <VersionsCard match={match} nm={nm} />
    </div>
  );
}

function CautionsBox({ match, syn }: { match: any; syn: any }) {
  const items: string[] = [...(syn.warnings ?? [])];
  if (match.postHocAnalysis)
    items.unshift("Post-hoc analysis: the user already knew the result when this analysis was generated. The verdict may be biased by the user's choice of inputs. Use with caution in ML training — flagged post_hoc=true.");
  if (match.staleAnalysis) items.unshift("Inputs changed since this analysis was run — the verdicts are stale. Re-run the analysis.");
  for (const c of match.verdictRao?.caveats ?? []) if (c.startsWith("Saturn")) items.push("Rao's methodology cautions that this configuration indicates potential match interruption (weather, crowd, technical). If an interruption occurs and the D/L method (or equivalent) is invoked, this prediction must be set aside per Rao's explicit exception.");
  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-[13px] font-sans text-amber-950">
      <div className="font-semibold">Cautions</div>
      <p className="mt-1">Research only — not betting advice. Rao: the method &ldquo;will not work for persons involved in betting.&rdquo;</p>
      <ul className="list-disc pl-5 mt-1 space-y-0.5">{items.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  );
}

function EngineShell({ k, winner, nm, children, chart, match, onReanalyzed }: any) {
  const meta = (ENGINE_META as any)[k];
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  return (
    <Card accent={meta.color}>
      <div className="px-5 py-3 border-b border-rule flex flex-wrap justify-between items-start gap-3" style={{ background: meta.soft }}>
        <div>
          <h2 className="font-semibold text-lg" style={{ color: meta.color }}>{meta.title}</h2>
          <div className="text-sm italic text-slate-700">{meta.book} — {meta.author}</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="label">Verdict</div>
            <div className="font-semibold">{nm(winner)}</div>
          </div>
          <Button
            variant="secondary"
            disabled={busy}
            title="The analysis is already stored in the dataset; this saves a fresh snapshot as a new version"
            onClick={async () => {
              setBusy(true);
              try {
                await api(`/api/matches/${match.id}/reanalyze`, { method: "POST" });
                setSaved("Snapshot saved");
                onReanalyzed?.();
              } catch (e: any) {
                setSaved(e.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Saving…" : saved ?? "✓ Saved · save new snapshot"}
          </Button>
        </div>
      </div>
      <div className="p-5 grid lg:grid-cols-[minmax(0,1fr)_320px] gap-6">
        <div className="min-w-0">{children}</div>
        <div className="flex flex-col items-center gap-3">
          {chart}
          <Link href={`/dataset/${match.id}/chart`} className="font-sans text-xs underline text-slate-600">Detailed chart view →</Link>
        </div>
      </div>
      <div className="px-5 pb-4 text-[13px] text-slate-600 border-t border-rule pt-3">
        <span className="label">Method note</span> {METHOD_NOTE[k as keyof typeof METHOD_NOTE]}
      </div>
    </Card>
  );
}

function RaoCard({ rao, match, nm, winner, onReanalyzed }: any) {
  if (!rao) return <Alert tone="slate">Rao engine disabled in Settings.</Alert>;
  const labels: Record<string, string> = {
    ascendant: "Ascendant", asc_lord: "Ascendant lord", score: "Score", game_coach: "Game + Coach & Captain",
    fans_odds: "Fans & Odds", penalties: "Penalties", nation_moon: "Nation/club Moon", nation_asc: "Nation/club Ascendant",
    planetary_influence: "Planetary influence",
  };
  const inp = match.synthesis?.input ?? {};
  const fav = inp.fav_side === "B" ? match.teamB.displayName : match.teamA.displayName;
  const und = inp.fav_side === "B" ? match.teamA.displayName : match.teamB.displayName;
  const w = wheelFromChart(match.chartD1Rao);
  return (
    <EngineShell k="rao" winner={winner} nm={nm} match={match} onReanalyzed={onReanalyzed}
      chart={<ChartWheel {...w} wholeSign title={`D1 · sidereal (Lahiri) · whole sign · Lagna ${rao.lagna}`} color="#d97706" />}>
      <table className="w-full text-sm mb-4">
        <thead><tr className="label text-left"><th className="py-1">Parameter</th><th>{fav} (Native)</th><th>{und} (Rival)</th></tr></thead>
        <tbody>
          {Object.entries(labels).map(([k, l]) => {
            const a = rao.fav[k], b = rao.und[k];
            const skipped = a === undefined && b === undefined;
            return (
              <tr key={k} className="border-t border-rule">
                <td className="py-1.5">{l}</td>
                <td className="num">{skipped ? <span className="text-slate-400 font-sans text-xs">skipped</span> : a ?? "—"}</td>
                <td className="num">{skipped ? "" : b ?? "—"}</td>
              </tr>
            );
          })}
          <tr className="border-t-2 border-slate-400 font-semibold">
            <td className="py-1.5">Total</td><td className="num">{rao.total_fav}</td><td className="num">{rao.total_und}</td>
          </tr>
        </tbody>
      </table>
      <div className="prose-analysis text-[14px]"><ReactMarkdown>{rao.markdown}</ReactMarkdown></div>
      {rao.caveats?.length ? (
        <ul className="mt-3 text-[13px] font-sans text-amber-900 list-disc pl-5">{rao.caveats.map((c: string) => <li key={c}>{c}</li>)}</ul>
      ) : null}
    </EngineShell>
  );
}

function ChokoiskyCard({ chok, match, nm, winner, onReanalyzed }: any) {
  if (!chok) return <Alert tone="slate">Chokoisky engine disabled in Settings.</Alert>;
  const names: Record<string, [string, string]> = {
    victory_houses: ["Victory houses", "Tier 1"], sky_pky: ["SKY / PKY", "Tier 2"], d1_cusps: ["Cuspal strength (D1)", "Tier 2"],
    d9_cusps: ["Navamsha cuspal strength (D9)", "Tier 3"], nama_pada: ["Nama pada", "Tier 3"], sublords: ["Sublords (KP)", "Tier 2"],
    nakshatra_tara: ["Nakshatra taras", "Tier 2"], planetary_war: ["Planetary war", "—"],
  };
  const d1 = wheelFromChart(match.chartD1Chokoisky);
  const d9c = match.chartD9Chokoisky;
  const d9planets: Record<string, any> = {};
  for (const [k, p] of Object.entries<any>(d9c?.planets ?? {})) d9planets[k] = { lon: p.lon };
  return (
    <EngineShell k="chokoisky" winner={winner} nm={nm} match={match} onReanalyzed={onReanalyzed}
      chart={<>
        <ChartWheel {...d1} size={280} title="D1 · sidereal · Placidus" color="#4338ca" />
        <ChartWheel ascendant={d9c?.ascendant_deg ?? 0} planets={d9planets} wholeSign size={240} title="D9 Navamsha" color="#4338ca" />
      </>}>
      <table className="w-full text-sm">
        <thead><tr className="label text-left"><th className="py-1">Technique</th><th>Tier</th><th className="text-right pr-3">Points</th><th>Detail</th></tr></thead>
        <tbody>
          {Object.keys(names).filter((k) => chok.rows[k]).map((k) => [k, chok.rows[k]] as const).map(([k, r]) => (
            <tr key={k} className="border-t border-rule align-top">
              <td className="py-1.5 pr-2">{names[k]?.[0] ?? k}</td>
              <td className="text-xs text-slate-500 pr-2">{names[k]?.[1]}</td>
              <td className={`num text-right pr-3 ${r.points > 0 ? "text-green-700" : r.points < 0 ? "text-red-700" : ""}`}>{r.points > 0 ? "+" : ""}{r.points}</td>
              <td className="text-xs text-slate-700">{r.detail || "—"}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-400 font-semibold">
            <td className="py-1.5">Cumulative total</td><td /><td className="num text-right pr-3">{chok.total > 0 ? "+" : ""}{chok.total}</td>
            <td className="text-xs font-normal">positive → favourite; |total| ≤ 3 → draw; goal diff ≈ |total| / 3 = {chok.goal_diff}</td>
          </tr>
        </tbody>
      </table>
      <div className="mt-3 text-sm space-y-1">
        <div>Confidence: <Badge tone={chok.confidence === "high" ? "green" : chok.confidence === "medium" ? "amber" : "slate"}>{chok.confidence}</Badge></div>
        {chok.decisive?.length ? <div>Decisive testimonies: {chok.decisive.join(" · ")}</div> : null}
        <div className="text-xs text-slate-600">MC navamsha syllable: <strong>{chok.mc_syllable}</strong> · sublord difference {chok.sublord_diff}</div>
      </div>
    </EngineShell>
  );
}

function FrawleyCard({ fraw, notice, match, nm, winner, onReanalyzed }: any) {
  const w = wheelFromChart(match.chartD1Frawley);
  if (!fraw)
    return (
      <Card accent={ENGINE_META.frawley.color}>
        <div className="p-5">
          <h2 className="font-semibold text-lg" style={{ color: ENGINE_META.frawley.color }}>{ENGINE_META.frawley.title}</h2>
          <Alert tone="amber">{notice ?? "Frawley engine disabled in Settings."}</Alert>
        </div>
      </Card>
    );
  return (
    <EngineShell k="frawley" winner={winner} nm={nm} match={match} onReanalyzed={onReanalyzed}
      chart={<ChartWheel {...w} title={`Event chart · tropical · Placidus · L1 ${fraw.lords.L1} · L7 ${fraw.lords.L7}`} color="#1f6f3a" />}>
      <div className="text-sm mb-2 font-sans">Significators — favourite: Lord 1 <strong>{fraw.lords.L1}</strong>, Lord 10 <strong>{fraw.lords.L10}</strong>; underdog: Lord 7 <strong>{fraw.lords.L7}</strong>, Lord 4 <strong>{fraw.lords.L4}</strong></div>
      {fraw.testimonies.length ? (
        <table className="w-full text-sm">
          <thead><tr className="label text-left"><th className="py-1">Testimony</th><th>For</th><th>Strength</th></tr></thead>
          <tbody>
            {fraw.testimonies.map((t: any, i: number) => (
              <tr key={i} className="border-t border-rule">
                <td className="py-1.5 pr-2">{t.text}</td>
                <td className="pr-2 whitespace-nowrap">{t.team === "fav" ? "favourite" : "underdog"}</td>
                <td><Badge tone={t.strength === "strong" ? "green" : t.strength === "medium" ? "amber" : "slate"}>{t.strength}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <Alert tone="slate">No testimony at all — default rule: the favourite wins.</Alert>}
      <div className="mt-3 text-sm space-y-1">
        <div>Net score <span className="num">{fraw.score > 0 ? "+" : ""}{fraw.score}</span> → <strong>{nm(winner)}</strong>{fraw.verdict !== "draw" ? <> · predicted <span className="num">{fraw.goals.winner}–{fraw.goals.loser}</span></> : " · testimonies balanced (draw)"}</div>
        {fraw.late_goal ? <div className="text-forest">⏱ Late-winning-goal indicator: the Moon&apos;s final aspect completes late in its range.</div> : null}
      </div>
    </EngineShell>
  );
}

function VersionsCard({ match, nm }: any) {
  const versions: any[] = Array.isArray(match.analysisVersions) ? match.analysisVersions : [];
  if (versions.length < 2) return null;
  return (
    <Card>
      <div className="px-5 py-3 border-b border-rule font-sans font-semibold text-sm">Analysis versions ({versions.length}) — earlier verdicts are preserved</div>
      <table className="w-full text-sm m-0">
        <thead><tr className="label text-left"><th className="px-5 py-1.5">When</th><th>Reason</th><th>Captain data</th><th>Rao</th><th>Chokoisky</th><th>Frawley</th><th>Consensus</th></tr></thead>
        <tbody>
          {versions.map((x, i) => (
            <tr key={i} className="border-t border-rule">
              <td className="px-5 py-1.5 num text-xs">{fmtDate(x.timestamp)}</td>
              <td>{x.reason}</td>
              <td>{x.hasCaptainData ? "yes" : "no"}</td>
              <td>{nm(x.synthesis?.verdicts?.rao)}</td>
              <td>{nm(x.synthesis?.verdicts?.chokoisky)}</td>
              <td>{nm(x.synthesis?.verdicts?.frawley ?? "disabled")}</td>
              <td className="font-semibold">{nm(x.synthesis?.winner)} <span className="num text-xs font-normal">({x.synthesis?.ml?.finalConfidence ?? x.synthesis?.base_confidence}%)</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

