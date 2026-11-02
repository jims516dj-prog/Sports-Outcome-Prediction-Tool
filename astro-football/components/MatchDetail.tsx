"use client";
// Match record detail & edit (spec 9.4).
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AnalysisView } from "@/components/AnalysisView";
import { MarkResultModal } from "@/components/DatasetTable";
import { MatchForm, formFromMatch } from "@/components/MatchForm";
import { Alert, Badge, Button, Card, Spinner } from "@/components/ui";
import { api, fmtDate } from "@/lib/client";

export function MatchDetail({ id }: { id: string }) {
  const sp = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState(sp.get("tab") ?? "analysis");
  const [data, setData] = useState<{ match: any; combos: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mark, setMark] = useState(false);
  const saved = sp.get("saved");

  const load = useCallback(() => api(`/api/matches/${id}`).then(setData).catch((e) => setError(e.message)), [id]);
  useEffect(() => { load(); }, [load, saved]); // refetch after an edit (same route, new query)
  useEffect(() => setTab(sp.get("tab") ?? "analysis"), [sp]);

  if (error) return <Alert tone="red">{error}</Alert>;
  if (!data) return <Spinner label="Loading match…" />;
  const m = data.match;
  const go = (t: string) => { setTab(t); router.replace(`/dataset/${id}?tab=${t}`, { scroll: false }); };

  return (
    <div>
      <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
        <div className="font-sans text-sm text-slate-600">
          <Link href="/dataset" className="underline">Dataset</Link> / {m.teamA.displayName} vs {m.teamB.displayName}
          <span className="ml-2">
            <Badge tone={m.status === "pending" ? "amber" : m.status === "completed" ? "green" : "slate"}>{m.status}</Badge>{" "}
            {m.postHocAnalysis ? <Badge>post-hoc</Badge> : null} {m.staleAnalysis ? <Badge tone="red">stale analysis</Badge> : null}
            {m.deleted ? <Badge tone="red">deleted</Badge> : null}
          </span>
        </div>
        <div className="flex gap-2">
          {(["analysis", "edit", "timeline"] as const).map((t) => (
            <Button key={t} variant={tab === t ? "primary" : "secondary"} onClick={() => go(t)}>
              {t === "analysis" ? "Analysis" : t === "edit" ? "Edit record" : `Edit timeline (${m.audits.length})`}
            </Button>
          ))}
          <Link href={`/dataset/${id}/chart`}><Button variant="secondary">Chart view</Button></Link>
          <Button variant="secondary" disabled={busy} onClick={async () => {
            setBusy(true);
            try { await api(`/api/matches/${id}/reanalyze`, { method: "POST" }); await load(); } catch (e: any) { setError(e.message); } finally { setBusy(false); }
          }}>{busy ? "Re-running…" : "Re-run analysis"}</Button>
        </div>
      </div>
      {saved === "stale" ? <div className="mb-3"><Alert tone="amber">Changes saved without re-running — this analysis is marked stale.</Alert></div> : null}
      {saved === "rerun" ? <div className="mb-3"><Alert tone="green">Changes saved and the engines re-run; the earlier verdicts are kept under Analysis versions.</Alert></div> : null}
      {m.status === "pending" && !m.deleted ? (
        <div className="mb-4">
          <Alert tone="teal">
            <div className="flex items-center justify-between gap-3">
              <span><strong>Pending — add scoreline.</strong> After the match is played, record the result; the original verdicts stand.</span>
              <Button variant="teal" onClick={() => setMark(true)}>Add scoreline</Button>
            </div>
          </Alert>
        </div>
      ) : null}

      {tab === "analysis" ? <AnalysisView match={m} combos={data.combos} onReanalyzed={load} /> : null}
      {tab === "edit" ? (
        <div>
          {m.status === "completed" ? <div className="mb-3"><Alert tone="slate">This record is completed: the scoreline and status are locked (spec 12.11). Input fields can still be corrected — changing them prompts a re-run or marks the analysis stale.</Alert></div> : null}
          <MatchForm mode="edit" matchId={id} initial={formFromMatch(m)} />
        </div>
      ) : null}
      {tab === "timeline" ? (
        <Card>
          <table className="w-full text-sm">
            <thead><tr className="label text-left border-b border-rule"><th className="px-4 py-2">When</th><th>Field</th><th>Old value</th><th>New value</th><th>By</th></tr></thead>
            <tbody>
              <tr className="border-b border-rule"><td className="px-4 py-1.5 num text-xs">{fmtDate(m.createdAt)}</td><td colSpan={4}>record created ({m.postHocAnalysis ? "historical, post-hoc" : "pending analysis"})</td></tr>
              {m.audits.map((a: any) => (
                <tr key={a.id} className="border-b border-rule">
                  <td className="px-4 py-1.5 num text-xs">{fmtDate(a.editedAt)}</td><td>{a.fieldName}</td>
                  <td className="text-xs text-slate-600 break-all">{a.oldValue ?? "∅"}</td><td className="text-xs break-all">{a.newValue ?? "∅"}</td><td className="text-xs">{a.editedBy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
      <MarkResultModal row={mark ? { id, teamA: m.teamA.displayName, teamB: m.teamB.displayName } : null} onClose={() => setMark(false)} onDone={() => { setMark(false); load(); }} />
    </div>
  );
}
