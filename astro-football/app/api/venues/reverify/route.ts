import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { prisma } from "@/lib/prisma";

// "Re-verify all venue coordinates from Wikipedia" (spec 3.2). Manual overrides are kept.
export async function POST() {
  return handle(async () => {
    const venues = await prisma.venue.findMany({ where: { NOT: { coordinateSource: "manual" } } });
    const aliases = Object.fromEntries((await prisma.wikiAlias.findMany()).map((a) => [a.venueName.toLowerCase(), a.wikiTitle]));
    const out = { checked: 0, updated: 0, failed: [] as string[] };
    for (const v of venues) {
      out.checked++;
      try {
        const r = await astro.geo(v.name, aliases[v.name.toLowerCase()]);
        if (r.source !== "wikipedia") throw new Error(r.message ?? "no Wikipedia coordinates");
        await prisma.venue.update({
          where: { id: v.id },
          data: { lat: r.lat, long: r.long, coordinateSource: "wikipedia", wikipediaPageId: r.pageId ?? null,
            canonicalName: r.canonicalName ?? v.canonicalName, timezone: r.timezone ?? v.timezone, lastVerifiedAt: new Date() },
        });
        out.updated++;
      } catch {
        out.failed.push(v.name);
      }
    }
    return out;
  });
}
