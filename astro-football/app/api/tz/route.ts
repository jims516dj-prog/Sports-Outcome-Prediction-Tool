import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";

// ?lat=&long=&gmt=YYYY-MM-DDTHH:MM  or  &local=YYYY-MM-DDTHH:MM
export async function GET(req: Request) {
  return handle(async () => {
    const p = Object.fromEntries(new URL(req.url).searchParams);
    return astro.tz(p);
  });
}
