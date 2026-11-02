import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";

// { date, time_gmt, lat, long, ayanamsha? } -> D1 (three variants) + D9 + sublords + antiscia
export async function POST(req: Request) {
  return handle(async () => astro.chart(await req.json()));
}
