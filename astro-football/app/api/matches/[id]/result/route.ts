import { handle, isAdmin } from "@/lib/api";
import { updateMatch } from "@/lib/dataset/crud";

// Quick "Mark result" action: { scoreA, scoreB, status?, notes? }
export async function POST(req: Request, ctx: RouteContext<"/api/matches/[id]/result">) {
  return handle(async () => {
    const { id } = await ctx.params;
    const b = await req.json();
    const r = await updateMatch(
      id,
      { scoreA: b.scoreA ?? null, scoreB: b.scoreB ?? null, status: b.status || undefined, notes: b.notes ?? undefined },
      { admin: isAdmin(req), editedBy: "mark-result" },
    );
    return { id: r.match.id, status: r.match.status };
  });
}
