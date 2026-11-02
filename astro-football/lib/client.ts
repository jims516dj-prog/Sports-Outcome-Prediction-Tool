"use client";
// Browser-side fetch helper. Admin mode (Settings) is a local flag sent as a header.
export const isAdminMode = () => typeof window !== "undefined" && localStorage.getItem("astro-admin") === "1";

export async function api<T = any>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "content-type": "application/json", ...(isAdminMode() ? { "x-admin": "1" } : {}), ...(init?.headers ?? {}) },
  });
  const ct = res.headers.get("content-type") ?? "";
  const body = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error((body as any)?.error ?? `Request failed (${res.status})`);
  return body as T;
}

export const PLANET_GLYPH: Record<string, string> = {
  Su: "☉", Mo: "☽", Ma: "♂", Me: "☿", Ju: "♃", Ve: "♀", Sa: "♄", Ra: "☊", Ke: "☋", Ur: "♅", Ne: "♆", Pl: "♇",
  Ce: "⚳", Ch: "⚷", Uk: "Uk", Gu: "Gu",
};
export const PLANET_NAME: Record<string, string> = {
  Su: "Sun", Mo: "Moon", Ma: "Mars", Me: "Mercury", Ju: "Jupiter", Ve: "Venus", Sa: "Saturn", Ra: "Rahu", Ke: "Ketu",
  Ur: "Uranus", Ne: "Neptune", Pl: "Pluto", Ce: "Ceres", Ch: "Chiron", Uk: "Upaketu", Gu: "Gulika",
};
// U+FE0E forces text (not emoji) presentation
export const SIGN_GLYPH = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"].map((g) => g + "\uFE0E");
export const PLANET_ORDER = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke", "Ur", "Ne", "Pl", "Ce", "Ch", "Uk", "Gu"];
/** JSONB stores object keys in its own order; restore the canonical planet order. */
export const byPlanet = <T,>(o: Record<string, T> | undefined) =>
  Object.entries(o ?? {}).sort(([a], [b]) => PLANET_ORDER.indexOf(a) - PLANET_ORDER.indexOf(b));
export const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
export const JERSEY_COLORS = ["Mars-red", "Saturn-black/blue", "Jupiter-gold", "Venus-yellow", "Mercury-green", "Sun-maroon", "Moon-white", "Rahu-brown", "Ketu-grey"];
export const ENGINE_META = {
  rao: { title: "Rao — Inclusive Methodology", book: "Sports Astrology: The Inclusive Methodology of Game Analysis", author: "Dr. Ravi Rao (2017)", color: "#d97706", soft: "#fdf3e2" },
  chokoisky: { title: "Chokoisky — Gambler's Dharma", book: "Gambler's Dharma: Sports Betting with Vedic Astrology", author: "Simon Chokoisky (2017)", color: "#4338ca", soft: "#eef0fd" },
  frawley: { title: "Frawley — Event Chart", book: "Sports Astrology", author: "John Frawley (Apprentice Books, 2007)", color: "#1f6f3a", soft: "#e9f4ec" },
} as const;
export const fmtDate = (d: string | Date) => new Date(d).toISOString().slice(0, 16).replace("T", " ");
