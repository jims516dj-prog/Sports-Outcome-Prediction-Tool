// Client for the Python astrology microservice (services/python-astro).
const BASE = process.env.ASTRO_SERVICE_URL ?? "http://127.0.0.1:8001";

export class ServiceError extends Error {
  constructor(message: string, public status = 502) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
      signal: AbortSignal.timeout(init?.timeoutMs ?? 30000),
      cache: "no-store",
    });
  } catch {
    throw new ServiceError("Astrology service unavailable - start services/python-astro (uvicorn main:app --port 8001)", 503);
  }
  if (!res.ok) {
    const txt = await res.text();
    let detail = txt;
    try {
      detail = JSON.parse(txt).detail ?? txt;
    } catch {}
    throw new ServiceError(`Astrology service error: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`, res.status);
  }
  return res.json() as Promise<T>;
}

export const astro = {
  analyze: (body: unknown) => call<any>("/analyze", { method: "POST", body: JSON.stringify(body) }),
  engine: (name: string, body: unknown) => call<any>(`/engine/${name}`, { method: "POST", body: JSON.stringify(body) }),
  chart: (body: unknown) => call<any>("/chart", { method: "POST", body: JSON.stringify(body) }),
  natal: (body: unknown) => call<any>("/natal", { method: "POST", body: JSON.stringify(body) }),
  geo: (name: string, wikiTitle?: string) =>
    call<any>(`/geo/lookup?${new URLSearchParams({ name, ...(wikiTitle ? { wiki_title: wikiTitle } : {}) })}`, { timeoutMs: 10000 }),
  tz: (params: Record<string, string>) => call<any>(`/tz?${new URLSearchParams(params)}`),
  reference: () => call<any>("/reference"),
  train: (config: unknown) => call<any>("/ml/train", { method: "POST", body: JSON.stringify(config ?? {}), timeoutMs: 600000 }),
  schedule: (body?: unknown) =>
    body === undefined ? call<any>("/ml/schedule") : call<any>("/ml/schedule", { method: "POST", body: JSON.stringify(body) }),
  sourcesLeagues: () => call<any>("/sources/leagues", { timeoutMs: 10000 }),
  sourcesPlan: (body: unknown) => call<any>("/sources/plan", { method: "POST", body: JSON.stringify(body), timeoutMs: 900000 }),
  health: () => call<any>("/health", { timeoutMs: 3000 }),
};
