import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

export async function GET(req: Request) {
  return handle(async () => {
    const q = new URL(req.url).searchParams.get("q") ?? "";
    return prisma.venue.findMany({
      where: q ? { name: { contains: q, mode: "insensitive" } } : undefined,
      orderBy: { name: "asc" },
      take: q ? 20 : 2000,
    });
  });
}

export async function POST(req: Request) {
  return handle(async () => {
    const b = await req.json();
    return prisma.venue.create({
      data: { name: b.name, canonicalName: b.canonicalName || null, lat: Number(b.lat), long: Number(b.long),
        timezone: b.timezone || null, coordinateSource: b.coordinateSource || "manual", lastVerifiedAt: new Date() },
    });
  });
}
