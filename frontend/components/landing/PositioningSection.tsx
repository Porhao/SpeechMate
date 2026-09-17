import { EarOff } from "lucide-react";

// A deliberate, contrarian design decision — everyone else markets live
// mid-speech correction as the selling point. This is the one place that
// claim gets stated plainly instead of staying an architecture footnote.
export default function PositioningSection() {
  return (
    <section className="py-16 px-6 bg-white border-y border-[#E6E2D8]">
      <div className="max-w-[820px] mx-auto text-center">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full mb-5" style={{ background: "#F1EEE6" }}>
          <EarOff className="w-4.5 h-4.5" style={{ color: "#23345C" }} />
        </div>
        <p className="font-display text-[26px] sm:text-[30px] leading-snug text-[#17181C]">
          The only coach that never interrupts you while you&apos;re speaking.
        </p>
        <p className="mt-4 text-[15px] text-[#6E6C63] leading-relaxed max-w-[560px] mx-auto">
          Most delivery-coaching apps flag mistakes live, mid-sentence — which is exactly when a
          nervous speaker can least afford the extra cognitive load. SpeechMate holds every score
          and correction until you&apos;ve finished, grounded deliberately in Cognitive Load Theory:
          interrupting someone to fix them rarely makes them speak better in the moment.
        </p>
      </div>
    </section>
  );
}
