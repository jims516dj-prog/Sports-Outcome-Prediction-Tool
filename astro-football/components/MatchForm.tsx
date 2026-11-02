"use client";
// Match-setup form (spec section 3 / 9.1). Used for new matches, historical matches and edits.
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Badge, Button, Field, Input, Modal, Section, Select, Spinner } from "@/components/ui";
import { JERSEY_COLORS, api } from "@/lib/client";

type Mode = "new" | "historical" | "edit";
type Founding = { date: string; time: string; place: string; lat: string; long: string; tz: string };
const emptyFounding: Founding = { date: "", time: "", place: "", lat: "", long: "", tz: "" };

export type FormState = {
  teamA: string; teamB: string; teamAType: string; teamBType: string; date: string; timeGMT: string;
  timeEntry: "gmt" | "local"; timeLocal: string; gmtDate: string;
  venueName: string; lat: string; long: string; coordSource: string; pageId: number | null; canonicalName: string; venueTz: string;
  sport: string; context: string; oddsA: string; oddsB: string; oddsDraw: string;
  foundingA: Founding; foundingB: Founding;
  hasCaptainData: boolean; captainAJersey: string; captainBJersey: string; teamAJerseyColor: string; teamBJerseyColor: string;
  playedAlready: boolean; scoreA: string; scoreB: string; status: string; notes: string;
};

export const blankForm = (): FormState => ({
  teamA: "", teamB: "", teamAType: "club", teamBType: "club", date: "", timeGMT: "", timeEntry: "gmt", timeLocal: "", gmtDate: "",
  venueName: "", lat: "", long: "", coordSource: "", pageId: null, canonicalName: "", venueTz: "",
  sport: "football", context: "league", oddsA: "", oddsB: "", oddsDraw: "",
  foundingA: { ...emptyFounding }, foundingB: { ...emptyFounding },
  hasCaptainData: false, captainAJersey: "", captainBJersey: "", teamAJerseyColor: "", teamBJerseyColor: "",
  playedAlready: false, scoreA: "", scoreB: "", status: "completed", notes: "",
});

const SPORTS: [string, string, string[]][] = [
  ["football", "Football / Soccer", ["league", "friendly"]],
  ["american_football", "American Football", []],
  ["cricket", "Cricket", ["league"]],
  ["tennis", "Tennis", []],
  ["basketball", "Basketball", []],
  ["ice_hockey", "Ice Hockey", []],
];
const num = (s: string) => (s === "" || s == null ? null : Number(s));
/** GMT date of the kick-off: differs from the local date when local time was entered near midnight. */
const gmtDateOf = (f: FormState) => (f.timeEntry === "local" && f.gmtDate ? f.gmtDate : f.date);

function foundingFromTeam(t: any): Founding {
  return {
    date: t?.foundingDate ? String(t.foundingDate).slice(0, 10) : "", time: t?.foundingTime ?? "", place: t?.foundingPlace ?? "",
    lat: t?.foundingLat?.toString() ?? "", long: t?.foundingLong?.toString() ?? "", tz: t?.foundingTz ?? "",
  };
}

export function toPayload(f: FormState) {
  const f2 = (x: Founding) => (x.date ? { date: x.date, time: x.time || null, place: x.place || null, lat: num(x.lat), long: num(x.long), tz: x.tz || null } : null);
  return {
    sport: f.sport, context: f.context, teamA: f.teamA.trim(), teamB: f.teamB.trim(), teamAType: f.teamAType, teamBType: f.teamBType,
    kickoffGMT: `${gmtDateOf(f)}T${f.timeGMT}`,
    venue: { name: f.venueName.trim(), lat: Number(f.lat), long: Number(f.long), source: f.coordSource || "manual", pageId: f.pageId, canonicalName: f.canonicalName || null, timezone: f.venueTz || null },
    oddsA: Number(f.oddsA), oddsB: Number(f.oddsB), oddsDraw: num(f.oddsDraw),
    foundingA: f2(f.foundingA), foundingB: f2(f.foundingB),
    hasCaptainData: f.hasCaptainData,
    captainAJersey: f.hasCaptainData ? num(f.captainAJersey) : null, captainBJersey: f.hasCaptainData ? num(f.captainBJersey) : null,
    teamAJerseyColor: f.hasCaptainData ? f.teamAJerseyColor || null : null, teamBJerseyColor: f.hasCaptainData ? f.teamBJerseyColor || null : null,
    scoreA: num(f.scoreA), scoreB: num(f.scoreB), status: f.status, notes: f.notes || null,
  };
}

export function formFromMatch(m: any): FormState {
  const ko = new Date(m.kickoffGMT).toISOString();
  return {
    ...blankForm(),
    teamA: m.teamA.name, teamB: m.teamB.name, teamAType: m.teamA.nationOrClub, teamBType: m.teamB.nationOrClub,
    date: ko.slice(0, 10), timeGMT: ko.slice(11, 16),
    venueName: m.venue.name, lat: String(m.venue.lat), long: String(m.venue.long), coordSource: m.venue.coordinateSource,
    pageId: m.venue.wikipediaPageId, canonicalName: m.venue.canonicalName ?? "", venueTz: m.venue.timezone ?? "",
    sport: m.sport, context: m.context, oddsA: String(m.oddsA), oddsB: String(m.oddsB), oddsDraw: m.oddsDraw?.toString() ?? "",
    foundingA: foundingFromTeam(m.teamA), foundingB: foundingFromTeam(m.teamB),
    hasCaptainData: m.hasCaptainData, captainAJersey: m.captainAJersey?.toString() ?? "", captainBJersey: m.captainBJersey?.toString() ?? "",
    teamAJerseyColor: m.teamAJerseyColor ?? "", teamBJerseyColor: m.teamBJerseyColor ?? "",
    playedAlready: m.scoreA != null, scoreA: m.scoreA?.toString() ?? "", scoreB: m.scoreB?.toString() ?? "", status: m.status, notes: m.notes ?? "",
  };
}

function TeamInput({ value, onChange, onPick, placeholder }: { value: string; onChange: (v: string) => void; onPick: (t: any) => void; placeholder: string }) {
  const [opts, setOpts] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const applied = useRef<string | null>(null);
  useEffect(() => {
    if (value.length < 2) return setOpts([]);
    const t = setTimeout(async () => {
      try {
        const list = await api(`/api/teams?q=${encodeURIComponent(value)}`);
        setOpts(list);
        // typing a known team's exact name applies its stored data (founding chart, home venue)
        const exact = list.find((x: any) => x.name.toLowerCase() === value.trim().toLowerCase());
        if (exact && applied.current !== exact.id) {
          applied.current = exact.id;
          onPick(exact);
        }
      } catch {
        setOpts([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="relative">
      <Input value={value} placeholder={placeholder} onChange={(e) => { onChange(e.target.value); setOpen(true); }} onBlur={() => setTimeout(() => setOpen(false), 150)} required />
      {open && opts.length > 0 && !(opts.length === 1 && opts[0].name === value) ? (
        <ul className="absolute z-20 left-0 right-0 bg-white border border-slate-300 rounded-md shadow mt-1 max-h-56 overflow-auto font-sans text-sm">
          {opts.map((t) => (
            <li key={t.id}>
              <button type="button" className="w-full text-left px-2.5 py-1.5 hover:bg-slate-100" onMouseDown={() => { applied.current = t.id; onPick(t); setOpen(false); }}>
                {t.displayName} <span className="text-xs text-slate-500">{t.nationOrClub}{t.foundingDate ? ` · founded ${String(t.foundingDate).slice(0, 10)}` : ""}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function FoundingFields({ label, value, onChange, known }: { label: string; value: Founding; onChange: (f: Founding) => void; known: boolean }) {
  const set = (k: keyof Founding) => (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: e.target.value });
  return (
    <div>
      <div className="font-sans text-sm font-semibold mb-2">{label} {known ? <Badge tone="teal">from database</Badge> : null}</div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Founding date"><Input type="date" value={value.date} onChange={set("date")} min="0800-01-01" /></Field>
        <Field label="Time (local)" hint="optional — enables the Ascendant"><Input type="time" value={value.time} onChange={set("time")} /></Field>
        <Field label="Place" className="col-span-2"><Input value={value.place} onChange={set("place")} placeholder="e.g. Westminster, London" /></Field>
        <Field label="Latitude"><Input value={value.lat} onChange={set("lat")} inputMode="decimal" /></Field>
        <Field label="Longitude"><Input value={value.long} onChange={set("long")} inputMode="decimal" /></Field>
        <Field label="Timezone (IANA)" hint="blank = from coordinates" className="col-span-2"><Input value={value.tz} onChange={set("tz")} placeholder="Europe/London" /></Field>
      </div>
    </div>
  );
}

export function MatchForm({ mode, initial, matchId }: { mode: Mode; initial?: FormState; matchId?: string }) {
  const router = useRouter();
  const [f, setF] = useState<FormState>(initial ?? { ...blankForm(), playedAlready: mode === "historical" });
  const [known, setKnown] = useState<{ A: boolean; B: boolean }>({ A: false, B: false });
  const [lookup, setLookup] = useState<{ busy: boolean; msg?: string }>({ busy: false });
  const [local, setLocal] = useState<any>(null);
  const [sandhi, setSandhi] = useState<string[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rerunAsk, setRerunAsk] = useState(false);
  const historical = mode === "historical" || f.playedAlready;
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setF((s) => ({ ...s, [k]: v }));

  const drawContexts = SPORTS.find((s) => s[0] === f.sport)?.[2] ?? [];
  const drawPossible = drawContexts.includes(f.context);
  const oA = Number(f.oddsA), oB = Number(f.oddsB);
  const oddsOk = oA > 1 && oB > 1;
  const equalOdds = oddsOk && Math.abs(oA - oB) <= 0.05;
  const favourite = !oddsOk ? null : equalOdds ? null : oA <= oB ? f.teamA || "Team A" : f.teamB || "Team B";
  const coordsOk = f.lat !== "" && f.long !== "" && Number.isFinite(Number(f.lat)) && Number.isFinite(Number(f.long));

  // live GMT <-> local preview at the venue (spec 3.6.1)
  useEffect(() => {
    if (!coordsOk || !f.date) return setLocal(null);
    const t = setTimeout(async () => {
      try {
        if (f.timeEntry === "local" && f.timeLocal) {
          const r = await api(`/api/tz?lat=${f.lat}&long=${f.long}&local=${f.date}T${f.timeLocal}`);
          setF((s) => ({ ...s, timeGMT: r.gmt.slice(11, 16), gmtDate: r.gmt.slice(0, 10) }));
          setLocal({ local: `${f.date}T${f.timeLocal}`, timezone: r.timezone, utc_offset: r.utc_offset, gmt: r.gmt });
        } else if (f.timeGMT) {
          setLocal(await api(`/api/tz?lat=${f.lat}&long=${f.long}&gmt=${f.date}T${f.timeGMT}`));
        }
      } catch {
        setLocal(null);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [f.lat, f.long, f.date, f.timeGMT, f.timeLocal, f.timeEntry, coordsOk]);

  // non-blocking sandhi preview (spec 10.2)
  useEffect(() => {
    if (!coordsOk || !f.date || !f.timeGMT) return setSandhi(null);
    const t = setTimeout(async () => {
      try {
        const r = await api("/api/rao", {
          method: "POST",
          body: JSON.stringify({ team_a: f.teamA || "A", team_b: f.teamB || "B", kickoff_gmt: `${gmtDateOf(f)}T${f.timeGMT}`, lat: Number(f.lat), long: Number(f.long), odds_a: oA > 1 ? oA : 2, odds_b: oB > 1 ? oB : 3 }),
        });
        setSandhi(r.sandhi?.warnings ?? []);
      } catch {
        setSandhi(null);
      }
    }, 600);
    return () => clearTimeout(t);
  }, [f.date, f.gmtDate, f.timeGMT, f.lat, f.long, coordsOk]); // eslint-disable-line react-hooks/exhaustive-deps

  const pickTeam = (side: "A" | "B") => (t: any) => {
    setF((s) => ({ ...s, [`team${side}`]: t.name, [`team${side}Type`]: t.nationOrClub, [`founding${side}`]: foundingFromTeam(t) }) as FormState);
    setKnown((k) => ({ ...k, [side]: !!t.foundingDate }));
    if (side === "A" && t.defaultVenue && !f.venueName) {
      set("venueName", t.defaultVenue);
      doLookup(t.defaultVenue);
    }
  };

  async function doLookup(name = f.venueName, force = false) {
    if (!name.trim()) return;
    setLookup({ busy: true });
    try {
      const r = await api(`/api/stadium-lookup?name=${encodeURIComponent(name.trim())}${force ? "&force=1" : ""}`);
      if (r.lat == null) {
        setLookup({ busy: false, msg: r.message ?? "Lookup unavailable — please enter coordinates manually" });
        set("coordSource", "manual");
        return;
      }
      setF((s) => ({ ...s, lat: String(r.lat), long: String(r.long), coordSource: r.source, pageId: r.pageId ?? null, canonicalName: r.canonicalName ?? "", venueTz: r.timezone ?? "" }));
      setLookup({ busy: false, msg: r.cached ? `Saved venue (${r.source}${r.lastVerifiedAt ? `, verified ${String(r.lastVerifiedAt).slice(0, 10)}` : ""})` : undefined });
    } catch (e: any) {
      setLookup({ busy: false, msg: `${e.message} — enter coordinates manually` });
    }
  }

  async function saveVenue() {
    try {
      await api("/api/venues", { method: "POST", body: JSON.stringify({ name: f.venueName, lat: f.lat, long: f.long, coordinateSource: f.coordSource || "manual", canonicalName: f.canonicalName, timezone: f.venueTz }) });
      setLookup({ busy: false, msg: "Venue saved to the database" });
    } catch (e: any) {
      setLookup({ busy: false, msg: e.message });
    }
  }

  function validate(asHistorical: boolean) {
    if (!f.teamA || !f.teamB) return "Both teams are required";
    if (!f.date || !f.timeGMT) return "Match date and kick-off time are required";
    if (!coordsOk) return "Venue coordinates are required (lookup or manual entry)";
    if (!oddsOk) return "Decimal odds for both teams are required";
    if (asHistorical && f.status === "completed" && (f.scoreA === "" || f.scoreB === "")) return "Enter the final scoreline for a historical match";
    return null;
  }

  async function submit(asHistorical: boolean, rerun?: "yes" | "no") {
    const v = validate(asHistorical);
    if (v) return setError(v);
    setError(null);
    setBusy(asHistorical ? "Analysing as historical…" : "Analysing…");
    try {
      if (mode === "edit") {
        const r = await api(`/api/matches/${matchId}`, { method: "PATCH", body: JSON.stringify({ input: toPayload(f), rerun }) });
        router.push(`/dataset/${r.id}?tab=analysis&saved=${r.rerun ? "rerun" : r.stale ? "stale" : "1"}`);
        router.refresh();
      } else {
        const r = await api("/api/matches", { method: "POST", body: JSON.stringify({ input: toPayload(f), historical: asHistorical }) });
        router.push(`/dataset/${r.id}`);
      }
    } catch (e: any) {
      setError(e.message);
      setBusy(null);
    }
  }

  const initialRef = useRef(initial);
  const inputsChanged = useMemo(() => {
    if (mode !== "edit" || !initialRef.current) return false;
    const a = toPayload(initialRef.current) as any, b = toPayload(f) as any;
    const keys = ["sport", "context", "teamA", "teamB", "kickoffGMT", "oddsA", "oddsB", "oddsDraw", "hasCaptainData", "captainAJersey", "captainBJersey", "teamAJerseyColor", "teamBJerseyColor"];
    return keys.some((k) => a[k] !== b[k]) || a.venue.lat !== b.venue.lat || a.venue.long !== b.venue.long || a.venue.name !== b.venue.name
      || JSON.stringify(a.foundingA) !== JSON.stringify(b.foundingA) || JSON.stringify(a.foundingB) !== JSON.stringify(b.foundingB);
  }, [f, mode]);

  const tag = f.coordSource === "wikipedia" ? "From Wikipedia" : f.coordSource === "openstreetmap" ? "From OpenStreetMap" : f.coordSource === "seed" ? "From seeded venue table" : f.coordSource === "manual" ? "Manual override" : null;

  return (
    <form onSubmit={(e) => e.preventDefault()} className="max-w-5xl">
      <Section title="1 · Core match inputs (required)">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="grid grid-cols-[1fr_110px] gap-2">
            <Field label="Team A"><TeamInput value={f.teamA} onChange={(v) => { set("teamA", v); setKnown((k) => ({ ...k, A: false })); }} onPick={pickTeam("A")} placeholder="e.g. Arsenal" /></Field>
            <Field label="Type"><Select value={f.teamAType} onChange={(e) => set("teamAType", e.target.value)}><option value="club">club</option><option value="nation">nation</option><option value="franchise">franchise</option></Select></Field>
          </div>
          <div className="grid grid-cols-[1fr_110px] gap-2">
            <Field label="Team B"><TeamInput value={f.teamB} onChange={(v) => { set("teamB", v); setKnown((k) => ({ ...k, B: false })); }} onPick={pickTeam("B")} placeholder="e.g. Chelsea" /></Field>
            <Field label="Type"><Select value={f.teamBType} onChange={(e) => set("teamBType", e.target.value)}><option value="club">club</option><option value="nation">nation</option><option value="franchise">franchise</option></Select></Field>
          </div>
          <Field label="Match date"><Input type="date" value={f.date} onChange={(e) => set("date", e.target.value)} required /></Field>
          <div>
            <div className="flex gap-3 mb-1">
              <label className="font-sans text-xs flex items-center gap-1"><input type="radio" checked={f.timeEntry === "gmt"} onChange={() => set("timeEntry", "gmt")} /> GMT</label>
              {historical ? <label className="font-sans text-xs flex items-center gap-1"><input type="radio" checked={f.timeEntry === "local"} onChange={() => set("timeEntry", "local")} /> enter local time instead</label> : null}
            </div>
            {f.timeEntry === "gmt" ? (
              <Field label="Kick-off time (GMT, 24h)"><Input type="time" value={f.timeGMT} onChange={(e) => set("timeGMT", e.target.value)} required /></Field>
            ) : (
              <Field label="Kick-off time (local at venue)"><Input type="time" value={f.timeLocal} onChange={(e) => set("timeLocal", e.target.value)} /></Field>
            )}
            <div className="font-sans text-xs text-slate-600 mt-1 min-h-4">
              {local ? <>→ {f.timeEntry === "gmt" ? <>local <strong>{local.local?.replace("T", " ")}</strong></> : <>GMT <strong>{local.gmt?.replace("T", " ")}</strong></>} · {local.timezone} (UTC{local.utc_offset}){local.dst ? " · DST" : ""}</> : coordsOk ? null : "Local time appears once the venue has coordinates"}
            </div>
          </div>
        </div>
        <div className="mt-4 border-t border-rule pt-4">
          <div className="grid md:grid-cols-[1fr_auto_auto] gap-2 items-end">
            <Field label="Venue name"><Input value={f.venueName} onChange={(e) => set("venueName", e.target.value)} onBlur={() => !f.lat && doLookup()} placeholder="e.g. Emirates Stadium" required /></Field>
            <Button type="button" variant="secondary" onClick={() => doLookup(f.venueName, true)} disabled={lookup.busy}>{lookup.busy ? "Looking up…" : "Lookup"}</Button>
            <Button type="button" variant="secondary" onClick={saveVenue} disabled={!coordsOk || !f.venueName}>Save venue to DB</Button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-[1fr_1fr_2fr] gap-2 mt-2 items-end">
            <Field label="Latitude"><Input value={f.lat} onChange={(e) => setF((s) => ({ ...s, lat: e.target.value, coordSource: "manual" }))} inputMode="decimal" placeholder="51.5550" /></Field>
            <Field label="Longitude"><Input value={f.long} onChange={(e) => setF((s) => ({ ...s, long: e.target.value, coordSource: "manual" }))} inputMode="decimal" placeholder="-0.1083" /></Field>
            <div className="font-sans text-xs pb-2 flex flex-wrap gap-2 items-center">
              {tag ? <Badge tone={f.coordSource === "manual" ? "amber" : "teal"}>{tag}</Badge> : null}
              {f.canonicalName ? <span className="text-slate-500">{f.canonicalName}</span> : null}
              {lookup.msg ? <span className="text-slate-600">{lookup.msg}</span> : null}
            </div>
          </div>
        </div>
      </Section>

      <Section title="2 · Context & odds (required)">
        <div className="grid md:grid-cols-5 gap-3">
          <Field label="Sport"><Select value={f.sport} onChange={(e) => set("sport", e.target.value)}>{SPORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</Select></Field>
          <Field label="Match context"><Select value={f.context} onChange={(e) => set("context", e.target.value)}><option value="league">League</option><option value="knockout">Knockout</option><option value="final">Final</option><option value="friendly">Friendly</option></Select></Field>
          <Field label={`Odds — ${f.teamA || "Team A"}`}><Input value={f.oddsA} onChange={(e) => set("oddsA", e.target.value)} inputMode="decimal" placeholder="1.85" required /></Field>
          <Field label={`Odds — ${f.teamB || "Team B"}`}><Input value={f.oddsB} onChange={(e) => set("oddsB", e.target.value)} inputMode="decimal" placeholder="4.20" required /></Field>
          {drawPossible ? <Field label="Odds — Draw" hint="optional"><Input value={f.oddsDraw} onChange={(e) => set("oddsDraw", e.target.value)} inputMode="decimal" placeholder="3.40" /></Field> : <div className="font-sans text-xs text-slate-500 self-end pb-2">No draw possible in this context</div>}
        </div>
        <div className="mt-3 font-sans text-sm flex flex-wrap gap-2 items-center">
          {favourite ? <>Favourite (Native / Lagna): <Badge tone="indigo">{favourite}</Badge></> : null}
          {equalOdds ? <Alert tone="amber">No clear favourite (odds within ±0.05): Frawley&apos;s event-chart method requires a clear favourite and will be disabled. Rao and Chokoisky still run, with Team A as Native.</Alert> : null}
        </div>
      </Section>

      <Section title="3 · Founding charts (Rao's Nations' Charts)" defaultOpen={!known.A || !known.B}>
        {!f.foundingA.date || !f.foundingB.date ? (
          <div className="mb-3"><Alert tone="amber">Missing founding chart for {[!f.foundingA.date && (f.teamA || "Team A"), !f.foundingB.date && (f.teamB || "Team B")].filter(Boolean).join(" and ")} — Rao&apos;s Nations&apos; Charts phase will be skipped for that side (Game Analysis and Planetary Influence still run).</Alert></div>
        ) : null}
        <div className="grid md:grid-cols-2 gap-6">
          <FoundingFields label={f.teamA || "Team A"} value={f.foundingA} onChange={(v) => set("foundingA", v)} known={known.A} />
          <FoundingFields label={f.teamB || "Team B"} value={f.foundingB} onChange={(v) => set("foundingB", v)} known={known.B} />
        </div>
        <p className="font-sans text-xs text-slate-500 mt-2">Values entered here are saved to the team record (editable in Settings).</p>
      </Section>

      <Section title="4 · Captains & jerseys (optional)" defaultOpen={f.hasCaptainData}>
        <label className="font-sans text-sm flex items-center gap-2">
          <input type="checkbox" checked={f.hasCaptainData} onChange={(e) => set("hasCaptainData", e.target.checked)} />
          Include captains &amp; jersey configuration
        </label>
        <p className="font-sans text-xs text-slate-500 mt-1">Usually unavailable until minutes before kickoff. Optional in Rao&apos;s methodology — without it Rao runs without the planetary-influence layer.</p>
        {f.hasCaptainData ? (
          <div className="grid md:grid-cols-4 gap-3 mt-3">
            <Field label={`Captain jersey — ${f.teamA || "A"}`}><Input type="number" min={1} max={99} value={f.captainAJersey} onChange={(e) => set("captainAJersey", e.target.value)} /></Field>
            <Field label={`Captain jersey — ${f.teamB || "B"}`}><Input type="number" min={1} max={99} value={f.captainBJersey} onChange={(e) => set("captainBJersey", e.target.value)} /></Field>
            <Field label={`Jersey colour — ${f.teamA || "A"}`}><Select value={f.teamAJerseyColor} onChange={(e) => set("teamAJerseyColor", e.target.value)}><option value="">—</option>{JERSEY_COLORS.map((c) => <option key={c}>{c}</option>)}</Select></Field>
            <Field label={`Jersey colour — ${f.teamB || "B"}`}><Select value={f.teamBJerseyColor} onChange={(e) => set("teamBJerseyColor", e.target.value)}><option value="">—</option>{JERSEY_COLORS.map((c) => <option key={c}>{c}</option>)}</Select></Field>
          </div>
        ) : null}
      </Section>

      {mode === "new" ? (
        <label className="font-sans text-sm flex items-center gap-2 mb-3">
          <input type="checkbox" checked={f.playedAlready} onChange={(e) => set("playedAlready", e.target.checked)} /> This match has already been played (add scoreline)
        </label>
      ) : null}
      {historical || mode === "edit" ? (
        <Section title={mode === "edit" ? "5 · Result" : "5 · Scoreline (historical match)"} tone={mode === "historical" ? "#0f766e" : undefined}>
          <div className="grid md:grid-cols-4 gap-3">
            <Field label={`Final score — ${f.teamA || "A"}`}><Input type="number" min={0} value={f.scoreA} onChange={(e) => set("scoreA", e.target.value)} /></Field>
            <Field label={`Final score — ${f.teamB || "B"}`}><Input type="number" min={0} value={f.scoreB} onChange={(e) => set("scoreB", e.target.value)} /></Field>
            <Field label="Match status"><Select value={f.status} onChange={(e) => set("status", e.target.value)}>
              {mode === "edit" ? <option value="pending">Pending</option> : null}
              <option value="completed">Completed</option><option value="walkover">Walkover</option><option value="abandoned">Abandoned</option><option value="no_result">No result</option><option value="dl_method">D/L method applied</option>
            </Select></Field>
            <Field label="Notes"><Input value={f.notes} onChange={(e) => set("notes", e.target.value)} placeholder="Red card 65' Team B" /></Field>
          </div>
          {mode !== "edit" ? <p className="font-sans text-xs text-slate-500 mt-2">The engines still run so you can see what they would have predicted; the record is tagged post-hoc (weighted 0.5 in ML training by default).</p> : null}
        </Section>
      ) : null}

      {sandhi && sandhi.length ? (
        <div className="mb-3"><Alert tone="amber"><strong>Sandhi warnings (non-blocking):</strong> {sandhi.join(" · ")}</Alert></div>
      ) : null}
      {error ? <div className="mb-3"><Alert tone="red">{error}</Alert></div> : null}

      <div className="flex flex-wrap gap-3 items-center">
        {mode === "edit" ? (
          <Button type="button" disabled={!!busy} onClick={() => (inputsChanged ? setRerunAsk(true) : submit(false))}>Save changes</Button>
        ) : (
          <>
            {mode === "new" ? <Button type="button" disabled={!!busy || f.playedAlready} onClick={() => submit(false)}>Analyze &amp; save as pending</Button> : null}
            <Button type="button" variant="teal" disabled={!!busy || (mode === "new" && !f.playedAlready)} onClick={() => submit(true)}>Analyze as historical (with scoreline)</Button>
          </>
        )}
        {busy ? <Spinner label={busy} /> : null}
      </div>

      <Modal open={rerunAsk} onClose={() => setRerunAsk(false)} title="Input changes require re-analysis">
        <p className="text-sm">You changed fields that affect the charts. Re-run the engines now? The current verdicts are kept as an earlier version.</p>
        <div className="flex gap-2 mt-4">
          <Button onClick={() => { setRerunAsk(false); submit(false, "yes"); }}>Yes, re-run</Button>
          <Button variant="secondary" onClick={() => { setRerunAsk(false); submit(false, "no"); }}>Save without re-run</Button>
          <Button variant="ghost" onClick={() => setRerunAsk(false)}>Cancel</Button>
        </div>
      </Modal>
    </form>
  );
}
