import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";
import { teamData } from "@/lib/dataset/teams";

export async function GET(req: Request) {
  return handle(async () => {
    const q = new URL(req.url).searchParams.get("q") ?? "";
    return prisma.team.findMany({
      where: q ? { name: { contains: q, mode: "insensitive" } } : undefined,
      orderBy: { name: "asc" },
      take: q ? 20 : 1000,
    });
  });
}

export async function POST(req: Request) {
  return handle(async () => {
    const b = await req.json();
    return prisma.team.create({ data: teamData(b) as any });
  });
}
