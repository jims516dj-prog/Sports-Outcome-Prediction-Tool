// Spec 10.1 - mandatory, persistent, cannot be dismissed.
export function DisclaimerBanner() {
  return (
    <div role="note" className="bg-amber-50 border-b border-amber-300 text-amber-950 text-[13px] leading-snug">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2">
        <strong>⚠️ For astrological research and educational purposes only.</strong>{" "}
        Dr. Ravi Rao&apos;s foundational text <em>Sports Astrology</em> explicitly states: &ldquo;I would go so far as
        to say that the method will not work for persons involved in betting. I would like to call it astrology&apos;s
        curse.&rdquo; This application does not facilitate gambling and must not be used for that purpose. Predictions
        are probabilistic estimates based on classical texts, not guarantees. The traditional 70/30 doctrine holds that
        astrologers are at best 70% accurate. Use these analyses as explorations of astrological method, not as betting
        advice.
      </div>
    </div>
  );
}
