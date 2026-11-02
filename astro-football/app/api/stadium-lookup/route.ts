import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { prisma } from "@/lib/prisma";

// Spec 3.2: cached venue -> Wikipedia (via disambiguation table) -> OpenStreetMap -> manual.
export async function GET(req: Request) {
  return handle(async () => {
    const sp = new URL(req.url).searchParams;
    const name = (sp.get("name") ?? "").trim();
    const force = sp.get("force") === "1";
    if (!name) return Response.json({ error: "name is required" }, { status: 400 });
    if (!force) {
      const cached = await prisma.venue.findUnique({ where: { name } });
      if (cached)
        return {
          source: cached.coordinateSource, cached: true, lat: cached.lat, long: cached.long,
          canonicalName: cached.canonicalName, timezone: cached.timezone, pageId: cached.wikipediaPageId,
          lastVerifiedAt: cached.lastVerifiedAt,
        };
    }
    const alias = await prisma.wikiAlias.findFirst({ where: { venueName: { equals: name, mode: "insensitive" } } });
    return astro.geo(name, alias?.wikiTitle);
  });
}
