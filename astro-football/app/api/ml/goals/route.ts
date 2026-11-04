import { handle } from "@/lib/api";
import { prisma } from "@/lib/prisma";

// Goal-market evaluation (over/under 2.5, both teams to score) stored with the current model version.
export async function GET() {
  return handle(async () => {
    const v = await prisma.mLModelVersion.findFirst({ where: { isCurrent: true } });
    return { version: v?.versionNumber ?? null, goals: (v?.metrics as any)?.goals ?? null };
  });
}
