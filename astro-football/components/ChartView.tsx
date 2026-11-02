"use client";
// Detailed chart view (spec 9.7) - uses the snapshots stored at analysis time.
import Link from "next/link";
import { useEffect, useState } from "react";
import { ChartWheel, wheelFromChart } from "@/components/ChartWheel";
import { Alert, Button, Card, Spinner } from "@/components/ui";
import { PLANET_GLYPH, PLANET_NAME, SIGNS, api, byPlanet, fmtDate } from "@/lib/client";

const VARIANTS = {
  frawley: { label: "Tropical · Placidus (Frawley)", key: "chartD1Frawley", color: "#1f6f3a", whole: false },
  chokoisky: { label: "Sidereal Lahiri · Placidus (Chokoisky)", key: "chartD1Chokoisky", color: "#4338ca", whole: false },
  rao: { label: "Sidereal Lahiri · whole sign (Rao)", key: "chartD1Rao", color: "#d97706", whole: true },
} as const;

export function ChartView({ id }: { id: string }) {
  const [m, setM] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [variant, setVariant] = useState<keyof typeof VARIANTS>("frawley");
  useEffect(() => { api(`/api/matches/${id}`).then((r) => setM(r.match)).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <Alert tone="red">{err}</Alert>;
  if (!m) return <Spinner label="Loading…" />;
  const V = VARIANTS[variant];
  const ch = m[V.key];
  if (!ch) return <Alert tone="amber">No chart snapshot stored — re-run the analysis.</Alert>;
  const fr = m.chartD1Frawley, ck = m.chartD1Chokoisky, d9 = m.chartD9Chokoisky, rao = m.chartD1Rao;
  const comb: Record<string, any> = Object.fromEntries((fr?.combustions ?? []).map((c: any) => [c.planet, c]));
  const d9planets = Object.fromEntries(Object.entries<any>(d9?.planets ?? {}).map(([k, p]) => [k, { lon: p.lon }]));

  return (
    <div>
      <div className="font-sans text-sm text-slate-600 mb-3">
        <Link href={`/dataset/${id}`} className="underline">← {m.teamA.displayName} vs {m.teamB.displayName}</Link> · {fmtDate(m.kickoffGMT)} GMT · {m.venue.name} ({m.venue.lat.toFixed(3)}, {m.venue.long.toFixed(3)})
        <span className="ml-2 text-xs">Snapshot from analysis time — not recomputed on view.</span>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {(Object.keys(VARIANTS) as (keyof typeof VARIANTS)[]).map((k) => (
          <Button key={k} variant={variant === k ? "primary" : "secondary"} onClick={() => setVariant(k)}>{VARIANTS[k].label}</Button>
        ))}
      </div>
      <div className="grid lg:grid-cols-2 gap-5">
        <Card className="p-4 flex flex-col items-center">
          <ChartWheel {...wheelFromChart(ch)} wholeSign={V.whole} size={440} color={V.color} title={`D1 — ${V.label} — Asc ${ch.ascendant}`} />
          <p className="font-sans text-xs text-slate-500 mt-1">Hover a glyph for its exact position; red glyphs are retrograde.</p>
        </Card>
        <Card className="p-4 flex flex-col items-center">
          <ChartWheel ascendant={d9?.ascendant_deg ?? 0} planets={d9planets} wholeSign size={360} color="#4338ca" title={`D9 Navamsha — Asc ${d9?.ascendant ?? "—"} · 7th ${d9?.descendant ?? "—"}`} />
          <table className="w-full text-xs mt-3">
            <thead><tr className="label text-left"><th>Planet</th><th>D9 position</th><th>to D9 Asc</th><th>to D9 7th</th></tr></thead>
            <tbody>
              {byPlanet<any>(d9?.planets).map(([k, p]) => (
                <tr key={k} className={`border-t border-rule ${p.distance_to_asc <= 2.5 || p.distance_to_desc <= 2.5 ? "bg-indigo-soft font-semibold" : ""}`}>
                  <td>{PLANET_GLYPH[k]} {PLANET_NAME[k]}</td><td className="num">{p.pos}</td><td className="num">{p.distance_to_asc}°</td><td className="num">{p.distance_to_desc}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-5 mt-5">
        <Card className="p-4">
          <h3 className="font-sans font-semibold mb-2">House cusps — Placidus and whole sign</h3>
          <table className="w-full text-sm">
            <thead><tr className="label text-left"><th>House</th><th>Placidus (tropical)</th><th>Placidus (sidereal)</th><th>Whole sign (tropical)</th><th>Whole sign (sidereal)</th></tr></thead>
            <tbody>
              {Array.from({ length: 12 }, (_, i) => (
                <tr key={i} className="border-t border-rule">
                  <td className="num">{i + 1}</td>
                  <td className="num text-xs">{fr?.cusps_placidus?.[i]?.pos}</td>
                  <td className="num text-xs">{ck?.cusps_placidus?.[i]?.pos}</td>
                  <td className="text-xs">{fr?.cusps_wholesign?.[i]}</td>
                  <td className="text-xs">{rao?.houses?.[i]?.sign}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card className="p-4">
          <h3 className="font-sans font-semibold mb-2">KP sublords (Krishnamurti ayanamsha {ck?.ayanamsha_kp?.toFixed?.(3)}°)</h3>
          <table className="w-full text-sm">
            <thead><tr className="label text-left"><th>Cusp</th><th>KP longitude</th><th>Star lord</th><th>Sub lord</th></tr></thead>
            <tbody>
              {(ck?.sublords ?? []).map((s: any) => (
                <tr key={s.house} className={`border-t border-rule ${s.house === 1 || s.house === 7 ? "font-semibold" : ""}`}>
                  <td className="num">{s.house}</td><td className="num text-xs">{(s.kp_lon % 30).toFixed(2)}° {SIGNS[Math.floor(s.kp_lon / 30)]}</td>
                  <td>{PLANET_NAME[s.star_lord]}</td><td>{PLANET_NAME[s.sub_lord]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card className="p-4 mt-5 overflow-x-auto">
        <h3 className="font-sans font-semibold mb-2">Planet positions</h3>
        <table className="w-full text-sm">
          <thead><tr className="label text-left"><th>Planet</th><th>Tropical</th><th>Sidereal (Lahiri)</th><th>Nakshatra</th><th>Placidus house</th><th>Speed °/day</th><th>Dignity (sid.)</th><th>Combustion</th><th>Antiscion (trop.)</th></tr></thead>
          <tbody>
            {byPlanet<any>(fr?.planets).map(([k, p]) => {
              const s = ck?.planets?.[k];
              const c = comb[k];
              return (
                <tr key={k} className="border-t border-rule">
                  <td>{PLANET_GLYPH[k]} {PLANET_NAME[k]}{p.retrograde ? <span className="text-red-700 text-xs"> Rx</span> : null}</td>
                  <td className="num text-xs">{p.pos}</td><td className="num text-xs">{s?.pos}</td><td className="text-xs">{s?.nakshatra}</td>
                  <td className="num">{p.house}</td><td className="num text-xs">{p.speed}</td><td className="text-xs">{s?.dignity}</td>
                  <td className="text-xs">{c ? (c.cazimi ? "cazimi" : `${c.distance}° from Sun${c.distance <= 2 ? " (destructive)" : ""}`) : ""}</td>
                  <td className="num text-xs">{fr?.antiscia?.[k]?.pos}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="font-sans text-xs text-slate-600 mt-3 grid md:grid-cols-3 gap-2">
          <div>Part of Fortune: <span className="num">{fr?.part_of_fortune?.pos}</span> · antiscion <span className="num">{fr?.antiscia?.Fortuna?.pos}</span></div>
          <div>Part of Resignation: <span className="num">{fr?.part_of_resignation?.pos}</span></div>
          <div>Moon nakshatra {fr?.nakshatra_of_moon} · tithi {fr?.tithi} · {fr?.day_of_week} (day lord {PLANET_NAME[fr?.day_lord]})</div>
          {fr?.planetary_wars?.length ? <div>Planetary wars: {fr.planetary_wars.map((w: any) => `${PLANET_NAME[w[0]]}–${PLANET_NAME[w[1]]} (${w[2]}°)`).join(", ")}</div> : null}
        </div>
      </Card>
    </div>
  );
}
