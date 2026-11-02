import { handle } from "@/lib/api";
import { astro } from "@/lib/astro";
import { getSettings, saveSettings } from "@/lib/settings";

export async function GET() {
  return handle(async () => {
    const s = await getSettings();
    // keep the service's scheduler in line with the stored preference
    return astro.schedule({ enabled: s.ml.nightly, timezone: s.ml.nightly_timezone, config: s.ml });
  });
}

export async function POST(req: Request) {
  return handle(async () => {
    const { enabled } = await req.json();
    const s = await saveSettings({ ml: { nightly: !!enabled } as any });
    return astro.schedule({ enabled: s.ml.nightly, timezone: s.ml.nightly_timezone, config: s.ml });
  });
}
