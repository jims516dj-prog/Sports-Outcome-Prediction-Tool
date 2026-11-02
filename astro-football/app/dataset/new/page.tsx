import { MatchForm } from "@/components/MatchForm";

export default function NewHistoricalPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Add historical match</h1>
      <p className="text-slate-600 mb-5">For a match that has already been played. The engines still run, and the verdict is stored tagged <em>post-hoc</em>.</p>
      <MatchForm mode="historical" />
    </div>
  );
}
