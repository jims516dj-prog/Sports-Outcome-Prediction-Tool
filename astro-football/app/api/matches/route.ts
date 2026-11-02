import { handle, isAdmin } from "@/lib/api";
import { createMatch, type MatchInput } from "@/lib/dataset/crud";
import { listMatches, parseFilters } from "@/lib/dataset/query";

export async function GET(req: Request) {
  return handle(async () => listMatches(parseFilters(new URL(req.url).searchParams, isAdmin(req))));
}

// body: { input: MatchInput, historical: boolean }
export async function POST(req: Request) {
  return handle(async () => {
    const { input, historical } = (await req.json()) as { input: MatchInput; historical?: boolean };
    const m = await createMatch(input, { historical: !!historical });
    return { id: m.id };
  });
}
