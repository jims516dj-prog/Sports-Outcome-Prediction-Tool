import { Suspense } from "react";
import { MatchDetail } from "@/components/MatchDetail";

export default function MatchPage({ params }: PageProps<"/dataset/[id]">) {
  return (
    <Suspense fallback={<p className="font-sans text-sm text-slate-500">Loading match…</p>}>
      <Detail params={params} />
    </Suspense>
  );
}

async function Detail({ params }: { params: PageProps<"/dataset/[id]">["params"] }) {
  const { id } = await params;
  return <MatchDetail id={id} />;
}
