import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { getSettings, saveSettings } from "@/lib/settings";

export async function GET() {
  return handle(() => getSettings());
}

export async function PUT(req: Request) {
  return handle(async () => {
    const patch = await req.json();
    const s = await saveSettings(patch);
    if (patch.ml && ("nightly" in patch.ml || "nightly_timezone" in patch.ml)) {
      try {
        await astro.schedule({ enabled: s.ml.nightly, timezone: s.ml.nightly_timezone, config: s.ml });
      } catch {
        /* service offline: schedule is re-applied when the ML page loads */
      }
    }
    return s;
  });
}
