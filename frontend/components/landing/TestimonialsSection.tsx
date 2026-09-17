const testimonials = [
  {
    name: "Amirah Zulkifli",
    role: "Computer Science Student, UTP",
    content:
      "SpeechMate helped me prepare for my FYP presentation. After two weeks of practice, my fluency score jumped from 58% to 79%. My supervisor noticed the difference immediately.",
    score: "79%",
    metric: "Fluency",
  },
  {
    name: "Raj Kumar",
    role: "Software Engineer",
    content:
      "I used to avoid speaking in meetings. After a month with SpeechMate's AI Coach, my confidence is completely different. The eye contact feedback was a game changer.",
    score: "91%",
    metric: "Confidence",
  },
  {
    name: "Nurul Aisyah",
    role: "Business Student",
    content:
      "The mock interview mode is incredibly realistic. I practiced over 20 sessions before my internship interviews and got offers from 3 companies. Highly recommend.",
    score: "85%",
    metric: "Pronunciation",
  },
];

export default function TestimonialsSection() {
  return (
    <section id="testimonials" className="py-20 px-6 bg-[#F5F2EB]">
      <div className="max-w-[1280px] mx-auto">
        <div className="text-center mb-12">
          <p className="text-xs font-medium tracking-wide text-[#6E6C63] mb-3">Success stories</p>
          <h2 className="font-display text-[34px] leading-tight text-[#17181C] tracking-tight">
            Real results from real users
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t) => (
            <div
              key={t.name}
              className="bg-white rounded-[12px] p-6 border border-[#E6E2D8]"
            >
              {/* Score */}
              <div className="flex items-baseline gap-1.5 mb-4">
                <span className="text-[#23345C] font-display text-2xl">{t.score}</span>
                <span className="text-[#6E6C63] text-xs">{t.metric}</span>
              </div>

              {/* Quote */}
              <p className="text-[14px] text-[#34343A] leading-relaxed mb-5">
                &ldquo;{t.content}&rdquo;
              </p>

              {/* Author */}
              <div className="flex items-center gap-3 pt-4 border-t border-[#F1EEE6]">
                <div className="w-8 h-8 rounded-full bg-[#23345C] flex items-center justify-center shrink-0">
                  <span className="text-white text-xs font-semibold">
                    {t.name.split(" ").map((n) => n[0]).join("")}
                  </span>
                </div>
                <div>
                  <div className="text-[13px] font-semibold text-[#17181C]">{t.name}</div>
                  <div className="text-[12px] text-[#6E6C63]">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
