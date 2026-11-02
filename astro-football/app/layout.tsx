import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Astrological Football Match Analyzer",
  description: "Three-engine astrological analysis of football matches (Rao, Chokoisky, Frawley) - research instrument",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <DisclaimerBanner />
        <Suspense fallback={<div className="bg-terminal h-12" />}>
          <Nav />
        </Suspense>
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 py-6">{children}</main>
        <footer className="border-t border-rule py-4 text-center label">
          Rao · Chokoisky · Frawley — astrological research instrument
        </footer>
      </body>
    </html>
  );
}
