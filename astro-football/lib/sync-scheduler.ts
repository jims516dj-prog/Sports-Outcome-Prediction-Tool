// Background refresh while the app runs: checks every 10 minutes and starts a "refresh" sync
// when automatic sync is on and the interval set in Data sync has passed since the last one.
import { currentJob, recentRuns, startSync } from "@/lib/sync";
import { getSettings } from "@/lib/settings";

const g = globalThis as unknown as { __astroSyncTimer?: NodeJS.Timeout };

async function tick() {
  try {
    const s = await getSettings();
    if (!s.sync.auto || currentJob()?.state === "running") return;
    const last = (await recentRuns()).find((r) => r.mode === "refresh" && r.finishedAt);
    const due = !last || Date.now() - Date.parse(last.finishedAt!) >= s.sync.interval_hours * 3600000;
    if (due) startSync("refresh", { trigger: "auto" });
  } catch {
    // database or astrology service not ready yet: try again on the next tick
  }
}

export function startScheduler() {
  if (g.__astroSyncTimer || process.env.NEXT_PHASE === "phase-production-build") return;
  g.__astroSyncTimer = setInterval(tick, 10 * 60000);
  g.__astroSyncTimer.unref();
  setTimeout(tick, 60000).unref();
}
