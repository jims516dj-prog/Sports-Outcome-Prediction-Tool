"use client";
// Historical dataset browser (spec 9.3).
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable, type SortingState } from "@tanstack/react-table";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Modal, Select, Spinner } from "@/components/ui";
import { api, fmtDate, isAdminMode } from "@/lib/client";

type Row = {
  id: string; kickoffGMT: string; teamA: string; teamB: string; scoreA: number | null; scoreB: number | null; status: string;
  sport: string; league: string | null; venue: string; predicted: string | null; actual: string | null; agreement: number | null; pattern: string | null;
  mlCount: number; notes: string | null; hasCaptainData: boolean; postHoc: boolean; stale: boolean; deleted: boolean; confidence: number | null;
};
const ch = createColumnHelper<Row>();
const LEAGUES: Record<string, string> = {
  "en.1": "Premier League", "de.1": "Bundesliga", "es.1": "La Liga", "it.1": "Serie A", "fr.1": "Ligue 1",
  "en.2": "Championship", "nl.1": "Eredivisie", "pt.1": "Primeira Liga",
};
const winnerName = (r: Row, s: string | null) => (s === "A" ? r.teamA : s === "B" ? r.teamB : s === "draw" ? "Draw" : "—");
const FILTERS = ["q", "from", "to", "sport", "league", "status", "agreement", "correct", "mlPattern", "captain", "showDeleted"] as const;

export function DatasetTable() {
  const router = useRouter();
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [data, setData] = useState<{ rows: Row[]; total: number }>({ rows: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mark, setMark] = useState<Row | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [admin, setAdmin] = useState(false);
  useEffect(() => setAdmin(isAdminMode()), []);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    for (const k of FILTERS) if (filters[k]) p.set(k, filters[k]);
    if (sorting[0]) { p.set("sort", sorting[0].id); p.set("dir", sorting[0].desc ? "desc" : "asc"); }
    return p;
  }, [filters, sorting]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams(query);
      p.set("page", String(page));
      p.set("pageSize", String(pageSize));
      setData(await api(`/api/matches?${p}`));
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [query, page, pageSize]);
  useEffect(() => { load(); }, [load]);

  async function action(id: string, fn: () => Promise<unknown>) {
    setBusyId(id);
    try { await fn(); await load(); } catch (e: any) { setError(e.message); } finally { setBusyId(null); }
  }

  const columns = useMemo(() => [
    ch.accessor("kickoffGMT", { id: "date", header: "Date (GMT)", cell: (c) => <span className="num text-xs whitespace-nowrap">{fmtDate(c.getValue())}</span> }),
    ch.accessor("teamA", { id: "teamA", header: "Team A" }),
    ch.accessor("teamB", { id: "teamB", header: "Team B" }),
    ch.display({ id: "score", header: "Scoreline", cell: (c) => c.row.original.scoreA == null ? <Badge tone="amber">Pending</Badge> : <span className="num">{c.row.original.scoreA}–{c.row.original.scoreB}</span> }),
    ch.accessor("status", { id: "status", header: "Status", cell: (c) => <span className="text-xs flex flex-wrap gap-1 items-center">{c.getValue()}{c.row.original.postHoc ? <Badge tone="slate">post-hoc</Badge> : null}{c.row.original.stale ? <Badge tone="red">stale</Badge> : null}{c.row.original.deleted ? <Badge tone="red">deleted</Badge> : null}</span> }),
    ch.accessor("league", { id: "league", header: "League", enableSorting: false, cell: (c) => <span className="text-xs">{LEAGUES[c.getValue() ?? ""] ?? c.row.original.sport}</span> }),
    ch.accessor("venue", { id: "venue", header: "Venue", cell: (c) => <span className="text-xs">{c.getValue()}</span> }),
    ch.display({ id: "predicted", header: "Predicted", cell: (c) => <span className="font-medium">{winnerName(c.row.original, c.row.original.predicted)}</span> }),
    ch.display({ id: "actual", header: "Actual", cell: (c) => winnerName(c.row.original, c.row.original.actual) }),
    ch.display({ id: "correct", header: "Correct?", cell: (c) => { const r = c.row.original; return r.actual == null ? "—" : r.predicted === r.actual ? <Badge tone="green">✓</Badge> : <Badge tone="red">✗</Badge>; } }),
    ch.accessor("agreement", { id: "agreement", header: "Engines agreed", cell: (c) => <span className="text-xs">{c.getValue() === 3 ? "all 3" : c.getValue() === 2 ? "2 of 3" : "none"}</span> }),
    ch.accessor("mlCount", { id: "ml", header: "ML pattern", enableSorting: false, cell: (c) => (c.getValue() ? <Badge tone="teal">{c.getValue()}</Badge> : "—") }),
    ch.accessor("notes", { id: "notes", header: "Notes", enableSorting: false, cell: (c) => <span title={c.getValue() ?? ""} className="text-xs text-slate-600 truncate max-w-48 block">{c.getValue()}</span> }),
    ch.display({
      id: "actions", header: "Actions", cell: (c) => {
        const r = c.row.original;
        return (
          <div className="flex gap-1 flex-wrap font-sans text-xs">
            <Link className="underline" href={`/dataset/${r.id}`}>View</Link>
            <Link className="underline" href={`/dataset/${r.id}?tab=edit`}>Edit</Link>
            {r.scoreA == null ? <button className="underline text-teal-ml" onClick={() => setMark(r)}>Mark result</button> : null}
            <button className="underline" disabled={busyId === r.id} onClick={() => action(r.id, () => api(`/api/matches/${r.id}/reanalyze`, { method: "POST" }))}>{busyId === r.id ? "…" : "Re-analyze"}</button>
            {admin && !r.deleted ? <button className="underline text-red-700" onClick={() => confirm("Soft-delete this record? It stays in the audit trail but is hidden and excluded from ML training.") && action(r.id, () => api(`/api/matches/${r.id}`, { method: "DELETE" }))}>Delete</button> : null}
          </div>
        );
      },
    }),
  ], [busyId, admin]); // eslint-disable-line react-hooks/exhaustive-deps

  const table = useReactTable({
    data: data.rows, columns, getCoreRowModel: getCoreRowModel(), manualSorting: true, manualPagination: true,
    state: { sorting }, onSortingChange: (u) => { setSorting(u); setPage(1); },
    pageCount: Math.ceil(data.total / pageSize),
  });
  const setFilter = (k: string, v: string) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1); };
  const pages = Math.max(1, Math.ceil(data.total / pageSize));

  return (
    <div>
      <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
        <h1 className="text-2xl font-semibold">Historical Dataset</h1>
        <div className="flex gap-2 flex-wrap">
          <Button variant="teal" onClick={() => router.push("/dataset/new")}>Add historical match</Button>
          <Button onClick={() => router.push("/analyze")}>Add new match for analysis</Button>
          <a href={`/api/matches/export?${query}&format=csv`}><Button variant="secondary">Export CSV</Button></a>
          <a href={`/api/matches/export?${query}&format=json`}><Button variant="secondary">Export JSON</Button></a>
        </div>
      </div>
      <Card className="p-3 mb-4">
        <div className="grid grid-cols-2 md:grid-cols-6 lg:grid-cols-12 gap-2 items-end">
          <Field label="Search" className="col-span-2"><Input placeholder="team or venue" value={filters.q ?? ""} onChange={(e) => setFilter("q", e.target.value)} /></Field>
          <Field label="From"><Input type="date" value={filters.from ?? ""} onChange={(e) => setFilter("from", e.target.value)} /></Field>
          <Field label="To"><Input type="date" value={filters.to ?? ""} onChange={(e) => setFilter("to", e.target.value)} /></Field>
          <Field label="Sport"><Select value={filters.sport ?? ""} onChange={(e) => setFilter("sport", e.target.value)}><option value="">all</option><option value="football">football</option><option value="american_football">american football</option><option value="cricket">cricket</option><option value="tennis">tennis</option><option value="basketball">basketball</option><option value="ice_hockey">ice hockey</option></Select></Field>
          <Field label="League"><Select value={filters.league ?? ""} onChange={(e) => setFilter("league", e.target.value)}><option value="">all</option>{Object.entries(LEAGUES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}<option value="none">entered by hand</option></Select></Field>
          <Field label="Status"><Select value={filters.status ?? ""} onChange={(e) => setFilter("status", e.target.value)}><option value="">all</option><option value="pending">pending</option><option value="completed">completed</option><option value="abandoned">abandoned</option><option value="walkover">walkover</option><option value="no_result">no result</option><option value="dl_method">D/L</option></Select></Field>
          <Field label="Engines"><Select value={filters.agreement ?? ""} onChange={(e) => setFilter("agreement", e.target.value)}><option value="">any</option><option value="all3">all 3 agree</option><option value="two">2 of 3</option><option value="none">all disagree</option></Select></Field>
          <Field label="Prediction"><Select value={filters.correct ?? ""} onChange={(e) => setFilter("correct", e.target.value)}><option value="">any</option><option value="correct">correct</option><option value="incorrect">incorrect</option><option value="pending">pending</option></Select></Field>
          <Field label="ML pattern"><Select value={filters.mlPattern ?? ""} onChange={(e) => setFilter("mlPattern", e.target.value)}><option value="">any</option><option value="yes">yes</option><option value="no">no</option></Select></Field>
          <Field label="Captain data"><Select value={filters.captain ?? ""} onChange={(e) => setFilter("captain", e.target.value)}><option value="">any</option><option value="yes">yes</option><option value="no">no</option></Select></Field>
        </div>
        {admin ? <label className="font-sans text-xs flex items-center gap-1 mt-2"><input type="checkbox" checked={filters.showDeleted === "1"} onChange={(e) => setFilter("showDeleted", e.target.checked ? "1" : "")} /> show soft-deleted (admin)</label> : null}
      </Card>
      {error ? <div className="mb-3"><Alert tone="red">{error}</Alert></div> : null}
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[1320px] text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-rule bg-slate-50">
                {hg.headers.map((h) => (
                  <th key={h.id} className="text-left px-2.5 py-2 label whitespace-nowrap">
                    {h.column.getCanSort() ? (
                      <button onClick={h.column.getToggleSortingHandler()} className="uppercase">
                        {flexRender(h.column.columnDef.header, h.getContext())}{" "}
                        {{ asc: "▲", desc: "▼" }[h.column.getIsSorted() as string] ?? ""}
                      </button>
                    ) : flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((r) => (
              <tr key={r.id} className={`border-b border-rule hover:bg-slate-50 ${r.original.deleted ? "opacity-50" : ""}`}>
                {r.getVisibleCells().map((c) => <td key={c.id} className="px-2.5 py-1.5 align-top">{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}
              </tr>
            ))}
            {!loading && data.rows.length === 0 ? (
              <tr><td colSpan={columns.length} className="p-6 text-center text-slate-500">No matches. Add one with the buttons above.</td></tr>
            ) : null}
          </tbody>
        </table>
      </Card>
      <div className="flex justify-between items-center mt-3 font-sans text-sm">
        <span>{loading ? <Spinner label="Loading" /> : `${data.total.toLocaleString()} matches`}</span>
        <div className="flex gap-2 items-center">
          <Select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }} className="w-28">{[25, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}</Select>
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Prev</Button>
          <span>Page {page} of {pages}</span>
          <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next ›</Button>
        </div>
      </div>
      <MarkResultModal row={mark} onClose={() => setMark(null)} onDone={() => { setMark(null); load(); }} />
    </div>
  );
}

export function MarkResultModal({ row, onClose, onDone }: { row: { id: string; teamA: string; teamB: string } | null; onClose: () => void; onDone: () => void }) {
  const [a, setA] = useState(""), [b, setB] = useState(""), [status, setStatus] = useState("completed"), [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null), [busy, setBusy] = useState(false);
  useEffect(() => { setA(""); setB(""); setStatus("completed"); setNotes(""); setErr(null); }, [row]);
  return (
    <Modal open={!!row} onClose={onClose} title={`Mark result — ${row?.teamA} vs ${row?.teamB}`}>
      <div className="grid grid-cols-2 gap-3">
        <Field label={row?.teamA ?? "A"}><Input type="number" min={0} value={a} onChange={(e) => setA(e.target.value)} /></Field>
        <Field label={row?.teamB ?? "B"}><Input type="number" min={0} value={b} onChange={(e) => setB(e.target.value)} /></Field>
        <Field label="Status"><Select value={status} onChange={(e) => setStatus(e.target.value)}><option value="completed">Completed</option><option value="walkover">Walkover</option><option value="abandoned">Abandoned</option><option value="no_result">No result</option><option value="dl_method">D/L method applied</option></Select></Field>
        <Field label="Notes"><Input value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      </div>
      <p className="font-sans text-xs text-slate-500 mt-2">The engine verdicts are not recomputed — the original prediction stands. Once completed, the scoreline is locked.</p>
      {err ? <div className="mt-2"><Alert tone="red">{err}</Alert></div> : null}
      <div className="mt-3 flex gap-2">
        <Button disabled={busy || (status === "completed" && (a === "" || b === ""))} onClick={async () => {
          setBusy(true);
          try {
            await api(`/api/matches/${row!.id}/result`, { method: "POST", body: JSON.stringify({ scoreA: a === "" ? null : Number(a), scoreB: b === "" ? null : Number(b), status, notes: notes || undefined }) });
            onDone();
          } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
        }}>Save result</Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
    </Modal>
  );
}
