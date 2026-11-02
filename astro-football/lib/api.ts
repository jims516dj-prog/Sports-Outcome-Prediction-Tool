import { connection } from "next/server";
import { ServiceError } from "@/lib/astro";
import { CrudError } from "@/lib/dataset/crud";

export function isAdmin(req: Request) {
  return req.headers.get("x-admin") === "1";
}

export async function handle(fn: () => Promise<unknown>) {
  await connection(); // always request-time (database / service access)
  try {
    const out = await fn();
    return out instanceof Response ? out : Response.json(out);
  } catch (e: any) {
    const status = e instanceof ServiceError || e instanceof CrudError ? e.status : e?.code === "P2025" ? 404 : 500;
    if (status === 500) console.error(e);
    return Response.json({ error: e?.message ?? String(e) }, { status });
  }
}
