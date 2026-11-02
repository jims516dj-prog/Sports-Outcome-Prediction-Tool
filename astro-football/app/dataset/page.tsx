import { Suspense } from "react";
import { DatasetTable } from "@/components/DatasetTable";

export default function DatasetPage() {
  // streamed: the table library reads the clock while rendering
  return (
    <Suspense fallback={<p className="font-sans text-sm text-slate-500">Loading dataset…</p>}>
      <DatasetTable />
    </Suspense>
  );
}
