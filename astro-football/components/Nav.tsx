"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  ["/", "Dashboard"],
  ["/analyze", "Analyze"],
  ["/dataset", "Historical Dataset"],
  ["/ml", "ML Training"],
  ["/settings", "Settings"],
] as const;

export function Nav() {
  const path = usePathname();
  return (
    <header className="bg-terminal text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-12 flex items-center gap-6">
        <Link href="/" className="font-sans font-semibold tracking-wide text-[15px]">
          <span className="text-amber-400">☉</span> Astro<span className="text-teal-300">Football</span>
        </Link>
        <nav className="flex gap-1 font-sans text-sm">
          {LINKS.map(([href, label]) => {
            const active = href === "/" ? path === "/" : path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`px-3 py-1.5 rounded ${active ? "bg-slate-700 text-white" : "text-slate-300 hover:text-white hover:bg-slate-800"}`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
