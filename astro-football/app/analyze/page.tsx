import { MatchForm } from "@/components/MatchForm";

export default function AnalyzePage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Analyze a match</h1>
      <p className="text-slate-600 mb-5">Enter the match; the three engines run in parallel on charts cast for the kick-off at the venue. The record is saved as <em>pending</em> until you add the result.</p>
      <MatchForm mode="new" />
    </div>
  );
}
