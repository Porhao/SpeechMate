import {
  Mic2,
  Eye,
  BarChart3,
  MessageSquare,
  Target,
  TrendingUp,
} from "lucide-react";

const features = [
  {
    icon: Mic2,
    title: "Speech Analysis",
    description:
      "Real-time analysis of fluency, pronunciation, speaking pace, and filler words with AI-powered feedback.",
  },
  {
    icon: Eye,
    title: "Non-Verbal Analysis",
    description:
      "Computer vision evaluates eye contact, facial expressions, posture, and overall presentation confidence.",
  },
  {
    icon: MessageSquare,
    title: "AI Conversations",
    description:
      "Practice natural dialogue, mock interviews, and presentations with an intelligent AI conversation partner.",
  },
  {
    icon: Target,
    title: "Pronunciation Coaching",
    description:
      "Word and sentence drills targeting your specific pronunciation challenges in English and Bahasa Melayu.",
  },
  {
    icon: BarChart3,
    title: "Detailed Assessments",
    description:
      "Comprehensive reports covering speech fluency, stuttering patterns, and communication effectiveness.",
  },
  {
    icon: TrendingUp,
    title: "Progress Tracking",
    description:
      "Long-term trend analytics with charts, milestones, and AI-generated improvement forecasts.",
  },
];

export default function FeaturesSection() {
  return (
    <section id="features" className="py-20 px-6 bg-[#F5F2EB]">
      <div className="max-w-[1280px] mx-auto">
        {/* Header */}
        <div className="max-w-[560px] mb-14">
          <p className="text-xs font-medium tracking-wide text-[#6E6C63] mb-3">Platform features</p>
          <h2 className="font-display text-[34px] leading-tight text-[#17181C] tracking-tight">
            Everything you need to communicate better
          </h2>
          <p className="mt-3 text-[16px] text-[#6E6C63]">
            SpeechMate combines speech AI, computer vision, and personalized coaching in one platform.
          </p>
        </div>

        {/* Feature list — numbered, no icon badges */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-10">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="pt-5" style={{ borderTop: "1px solid #E6E2D8" }}>
                <div className="flex items-center gap-2.5 mb-3">
                  <span className="text-xs font-mono text-[#9B988E]">{String(i + 1).padStart(2, "0")}</span>
                  <Icon className="w-4 h-4 text-[#23345C]" strokeWidth={1.6} />
                </div>
                <h3 className="text-[16px] font-semibold text-[#17181C] mb-1.5">{f.title}</h3>
                <p className="text-[14px] text-[#6E6C63] leading-relaxed">{f.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
