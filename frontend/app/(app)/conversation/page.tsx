"use client";

// Daily conversation: pick something to talk about, then chat with the AI partner.
// Every session is analysed afterwards (voice, language, body language, confidence).

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Coffee, Globe2, GraduationCap, MessageCircle, Shuffle, Sparkles, Users } from "lucide-react";
import { authService } from "@/services/auth";
import ClayArt from "@/components/three/ClayArt";
import { Button, Card, Field, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";

const SCENARIOS = [
  { icon: MessageCircle, title: "Your week", topic: "Catching up: what happened in your week and what you're looking forward to" },
  { icon: Coffee, title: "Small talk", topic: "Small talk with someone you just met at a café or event" },
  { icon: GraduationCap, title: "Studies & work", topic: "Talking about your studies, your work and your plans after graduating" },
  { icon: Users, title: "Making plans", topic: "Planning a weekend outing with a friend: where to go, when, and what to do" },
  { icon: Globe2, title: "Malaysia", topic: "Telling a visitor about Malaysian food, festivals and places to see" },
  { icon: Sparkles, title: "Share an opinion", topic: "Giving and defending your opinion: is social media good for young people?" },
];

const MEASURED = [
  ["Voice", "pace, fluency, pronunciation, vocal variety, volume"],
  ["Language", "filler words, vocabulary, hedging, grammar tips"],
  ["Body language", "eye contact, posture, gestures, head steadiness"],
  ["Confidence", "expression, response time, overall presence"],
] as const;

export default function ConversationPage() {
  const router = useRouter();
  const [topic, setTopic] = useState(SCENARIOS[0].topic);
  const [custom, setCustom] = useState("");

  const chosen = custom.trim() || topic;
  const start = () => {
    // Sessions are only recorded and analysed when signed in: ask before, not after, the talk
    if (!authService.isSignedIn()) { router.push("/login?next=/conversation"); return; }
    router.push(`/session?mode=Conversation&topic=${encodeURIComponent(chosen)}`);
  };

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto">
      <PageHeader eyebrow="Daily conversation" title="What would you like to talk about?" art={<ClayArt variant="mic" className="h-[260px]" />}>
        Have a relaxed spoken conversation with your AI partner. Nothing is scored while you talk; afterwards
        you get a simple report on how you sounded, the words you used and how you came across on camera.
      </PageHeader>

      <div className="grid lg:grid-cols-[1fr_340px] gap-6 items-start">
        <div className="space-y-5">
          <div className="grid sm:grid-cols-2 gap-3">
            {SCENARIOS.map(({ icon: Icon, title, topic: t }) => {
              const active = !custom.trim() && topic === t;
              return (
                <button key={title} onClick={() => { setTopic(t); setCustom(""); }} aria-pressed={active}
                  className="text-left p-4 rounded-lg flex gap-3 transition-colors hover:border-[var(--line-strong)]"
                  style={{ background: active ? "var(--surface-2)" : "var(--surface)", border: `1px solid ${active ? "var(--accent-ink)" : "var(--line)"}` }}>
                  <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--accent-ink)" }} />
                  <span>
                    <span className="block text-sm font-semibold" style={{ color: "var(--ink)" }}>{title}</span>
                    <span className="block text-xs mt-0.5 leading-relaxed" style={{ color: "var(--muted)" }}>{t}</span>
                  </span>
                </button>
              );
            })}
          </div>
          <Card>
            <Field label="Or your own topic" optional hint="Anything you want to practise talking about.">
              <input className={inputClass} style={inputStyle} value={custom} maxLength={200}
                placeholder="e.g. Explaining my final-year project to my family" onChange={(e) => setCustom(e.target.value)} />
            </Field>
          </Card>
        </div>

        <div className="lg:sticky lg:top-20 space-y-4">
          <Card title="Analysed after you finish">
            <dl className="space-y-2.5">
              {MEASURED.map(([k, v]) => (
                <div key={k}>
                  <dt className="text-sm font-medium" style={{ color: "var(--ink)" }}>{k}</dt>
                  <dd className="text-xs" style={{ color: "var(--muted)" }}>{v}</dd>
                </div>
              ))}
            </dl>
          </Card>
          <Button className="w-full h-12 text-base" onClick={start}>Start conversation</Button>
          <button onClick={() => { setCustom(""); setTopic(SCENARIOS[Math.floor(Math.random() * SCENARIOS.length)].topic); }}
            className="w-full flex items-center justify-center gap-1.5 text-xs font-semibold" style={{ color: "var(--accent-ink)" }}>
            <Shuffle className="w-3.5 h-3.5" /> Surprise me
          </button>
          <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            Tip: 3–5 minutes is enough for a useful report. Speak, pause, and the AI answers. You can also type.
          </p>
        </div>
      </div>
    </div>
  );
}
