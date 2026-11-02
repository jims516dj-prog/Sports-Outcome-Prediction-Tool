import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";

export async function GET() {
  return handle(() => astro.reference());
}
