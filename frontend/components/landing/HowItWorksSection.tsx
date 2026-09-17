const steps = [
  {
    step: "01",
    title: "Set your goal",
    description:
      "Tell SpeechMate what you want to improve — fluency, pronunciation, presentations, or interview skills.",
  },
  {
    step: "02",
    title: "Practice with AI",
    description:
      "Have natural conversations, run mock interviews, or deliver presentations to your AI coach.",
  },
  {
    step: "03",
    title: "Get real-time feedback",
    description:
      "Receive live scores on fluency, pronunciation, eye contact, posture, and confidence as you speak.",
  },
  {
    step: "04",
    title: "Track your progress",
    description:
      "Watch your communication skills improve over time through detailed analytics and personalized recommendations.",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 px-6 bg-white">
      <div className="max-w-[1280px] mx-auto">
        <div className="text-center mb-12">
          <p className="text-xs font-medium tracking-wide text-[#6E6C63] mb-3">How it works</p>
          <h2 className="font-display text-[34px] leading-tight text-[#17181C] tracking-tight">
            From first word to confident speaker
          </h2>
          <p className="mt-3 text-[16px] text-[#6E6C63] max-w-[480px] mx-auto">
            SpeechMate fits into your schedule. Five minutes a day is enough to start seeing improvement.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, i) => (
            <div key={s.step} className="relative">
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-5 left-[calc(100%_-_24px)] w-12 h-px bg-[#E6E2D8] z-10" />
              )}
              <div className="bg-[#F5F2EB] rounded-[16px] p-6 border border-[#E6E2D8] h-full">
                <div className="text-[28px] font-bold text-[#E6E2D8] mb-3">{s.step}</div>
                <h3 className="text-[15px] font-semibold text-[#17181C] mb-2">{s.title}</h3>
                <p className="text-[13px] text-[#6E6C63] leading-relaxed">{s.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
