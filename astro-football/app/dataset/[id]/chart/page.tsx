import { Suspense } from "react";
import { ChartView } from "@/components/ChartView";

export default function ChartPage({ params }: PageProps<"/dataset/[id]/chart">) {
  return (
    <Suspense fallback={<p className="font-sans text-sm text-slate-500">Loading chart…</p>}>
      <Inner params={params} />
    </Suspense>
  );
}

async function Inner({ params }: { params: PageProps<"/dataset/[id]/chart">["params"] }) {
  const { id } = await params;
  return <ChartView id={id} />;
}
