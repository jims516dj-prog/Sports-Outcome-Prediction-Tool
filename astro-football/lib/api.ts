import { connection } from "next/server";
import { ServiceError } from "@/lib/astro";
import { CrudError } from "@/lib/dataset/crud";

export function isAdmin(req: Request) {
  return req.headers.get("x-admin") === "1";
}

// The background data-sync scheduler starts with the first API request (the app's pages call the
// API as soon as they open). An instrumentation.ts hook would be the usual place, but in this
// Next.js version it makes the dev server reload every page in a loop.
const g = globalThis as unknown as { __astroSchedulerStarted?: boolean };
function ensureScheduler() {
  if (g.__astroSchedulerStarted) return;
  g.__astroSchedulerStarted = true;
  import("@/lib/sync-scheduler").then((m) => m.startScheduler()).catch(() => { g.__astroSchedulerStarted = false; });
}

export async function handle(fn: () => Promise<unknown>) {
  await connection(); // always request-time (database / service access)
  ensureScheduler();
  try {
    const out = await fn();
    return out instanceof Response ? out : Response.json(out);
  } catch (e: any) {
    const status = e instanceof ServiceError || e instanceof CrudError ? e.status : e?.code === "P2025" ? 404 : 500;
    if (status === 500) console.error(e);
    return Response.json({ error: e?.message ?? String(e) }, { status });
  }
}
