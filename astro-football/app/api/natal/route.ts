import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";

export async function POST(req: Request) {
  return handle(async () => astro.natal(await req.json()));
}
