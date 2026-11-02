"use client";
// SVG chart wheel: Ascendant on the left (9 o'clock), zodiac anticlockwise.
import { PLANET_GLYPH, PLANET_NAME, SIGN_GLYPH } from "@/lib/client";

type P = { lon: number; retrograde?: boolean };
export function ChartWheel({
  ascendant, cusps, planets, title, color = "#334155", size = 300, wholeSign = false,
}: {
  ascendant: number; cusps?: number[]; planets: Record<string, P>; title?: string; color?: string; size?: number; wholeSign?: boolean;
}) {
  const c = size / 2;
  const R = c - 6, rSign = R - 22, rHouse = rSign - 4, rPlanet = rHouse - 26, rInner = 34;
  const ang = (lon: number) => ((180 - (lon - ascendant)) * Math.PI) / 180;
  const pt = (lon: number, r: number) => [c + r * Math.cos(ang(lon)), c - r * Math.sin(ang(lon))];
  const houseLines = wholeSign
    ? Array.from({ length: 12 }, (_, i) => Math.floor(ascendant / 30) * 30 + i * 30)
    : cusps ?? [];
  // spread planets that sit close together
  const entries = Object.entries(planets).filter(([, p]) => Number.isFinite(p.lon)).sort((a, b) => a[1].lon - b[1].lon);
  const placed: { k: string; lon: number; disp: number; ring: number; retro?: boolean }[] = [];
  for (const [k, p] of entries) {
    const prev = placed[placed.length - 1];
    const close = prev && Math.abs(p.lon - prev.lon) < 7;
    placed.push({ k, lon: p.lon, disp: p.lon, ring: close ? (prev.ring + 1) % 3 : 0, retro: p.retrograde });
  }
  return (
    <figure className="flex flex-col items-center">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="max-w-full" role="img" aria-label={title ?? "chart wheel"}>
        <circle cx={c} cy={c} r={R} fill="#fff" stroke={color} strokeWidth={1.5} />
        <circle cx={c} cy={c} r={rSign} fill="none" stroke="#cbd5e1" />
        <circle cx={c} cy={c} r={rInner} fill="#f8fafc" stroke="#cbd5e1" />
        {Array.from({ length: 12 }, (_, i) => {
          const [x1, y1] = pt(i * 30, rSign);
          const [x2, y2] = pt(i * 30, R);
          const [tx, ty] = pt(i * 30 + 15, (R + rSign) / 2);
          return (
            <g key={i}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#cbd5e1" />
              <text x={tx} y={ty} textAnchor="middle" dominantBaseline="central" fontSize={13} fill={i % 4 === 0 ? "#b45309" : i % 4 === 1 ? "#166534" : i % 4 === 2 ? "#1d4ed8" : "#0e7490"}>
                {SIGN_GLYPH[i]}
              </text>
            </g>
          );
        })}
        {houseLines.map((lon, i) => {
          const [x1, y1] = pt(lon, rInner);
          const [x2, y2] = pt(lon, rSign);
          const [hx, hy] = pt(lon + (((houseLines[(i + 1) % 12] ?? lon + 30) - lon + 360) % 360) / 2, rInner + 12);
          const angle = i % 3 === 0;
          return (
            <g key={`h${i}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={angle ? color : "#94a3b8"} strokeWidth={angle ? 1.6 : 0.7} />
              <text x={hx} y={hy} fontSize={8.5} textAnchor="middle" dominantBaseline="central" fill="#64748b" fontFamily="ui-sans-serif">
                {i + 1}
              </text>
            </g>
          );
        })}
        {placed.map((p) => {
          const r = rPlanet - p.ring * 15;
          const [x, y] = pt(p.disp, r);
          const [mx, my] = pt(p.lon, rSign);
          const [m2x, m2y] = pt(p.lon, rSign - 5);
          return (
            <g key={p.k}>
              <title>{`${PLANET_NAME[p.k] ?? p.k} ${(p.lon % 30).toFixed(1)}°${p.retro ? " Rx" : ""}`}</title>
              <line x1={mx} y1={my} x2={m2x} y2={m2y} stroke="#0f172a" />
              <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={p.k.length > 1 && !PLANET_GLYPH[p.k]?.match(/[^\w]/) ? 8 : 13} fill={p.retro ? "#b91c1c" : "#0f172a"}>
                {PLANET_GLYPH[p.k] ?? p.k}
              </text>
            </g>
          );
        })}
        <text x={c} y={c} textAnchor="middle" dominantBaseline="central" fontSize={9} fill="#475569" fontFamily="ui-sans-serif">
          ASC {(ascendant % 30).toFixed(0)}° {SIGN_GLYPH[Math.floor(ascendant / 30)]}
        </text>
      </svg>
      {title ? <figcaption className="label mt-1">{title}</figcaption> : null}
    </figure>
  );
}

export function wheelFromChart(chart: any) {
  const planets: Record<string, { lon: number; retrograde?: boolean }> = {};
  for (const [k, p] of Object.entries<any>(chart?.planets ?? {})) planets[k] = { lon: p.lon, retrograde: p.retrograde };
  return {
    ascendant: chart?.ascendant_deg ?? 0,
    cusps: (chart?.cusps_placidus ?? []).map((x: any) => x.lon),
    planets,
  };
}
