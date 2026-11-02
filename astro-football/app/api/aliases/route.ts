import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

export async function GET() {
  return handle(() => prisma.wikiAlias.findMany({ orderBy: { venueName: "asc" } }));
}

export async function POST(req: Request) {
  return handle(async () => {
    const b = await req.json();
    return prisma.wikiAlias.upsert({
      where: { venueName: b.venueName },
      create: { venueName: b.venueName, wikiTitle: b.wikiTitle },
      update: { wikiTitle: b.wikiTitle },
    });
  });
}

export async function DELETE(req: Request) {
  return handle(async () => {
    const id = new URL(req.url).searchParams.get("id")!;
    await prisma.wikiAlias.delete({ where: { id } });
    return { ok: true };
  });
}
