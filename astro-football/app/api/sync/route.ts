import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { getSettings } from "@/lib/settings";
import { currentJob, recentRuns, startSync, type SyncMode } from "@/lib/sync";

// Status of the running / recent syncs, available leagues and the sync settings.
export async function GET() {
  return handle(async () => {
    const [s, runs] = await Promise.all([getSettings(), recentRuns()]);
    let info: any = null;
    try {
      info = await astro.sourcesLeagues();
    } catch (e: any) {
      info = { error: e.message };
    }
    return { job: currentJob(), runs, info, settings: { ...s.sync, api_key: s.sync.api_key ? "set" : "" } };
  });
}

// body: { mode: "history" | "refresh", leagues?: string[], fromSeason?, toSeason? }
export async function POST(req: Request) {
  return handle(async () => {
    const b = (await req.json()) as { mode: SyncMode; leagues?: string[]; fromSeason?: string; toSeason?: string };
    if (b.mode !== "history" && b.mode !== "refresh") return Response.json({ error: "mode must be history or refresh" }, { status: 400 });
    if (b.mode === "history" && (!b.fromSeason || !b.toSeason)) return Response.json({ error: "choose the first and last season" }, { status: 400 });
    return { job: startSync(b.mode, { ...b, trigger: "manual" }) };
  });
}
