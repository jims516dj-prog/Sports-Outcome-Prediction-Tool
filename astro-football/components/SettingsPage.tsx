"use client";
// Settings (spec 9.6): reference data, engine/technique toggles, ML configuration.
import { useCallback, useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Select, Spinner } from "@/components/ui";
import { PLANET_NAME, api, fmtDate } from "@/lib/client";

const TABS = ["Teams & founding charts", "Venues", "Wikipedia names", "Engines & techniques", "ML configuration", "Sport presets & ayanamsha", "Reference tables", "Admin"] as const;
type Tab = (typeof TABS)[number];

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>(TABS[0]);
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Settings</h1>
      <div className="flex flex-wrap gap-1 mb-4">
        {TABS.map((t) => <Button key={t} variant={tab === t ? "primary" : "secondary"} onClick={() => setTab(t)}>{t}</Button>)}
      </div>
      {tab === "Teams & founding charts" ? <Teams /> : null}
      {tab === "Venues" ? <Venues /> : null}
      {tab === "Wikipedia names" ? <Aliases /> : null}
      {tab === "Engines & techniques" ? <Toggles /> : null}
      {tab === "ML configuration" ? <MlConfig /> : null}
      {tab === "Sport presets & ayanamsha" ? <Presets /> : null}
      {tab === "Reference tables" ? <Reference /> : null}
      {tab === "Admin" ? <Admin /> : null}
    </div>
  );
}

const emptyTeam = { name: "", displayName: "", nationOrClub: "club", foundingDate: "", foundingTime: "", foundingPlace: "", foundingLat: "", foundingLong: "", foundingTz: "", defaultVenue: "", notes: "" };

function Teams() {
  const [teams, setTeams] = useState<any[] | null>(null);
  const [edit, setEdit] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [natal, setNatal] = useState<any>(null);
  const load = useCallback(() => api("/api/teams").then(setTeams).catch((e) => setMsg(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const list = (teams ?? []).filter((t) => t.name.toLowerCase().includes(q.toLowerCase()));
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setEdit({ ...edit, [k]: e.target.value });

  async function save() {
    try {
      if (edit.id) await api(`/api/teams/${edit.id}`, { method: "PATCH", body: JSON.stringify(edit) });
      else await api("/api/teams", { method: "POST", body: JSON.stringify(edit) });
      setEdit(null); setMsg("Saved"); load();
    } catch (e: any) { setMsg(e.message); }
  }
  async function preview() {
    try {
      setNatal(await api("/api/natal", { method: "POST", body: JSON.stringify({ date: edit.foundingDate, time: edit.foundingTime || null, lat: edit.foundingLat === "" ? null : Number(edit.foundingLat), long: edit.foundingLong === "" ? null : Number(edit.foundingLong), tz: edit.foundingTz || null }) }));
    } catch (e: any) { setNatal({ error: e.message }); }
  }

  return (
    <div className="grid lg:grid-cols-[1fr_380px] gap-4">
      <Card className="p-3">
        <div className="flex gap-2 mb-2"><Input placeholder="filter teams" value={q} onChange={(e) => setQ(e.target.value)} /><Button onClick={() => { setEdit({ ...emptyTeam }); setNatal(null); }}>Add team</Button></div>
        {!teams ? <Spinner /> : (
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white"><tr className="label text-left"><th>Name</th><th>Type</th><th>Founded</th><th>Time</th><th>Place</th><th /></tr></thead>
              <tbody>
                {list.map((t) => (
                  <tr key={t.id} className="border-t border-rule">
                    <td className="py-1">{t.displayName}</td><td className="text-xs">{t.nationOrClub}</td>
                    <td className="num text-xs">{t.foundingDate ? String(t.foundingDate).slice(0, 10) : <span className="text-amber-700 font-sans">missing</span>}</td>
                    <td className="num text-xs">{t.foundingTime ?? ""}</td><td className="text-xs">{t.foundingPlace ?? ""}</td>
                    <td><button className="underline font-sans text-xs" onClick={() => { setEdit({ ...emptyTeam, ...t, foundingDate: t.foundingDate ? String(t.foundingDate).slice(0, 10) : "", foundingLat: t.foundingLat ?? "", foundingLong: t.foundingLong ?? "" }); setNatal(null); }}>edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Card className="p-4">
        {msg ? <div className="mb-2"><Alert tone="slate">{msg}</Alert></div> : null}
        {edit ? (
          <div className="space-y-2">
            <h3 className="font-sans font-semibold">{edit.id ? "Edit team" : "New team"}</h3>
            <Field label="Name (unique key)"><Input value={edit.name} onChange={set("name")} disabled={!!edit.id} /></Field>
            <Field label="Display name"><Input value={edit.displayName} onChange={set("displayName")} /></Field>
            <Field label="Type"><Select value={edit.nationOrClub} onChange={set("nationOrClub")}><option value="club">club</option><option value="nation">nation</option><option value="franchise">franchise</option></Select></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Founding date"><Input type="date" value={edit.foundingDate} onChange={set("foundingDate")} /></Field>
              <Field label="Time (local)"><Input type="time" value={edit.foundingTime ?? ""} onChange={set("foundingTime")} /></Field>
              <Field label="Latitude"><Input value={edit.foundingLat} onChange={set("foundingLat")} /></Field>
              <Field label="Longitude"><Input value={edit.foundingLong} onChange={set("foundingLong")} /></Field>
            </div>
            <Field label="Place"><Input value={edit.foundingPlace ?? ""} onChange={set("foundingPlace")} /></Field>
            <Field label="Timezone (IANA)" hint="blank = derived from coordinates"><Input value={edit.foundingTz ?? ""} onChange={set("foundingTz")} /></Field>
            <Field label="Default venue"><Input value={edit.defaultVenue ?? ""} onChange={set("defaultVenue")} /></Field>
            <Field label="Notes / source"><Input value={edit.notes ?? ""} onChange={set("notes")} /></Field>
            <div className="flex gap-2"><Button onClick={save}>Save</Button><Button variant="secondary" disabled={!edit.foundingDate} onClick={preview}>Preview natal Moon / Asc</Button><Button variant="ghost" onClick={() => setEdit(null)}>Cancel</Button></div>
            {natal ? <p className="font-sans text-xs">{natal.error ?? `Sidereal Moon: ${natal.moon_sign_name}${natal.asc_sign_name ? ` · Ascendant: ${natal.asc_sign_name}` : " · Ascendant needs a founding time and place"}`}</p> : null}
          </div>
        ) : <p className="text-sm text-slate-600">Select a team to edit its founding chart. Rao&apos;s Nations&apos; Charts phase uses the sidereal Moon sign (date) and the Ascendant (date + time + place).</p>}
      </Card>
    </div>
  );
}

function Venues() {
  const [venues, setVenues] = useState<any[] | null>(null);
  const [edit, setEdit] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api("/api/venues").then(setVenues).catch((e) => setMsg(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const list = (venues ?? []).filter((v) => v.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-4">
      <Card className="p-3">
        <div className="flex gap-2 mb-2">
          <Input placeholder="filter venues" value={q} onChange={(e) => setQ(e.target.value)} />
          <Button onClick={() => setEdit({ name: "", lat: "", long: "", timezone: "", coordinateSource: "manual" })}>Add venue</Button>
          <Button variant="secondary" disabled={busy} onClick={async () => {
            setBusy(true);
            try { const r = await api("/api/venues/reverify", { method: "POST" }); setMsg(`Re-verified ${r.updated} of ${r.checked} venues from Wikipedia${r.failed.length ? `; ${r.failed.length} could not be verified (manual overrides are never touched)` : ""}`); load(); }
            catch (e: any) { setMsg(e.message); } finally { setBusy(false); }
          }}>{busy ? "Re-verifying…" : "Re-verify all from Wikipedia"}</Button>
        </div>
        {msg ? <div className="mb-2"><Alert tone="slate">{msg}</Alert></div> : null}
        {!venues ? <Spinner /> : (
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white"><tr className="label text-left"><th>Venue</th><th>Lat</th><th>Long</th><th>Timezone</th><th>Source</th><th>Verified</th><th /></tr></thead>
              <tbody>
                {list.map((v) => (
                  <tr key={v.id} className="border-t border-rule">
                    <td className="py-1">{v.name}</td><td className="num text-xs">{v.lat.toFixed(4)}</td><td className="num text-xs">{v.long.toFixed(4)}</td>
                    <td className="text-xs">{v.timezone}</td><td><Badge tone={v.coordinateSource === "manual" ? "amber" : "teal"}>{v.coordinateSource}</Badge></td>
                    <td className="num text-xs">{v.lastVerifiedAt ? fmtDate(v.lastVerifiedAt).slice(0, 10) : ""}</td>
                    <td><button className="underline font-sans text-xs" onClick={() => setEdit({ ...v })}>edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Card className="p-4">
        {edit ? (
          <div className="space-y-2">
            <h3 className="font-sans font-semibold">{edit.id ? "Edit venue" : "New venue"}</h3>
            <Field label="Name"><Input value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Latitude"><Input value={edit.lat} onChange={(e) => setEdit({ ...edit, lat: e.target.value, coordinateSource: "manual" })} /></Field>
              <Field label="Longitude"><Input value={edit.long} onChange={(e) => setEdit({ ...edit, long: e.target.value, coordinateSource: "manual" })} /></Field>
            </div>
            <Field label="Timezone (IANA)"><Input value={edit.timezone ?? ""} onChange={(e) => setEdit({ ...edit, timezone: e.target.value })} /></Field>
            <p className="font-sans text-xs text-slate-500">Editing coordinates marks the venue as a manual override.</p>
            <div className="flex gap-2">
              <Button onClick={async () => {
                try { await api(edit.id ? `/api/venues/${edit.id}` : "/api/venues", { method: edit.id ? "PATCH" : "POST", body: JSON.stringify(edit) }); setEdit(null); load(); }
                catch (e: any) { setMsg(e.message); }
              }}>Save</Button>
              {edit.id ? <Button variant="danger" onClick={async () => { try { await api(`/api/venues/${edit.id}`, { method: "DELETE" }); setEdit(null); load(); } catch (e: any) { setMsg(e.message); } }}>Delete</Button> : null}
              <Button variant="ghost" onClick={() => setEdit(null)}>Cancel</Button>
            </div>
          </div>
        ) : <p className="text-sm text-slate-600">Venues are cached on first use with their coordinate source (Wikipedia / OpenStreetMap / manual / seed) and verification date.</p>}
      </Card>
    </div>
  );
}

function Aliases() {
  const [rows, setRows] = useState<any[]>([]);
  const [v, setV] = useState({ venueName: "", wikiTitle: "" });
  const load = useCallback(() => api("/api/aliases").then(setRows), []);
  useEffect(() => { load(); }, [load]);
  return (
    <Card className="p-4 max-w-3xl">
      <p className="text-sm mb-3">The first Wikipedia lookup uses this table to map a venue name to its article title; otherwise the lookup searches Wikipedia and skips disambiguation pages.</p>
      <div className="flex gap-2 mb-3 items-end">
        <Field label="Venue name"><Input value={v.venueName} onChange={(e) => setV({ ...v, venueName: e.target.value })} placeholder="Old Trafford" /></Field>
        <Field label="Wikipedia article"><Input value={v.wikiTitle} onChange={(e) => setV({ ...v, wikiTitle: e.target.value })} placeholder="Old Trafford (football)" /></Field>
        <Button onClick={async () => { await api("/api/aliases", { method: "POST", body: JSON.stringify(v) }); setV({ venueName: "", wikiTitle: "" }); load(); }}>Add</Button>
      </div>
      <table className="w-full text-sm">
        <thead><tr className="label text-left"><th>Venue name</th><th>Wikipedia article</th><th /></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id} className="border-t border-rule"><td className="py-1">{r.venueName}</td><td>{r.wikiTitle}</td><td><button className="underline text-xs font-sans" onClick={async () => { await api(`/api/aliases?id=${r.id}`, { method: "DELETE" }); load(); }}>remove</button></td></tr>)}</tbody>
      </table>
    </Card>
  );
}

function useSettings() {
  const [s, setS] = useState<any>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { api("/api/settings").then(setS).catch((e) => setMsg(e.message)); }, []);
  const save = async (patch: any) => {
    try { setS(await api("/api/settings", { method: "PUT", body: JSON.stringify(patch) })); setMsg("Saved — applies to new analyses and re-analyses"); }
    catch (e: any) { setMsg(e.message); }
  };
  return { s, setS, save, msg };
}

const TECH_LABELS: Record<string, string> = {
  nation_charts: "Nations' / clubs' charts", planetary_influence: "Planetary influence (captain, day, colour)",
  victory_houses: "Victory houses", sky_pky: "SKY / PKY", d1_cusps: "D1 cuspal strength", d9_cusps: "D9 cuspal strength",
  nama_pada: "Nama pada", sublords: "KP sublords (+ sublord array)", nakshatra_tara: "Nakshatra taras", planetary_war: "Planetary war",
  house_placement: "Significators on cusps (body)", antiscia: "Antiscia of significators", moon_placement: "Moon placement",
  fortuna: "Part of Fortune (antiscion, lords to Fortuna)", moon_aspects: "Moon's applying aspects", dispositor: "Dispositor of Fortuna",
  misc: "Miscellaneous (nodes, combustion, Pluto, Saturn, Uranus)",
};

function Toggles() {
  const { s, setS, save, msg } = useSettings();
  if (!s) return <Spinner />;
  const t = s.toggles;
  const flip = (group: string, key: string) => setS({ ...s, toggles: { ...t, [group]: { ...t[group], [key]: !t[group][key] } } });
  return (
    <Card className="p-4 max-w-4xl">
      {msg ? <div className="mb-3"><Alert tone="slate">{msg}</Alert></div> : null}
      <div className="font-sans text-sm font-semibold mb-2">Engines</div>
      <div className="flex gap-4 mb-4">{Object.keys(t.engines).map((k) => <label key={k} className="font-sans text-sm flex gap-1.5 items-center"><input type="checkbox" checked={t.engines[k]} onChange={() => flip("engines", k)} /> {k}</label>)}</div>
      <div className="grid md:grid-cols-3 gap-4">
        {(["rao", "chokoisky", "frawley"] as const).map((g) => (
          <div key={g}>
            <div className="font-sans text-sm font-semibold capitalize mb-1">{g}</div>
            {Object.keys(t[g]).map((k) => <label key={k} className="font-sans text-sm flex gap-1.5 items-center py-0.5"><input type="checkbox" checked={t[g][k]} onChange={() => flip(g, k)} /> {TECH_LABELS[k] ?? k}</label>)}
          </div>
        ))}
      </div>
      <Button className="mt-4" onClick={() => save({ toggles: s.toggles })}>Save toggles</Button>
    </Card>
  );
}

function MlConfig() {
  const { s, setS, save, msg } = useSettings();
  if (!s) return <Spinner />;
  const ml = s.ml;
  const set = (k: string, v: any) => setS({ ...s, ml: { ...ml, [k]: v } });
  const n = (v: string) => (v === "" ? null : Number(v));
  return (
    <Card className="p-4 max-w-3xl space-y-3">
      {msg ? <Alert tone="slate">{msg}</Alert> : null}
      <div className="grid md:grid-cols-3 gap-3">
        <Field label="Minimum sample size" hint="blank = milestone default (10 / 15 / 20)"><Input value={ml.min_sample ?? ""} onChange={(e) => set("min_sample", n(e.target.value))} /></Field>
        <Field label="Minimum accuracy" hint="0–1; blank = milestone default (0.65 / 0.70 / 0.75)"><Input value={ml.min_accuracy ?? ""} onChange={(e) => set("min_accuracy", n(e.target.value))} /></Field>
        <Field label="Max combination length" hint="default 3"><Select value={ml.max_combo_length} onChange={(e) => set("max_combo_length", Number(e.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={3}>3</option></Select></Field>
        <Field label="Post-hoc sample weight" hint="default 0.5"><Input value={ml.post_hoc_weight} onChange={(e) => set("post_hoc_weight", Number(e.target.value))} /></Field>
        <Field label="Chi-squared p threshold" hint="default 0.05"><Input value={ml.p_threshold} onChange={(e) => set("p_threshold", Number(e.target.value))} /></Field>
        <Field label="Nightly retrain timezone" hint="runs at 02:00"><Input value={ml.nightly_timezone} onChange={(e) => set("nightly_timezone", e.target.value)} /></Field>
      </div>
      <label className="font-sans text-sm flex gap-1.5 items-center"><input type="checkbox" checked={ml.nightly} onChange={(e) => set("nightly", e.target.checked)} /> Schedule nightly retrain</label>
      <Button onClick={() => save({ ml: s.ml })}>Save ML configuration</Button>
    </Card>
  );
}

function Presets() {
  const [ref, setRef] = useState<any>(null);
  const { s, setS, save, msg } = useSettings();
  useEffect(() => { api("/api/reference").then(setRef).catch(() => setRef({ error: true })); }, []);
  if (!s || !ref) return <Spinner />;
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <Card className="p-4">
        <h3 className="font-sans font-semibold mb-2">Sport presets</h3>
        {ref.error ? <Alert tone="amber">Astrology service offline.</Alert> : (
          <table className="w-full text-sm">
            <thead><tr className="label text-left"><th>Sport</th><th>Draw possible in</th><th>Moon range</th><th>Extra time</th><th>Goal divisor</th></tr></thead>
            <tbody>{Object.entries<any>(ref.sport_presets).map(([k, p]) => <tr key={k} className="border-t border-rule"><td className="py-1">{p.label}</td><td className="text-xs">{p.draw_contexts.join(", ") || "never"}</td><td className="num">{p.moon_range_deg}°</td><td className="num">+{p.extra_time_deg}°</td><td className="num">{p.goal_divisor}</td></tr>)}</tbody>
          </table>
        )}
        <p className="font-sans text-xs text-slate-500 mt-2">Football uses Frawley&apos;s 5° Moon range (+1° when extra time is possible). Other sports use the same default until calibrated (Frawley p.86).</p>
      </Card>
      <Card className="p-4 space-y-2">
        <h3 className="font-sans font-semibold">Ayanamsha defaults</h3>
        {msg ? <Alert tone="slate">{msg}</Alert> : null}
        {Object.entries<string>(s.ayanamsha).map(([k, v]) => (
          <Field key={k} label={k.replace("_", " ")}>
            <Select value={v} disabled onChange={(e) => setS({ ...s, ayanamsha: { ...s.ayanamsha, [k]: e.target.value } })}><option value="lahiri">Lahiri</option><option value="krishnamurti">Krishnamurti</option><option value="tropical">Tropical</option></Select>
          </Field>
        ))}
        <p className="font-sans text-xs text-slate-500">Fixed per the specification (11.2): each engine sees the chart the way its author intended. Shown for reference.</p>
        <Button variant="secondary" disabled onClick={() => save({ ayanamsha: s.ayanamsha })}>Locked by specification</Button>
      </Card>
    </div>
  );
}

function Reference() {
  const [ref, setRef] = useState<any>(null);
  useEffect(() => { api("/api/reference").then(setRef).catch((e) => setRef({ error: e.message })); }, []);
  if (!ref) return <Spinner />;
  if (ref.error) return <Alert tone="amber">{ref.error}</Alert>;
  const fr = ref.friendships_rao_p39_standard_parashari;
  const g = Object.keys(fr);
  return (
    <div className="space-y-4">
      <Alert tone="slate">The cited book tables were not available when this app was built. Where the specification cites a page, the standard classical table is used instead and labelled. Check these against the books (the books win where they differ).</Alert>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-4 overflow-x-auto">
          <h3 className="font-sans font-semibold mb-2">Planetary friendships — standard Parashari (stands in for Rao p.39)</h3>
          <table className="text-xs"><thead><tr><th />{g.map((p) => <th key={p} className="px-1">{p}</th>)}</tr></thead>
            <tbody>{g.map((a) => <tr key={a}><th className="pr-2 text-left">{PLANET_NAME[a]}</th>{g.map((b) => <td key={b} className={`px-1 text-center ${fr[a][b] === "Friend" ? "text-green-700" : fr[a][b] === "Enemy" ? "text-red-700" : "text-slate-500"}`}>{fr[a][b][0]}</td>)}</tr>)}</tbody>
          </table>
        </Card>
        <Card className="p-4">
          <h3 className="font-sans font-semibold mb-2">Planet on cusp effects — Chokoisky table 4.1 (D1) and 5.3 (D9)</h3>
          <table className="w-full text-xs"><thead><tr className="label text-left"><th>Planet</th><th>1/7</th><th>4/10</th><th>6/12</th><th>D9 1/7</th><th>D9 meaning</th></tr></thead>
            <tbody>{Object.entries<any>(ref.d1_cusp_effects_chokoisky_t4_1).map(([p, e]) => <tr key={p} className="border-t border-rule"><td>{PLANET_NAME[p]}</td>{e.map((x: any, i: number) => <td key={i}>{fx(x)}</td>)}<td>{fx(ref.d9_effects_chokoisky_t5_3[p])}</td><td>{ref.d9_meanings[p]}</td></tr>)}</tbody>
          </table>
        </Card>
        <Card className="p-4">
          <h3 className="font-sans font-semibold mb-2">Dignities (stands in for Chokoisky table 3.1)</h3>
          <table className="w-full text-xs"><thead><tr className="label text-left"><th>Planet</th><th>Exaltation</th><th>Debilitation</th><th>Own</th><th>Dig bala house</th></tr></thead>
            <tbody>{Object.keys(ref.dignities.exaltation).map((p) => <tr key={p} className="border-t border-rule"><td>{PLANET_NAME[p]}</td><td>{ref.signs[ref.dignities.exaltation[p]]}</td><td>{ref.signs[ref.dignities.debilitation[p]]}</td><td>{(ref.dignities.own[p] ?? []).map((s: number) => ref.signs[s]).join(", ")}</td><td>{ref.dignities.dig_bala_house[p] ?? ""}</td></tr>)}</tbody>
          </table>
          <h3 className="font-sans font-semibold mt-4 mb-1">Station detection — mean daily motion</h3>
          <p className="text-xs">{Object.entries<number>(ref.station_speeds).map(([p, v]) => `${PLANET_NAME[p]} ${v}°/day`).join(" · ")} — stationary below 10% of mean.</p>
          <h3 className="font-sans font-semibold mt-4 mb-1">Antiscia pairs (Frawley App. 1) & Arabian Parts (App. 2)</h3>
          <p className="text-xs">{ref.antiscia_pairs.map((p: string[]) => p.join(" ↔ ")).join(" · ")}</p>
          <p className="text-xs mt-1">{Object.entries<string>(ref.arabian_parts).map(([k, v]) => `${k} = ${v}`).join(" · ")}</p>
        </Card>
        <Card className="p-4">
          <h3 className="font-sans font-semibold mb-2">Key yogataras (live positions from the Swiss Ephemeris star catalogue)</h3>
          <table className="w-full text-xs"><thead><tr className="label text-left"><th>Star</th><th>Spec position (sid.)</th><th>Points</th><th>Effect</th></tr></thead>
            <tbody>{Object.entries<any>(ref.key_stars).map(([s, v]) => <tr key={s} className="border-t border-rule"><td>{s}</td><td className="num">{(v[0] % 30).toFixed(1)}° {ref.signs[Math.floor(v[0] / 30)]}</td><td className="num">{v[1] > 0 ? "+" : ""}{v[1]}</td><td>{v[2]}</td></tr>)}</tbody>
          </table>
          <p className="font-sans text-[11px] text-slate-500 mt-1">The spec lists Algol at 26° Taurus, which is its tropical position; sidereally Algol is near 2° Taurus. The engine uses the computed sidereal position.</p>
          <h3 className="font-sans font-semibold mt-4 mb-1">28 nakshatra yogataras</h3>
          <p className="text-xs">{ref.yogataras.map((y: string[]) => `${y[0]}: ${y[1]}`).join(" · ")}</p>
        </Card>
        <Card className="p-4 lg:col-span-2">
          <h3 className="font-sans font-semibold mb-2">108 navamsha syllables — Avakahada chakra (stands in for Chokoisky table 7.1)</h3>
          <div className="grid grid-cols-3 md:grid-cols-6 lg:grid-cols-9 gap-x-4 text-xs">
            {Array.from({ length: 27 }, (_, i) => ref.navamsha_syllables_avakahada.slice(i * 4, i * 4 + 4)).map((g4: any[]) => (
              <div key={g4[0].nakshatra} className="py-0.5"><span className="text-slate-500">{g4[0].nakshatra}:</span> {g4.map((x) => x.syllable).join(" ")}</div>
            ))}
          </div>
          <h3 className="font-sans font-semibold mt-4 mb-1">Rao planetary influence</h3>
          <p className="text-xs">Numbers: {Object.entries<string>(ref.number_planet).map(([n, p]) => `${n}=${PLANET_NAME[p]}`).join(", ")} · Colours: {Object.entries<string>(ref.color_planet).map(([c, p]) => `${c}→${PLANET_NAME[p]}`).join(", ")} · Captain numbers: 9 and 7 best, then 3, 5, 1; 8, 4, 2 unfavourable.</p>
        </Card>
      </div>
    </div>
  );
}
const fx = (x: any) => (x === 1 ? "+" : x === -1 ? "−" : x === 0 ? "0" : x === "M" ? "±" : x === "UR" ? "+ direct / − Rx" : x === "NE" ? "− direct / + Rx" : String(x));

function Admin() {
  const [on, setOn] = useState(false);
  useEffect(() => setOn(localStorage.getItem("astro-admin") === "1"), []);
  return (
    <Card className="p-4 max-w-xl">
      <label className="font-sans text-sm flex gap-2 items-center">
        <input type="checkbox" checked={on} onChange={(e) => { localStorage.setItem("astro-admin", e.target.checked ? "1" : "0"); setOn(e.target.checked); }} />
        Admin mode on this browser
      </label>
      <p className="text-sm text-slate-600 mt-2">Admin mode enables soft-delete, viewing deleted records and correcting a completed record&apos;s scoreline. There is no authentication in this build — put the app behind your own auth before exposing it beyond your machine.</p>
    </Card>
  );
}
