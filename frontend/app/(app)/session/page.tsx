"use client";

import { Suspense, useEffect, useRef, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Mic, MicOff, PhoneOff, Send, Volume2, VolumeX, Shuffle,
  Activity, ChevronUp, ChevronDown, Minus,
  Loader2, Video, VideoOff, Star, Upload, FileText, Briefcase, EarOff,
} from "lucide-react";
import { useSessionStore } from "@/store/useSessionStore";
import { useFeedbackStore } from "@/store/useFeedbackStore";
import { cn } from "@/lib/utils";
import { practiceService } from "@/services/practice";
import { speechService } from "@/services/speech";
import { visionService } from "@/services/vision";
import { analysisService } from "@/services/analysis";
import type { SessionType, GazeTunnelingResult, GazeTunnelingWindow } from "@/types";

// ── Types ─────────────────────────────────────────────────────────────────────
type Message  = { role: "ai" | "user"; text: string; ts: number };
type MpStatus = "idle" | "loading" | "ready" | "error";
type OrbState = "idle" | "thinking" | "speaking" | "listening";

// ── Random topics (RandomTopicGen-inspired) ───────────────────────────────────
const RANDOM_TOPICS = [
  "What technology will change the world most in the next decade?",
  "Should social media platforms be regulated like public utilities?",
  "What makes a great leader in today's fast-moving world?",
  "How has remote work changed the way we think about productivity?",
  "What role should AI play in education — tool or teacher?",
  "Is it possible to balance ambition and mental wellbeing? How?",
  "What's the most underrated skill in the modern workplace?",
  "How do you think about failure — obstacle or teacher?",
  "What habit has made the biggest positive impact in your life?",
  "If you could solve one global problem, what would it be and why?",
  "What does success look like to you in five years?",
  "How do you communicate a complex idea to someone unfamiliar with it?",
];

// ── Pronunciation curriculum ──────────────────────────────────────────────────
const PRONUNCIATION_PHRASES = [
  { phrase: "The thorough theory through the theatre",              focus: "TH sounds",         hint: "Tongue between teeth for every 'th'" },
  { phrase: "I would like to present my research findings today",   focus: "Formal delivery",   hint: "Stress 'present' and 'findings'" },
  { phrase: "The preliminary presentation requires preparation",    focus: "P consonants",      hint: "Pop each P — don't swallow them" },
  { phrase: "Statistical significance supports the hypothesis",     focus: "S and H clarity",   hint: "Slow down and articulate every syllable" },
  { phrase: "Malaysian English has unique intonation patterns",     focus: "Natural intonation",hint: "Rising intonation on key words" },
  { phrase: "Could you please clarify that point for the audience", focus: "Question tone",     hint: "Natural rising tone at the end" },
  { phrase: "I am confident in my ability to lead this initiative", focus: "Confidence & pace", hint: "Slow, deliberate, authoritative delivery" },
  { phrase: "Technology drives innovation in modern communication", focus: "T and N clarity",   hint: "Crisp T at start, strong final N" },
];

// ── Mode content ──────────────────────────────────────────────────────────────
const MODE_PROMPTS: Record<string, string[]> = {
  Conversation: [
    "Let's have a natural conversation. Tell me — what's been the most interesting thing in your week?",
    "What's one skill or hobby you've been trying to develop lately?",
    "If you could have dinner with anyone in history, who would it be and why?",
    "What's something you recently changed your mind about? What shifted your thinking?",
  ],
  Interview: [
    "Great to meet you. Could you start by walking me through your background and what you're studying?",
    "Tell me about your greatest strength — can you give a concrete example of it in action?",
    "Describe a challenge you faced and exactly how you overcame it.",
    "Where do you see yourself in five years, and why does this role fit that path?",
  ],
  Presentation: [
    "Welcome to your presentation session. Begin with your opening — hook the audience immediately.",
    "Strong start. Now develop your first main argument with supporting evidence.",
    "Good. Use a clear signpost transition to move to your next point.",
    "Now close — summarise your key points and end with a memorable call to action.",
  ],
  Pronunciation: [
    "Welcome to pronunciation training. I'll say each phrase first, then you repeat after me.",
  ],
};

const MODE_ACKS: Record<string, string[]> = {
  Conversation: [
    "That's a really interesting perspective! ",
    "I love that — tell me more about it. ",
    "Ha, that's actually fascinating. ",
    "What a great point. Here's my follow-up: ",
  ],
  Interview: [
    "Thank you — that showed real depth. Now, ",
    "Strong answer — I appreciated the specificity. My next question: ",
    "Excellent. You articulated that very clearly. Let me follow up: ",
    "Really insightful. Here's what I want to explore next: ",
  ],
  Presentation: [
    "Good progress — keep that energy. Now, ",
    "Well delivered. Moving to the next coaching point: ",
    "That transition was clean. Continue with: ",
  ],
  Pronunciation: [],
};

const CHECKIN_MESSAGES = [
  "Just checking in — are you still there? Take your time, no rush at all.",
  "It looks like you've gone quiet. Everything okay? We can continue whenever you're ready.",
  "No pressure — would you like me to repeat the question, or shall we try a different topic?",
];

// ── Helpers ───────────────────────────────────────────────────────────────────
const BACKCHANNEL_TEXTS = ["Mm-hmm.", "I see.", "Right.", "Yeah.", "Go on.", "Interesting."];
const FILLER_WORDS = new Set([
  "um","uh","er","ah","hmm","like","basically","literally","actually",
  "you","know","mean","right","okay","so","well","lah","lor","meh","kan","wah","aiya",
]);

const clamp  = (v: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, v));
const ema    = (prev: number, next: number, a = 0.2) => prev * (1 - a) + next * a;
type Lm = { x: number; y: number; z: number; visibility?: number };

function computeEye(lms: Lm[]): number {
  if (!lms || lms.length < 455) return 50;
  const nose = lms[4], le = lms[234], re = lms[454];
  const xDev = Math.abs(nose.x - 0.5) * 2, yDev = Math.abs(nose.y - 0.42) * 2;
  const rot  = Math.min(1, Math.abs(le.z - re.z) * 4);
  return clamp(Math.round((1 - clamp(xDev)) * 35 + (1 - clamp(yDev)) * 20 + (1 - rot) * 45));
}

function computePosture(lms: Lm[]): number {
  if (!lms || lms.length < 25) return 50;
  const n = lms[0], ls = lms[11], rs = lms[12];
  if ((ls.visibility ?? 0) < 0.3 || (rs.visibility ?? 0) < 0.3) return 50;
  return clamp(Math.round(
    Math.max(0, 1 - Math.abs(ls.y - rs.y) * 10) * 40 +
    Math.max(0, 1 - Math.abs(n.x - (ls.x + rs.x) / 2) * 8) * 35 +
    (n.y < (ls.y + rs.y) / 2 - 0.02 ? 25 : n.y < (ls.y + rs.y) / 2 ? 15 : 5),
  ));
}

// ── Gaze Tunneling ───────────────────────────────────────────────────────────
// Fuses two signals every competitor reports as separate cards: where the
// speaker was looking (eye-contact samples, ~2/sec) and when their speech
// broke down (filler words + immediate word-repetitions, timestamped as
// they're recognised). Bucketed into fixed windows, then a real Pearson
// correlation between gaze aversion and disfluency density — not a canned
// number, actual arithmetic over what this session's tracking produced.
function computeGazeTunneling(
  gazeSamples: { t: number; eye: number }[],
  disfluencyEvents: { t: number }[],
  windowSeconds = 5,
): GazeTunnelingResult {
  const totalEvents = disfluencyEvents.length;
  if (gazeSamples.length < 4) {
    return { windows: [], windowSeconds, correlation: 0, coOccurrencePct: 0, totalEvents, label: "Not enough data" };
  }

  const duration = gazeSamples[gazeSamples.length - 1].t;
  const numWindows = Math.max(1, Math.ceil(duration / windowSeconds));
  const windows: GazeTunnelingWindow[] = [];
  for (let i = 0; i < numWindows; i++) {
    const start = i * windowSeconds, end = start + windowSeconds;
    const inWindow = gazeSamples.filter((s) => s.t >= start && s.t < end);
    const avgEye = inWindow.length
      ? inWindow.reduce((sum, s) => sum + s.eye, 0) / inWindow.length
      : windows[windows.length - 1]?.eyeContact ?? 50;
    const disCount = disfluencyEvents.filter((e) => e.t >= start && e.t < end).length;
    windows.push({ t: start, eyeContact: Math.round(avgEye), disfluencyCount: disCount });
  }

  const n = windows.length;
  if (n < 3 || totalEvents === 0) {
    return { windows, windowSeconds, correlation: 0, coOccurrencePct: 0, totalEvents, label: "Not enough data" };
  }

  // Pearson correlation between gaze aversion (100 − eye contact) and disfluency count per window.
  const xs = windows.map((w) => 100 - w.eyeContact);
  const ys = windows.map((w) => w.disfluencyCount);
  const meanX = xs.reduce((a, b) => a + b, 0) / n;
  const meanY = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, denX = 0, denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX, dy = ys[i] - meanY;
    num += dx * dy; denX += dx * dx; denY += dy * dy;
  }
  const correlation = denX > 0 && denY > 0 ? num / Math.sqrt(denX * denY) : 0;

  // Co-occurrence: % of disfluency events that fell in a window where eye
  // contact dipped meaningfully below this session's own average.
  const sessionAvgEye = windows.reduce((a, w) => a + w.eyeContact, 0) / n;
  const dipThreshold = sessionAvgEye - 8;
  let coOccur = 0;
  disfluencyEvents.forEach((e) => {
    const win = windows.find((w) => e.t >= w.t && e.t < w.t + windowSeconds);
    if (win && win.eyeContact < dipThreshold) coOccur++;
  });
  const coOccurrencePct = Math.round((coOccur / totalEvents) * 100);

  const label: GazeTunnelingResult["label"] =
    correlation > 0.4 ? "Strong link" : correlation > 0.15 ? "Some link" : "No clear link";

  return {
    windows, windowSeconds,
    correlation: Math.round(correlation * 100) / 100,
    coOccurrencePct, totalEvents, label,
  };
}

// ── Mood inference ────────────────────────────────────────────────────────────
// Rule-based, not a trained classifier — reads MediaPipe's ARKit-style face
// blendshape coefficients (52 facial-muscle activation scores from the same
// FaceLandmarker already running for the mesh overlay) and scores five
// presentation-relevant states against each other. Good enough to be an
// honest, real-time signal without pretending to be a full emotion model.
type Blendshape = { categoryName: string; score: number };

const MOOD_STATES = {
  Engaged:     { color: "#5C729B" },
  Confident:   { color: "#3F6B4C" },
  Enthusiastic:{ color: "#8A5A22" },
  Tense:       { color: "#8C3B32" },
  Uncertain:   { color: "#5A5470" },
} as const;
type MoodLabel = keyof typeof MOOD_STATES;

function inferMood(cats: Blendshape[]): { label: MoodLabel; score: number } {
  const g = (name: string) => cats.find((c) => c.categoryName === name)?.score ?? 0;
  const smile   = (g("mouthSmileLeft") + g("mouthSmileRight")) / 2;
  const browUp  = (g("browOuterUpLeft") + g("browOuterUpRight") + g("browInnerUp")) / 3;
  const browDn  = (g("browDownLeft") + g("browDownRight")) / 2;
  const eyeWide = (g("eyeWideLeft") + g("eyeWideRight")) / 2;
  const squint  = (g("eyeSquintLeft") + g("eyeSquintRight")) / 2;
  const press   = (g("mouthPressLeft") + g("mouthPressRight")) / 2;
  const jawOpen = g("jawOpen");
  const frown   = (g("mouthFrownLeft") + g("mouthFrownRight")) / 2;

  const scores: Record<MoodLabel, number> = {
    Enthusiastic: smile * 0.7 + browUp * 0.3,
    Confident:    (1 - press) * 0.35 + (1 - squint) * 0.25 + smile * 0.2 + (1 - browDn) * 0.2,
    Tense:        browDn * 0.45 + press * 0.35 + frown * 0.2,
    Uncertain:    eyeWide * 0.4 + browUp * 0.3 + jawOpen * 0.3,
    Engaged:      0.32, // steady baseline — wins when nothing else is strongly expressed
  };

  const [label, raw] = (Object.entries(scores) as [MoodLabel, number][])
    .sort((a, b) => b[1] - a[1])[0];
  return { label, score: clamp(Math.round(30 + raw * 90)) };
}

function computeFluency(wc: number, fc: number, elapsed: number) {
  if (elapsed < 2 || wc < 3) return { score: 70, wpm: 0 };
  const wpm = Math.round((wc / elapsed) * 60);
  const ws  = wpm < 60 ? 30 : wpm < 120 ? 30 + (wpm - 60) : wpm < 160 ? 90 + (wpm - 120) * 0.25
    : wpm < 200 ? 100 - (wpm - 160) * 1.5 : Math.max(30, 100 - (wpm - 160) * 2);
  const fs  = Math.max(0, 100 - (fc / Math.max(wc, 1)) * 300);
  return { score: clamp(Math.round(ws * 0.6 + fs * 0.4)), wpm };
}

function scorePhrase(spoken: string, target: string) {
  const n = (s: string) => s.toLowerCase().replace(/[^a-z\s]/g, "").split(/\s+/).filter(Boolean);
  const sw = n(spoken), tw = n(target);
  const hits = tw.filter((w) => sw.includes(w)).length;
  const score = clamp(Math.round((hits / tw.length) * 100));
  const feedback =
    score >= 90 ? "Excellent! Near-perfect pronunciation." :
    score >= 75 ? "Very good — just a couple of minor differences." :
    score >= 55 ? "Good attempt. Articulate each word more clearly." :
    score >= 35 ? "Keep practising. Try speaking more slowly." :
                  "Let's try again — one word at a time.";
  return { score, feedback };
}

function mockSlideOutline(fileName: string): string[] {
  const topic = fileName.replace(/\.(pdf|pptx?|key|odp)$/i, "").replace(/[-_]/g, " ");
  return [
    `Opening (Slides 1–2): Hook the audience on "${topic}". State your objectives.`,
    `Context (Slides 3–4): Background and key definitions. Establish credibility with data.`,
    `Core Arguments (Slides 5–8): 3 key points with evidence. Clear signpost transitions.`,
    `Discussion (Slides 9–10): Implications and connection to your stated goals.`,
    `Conclusion (Slides 11–12): Summarise takeaways. Close memorably.`,
  ];
}

// ── AI Orb (Sesame-inspired) ──────────────────────────────────────────────────
// `level` (0–1) is the user's live mic amplitude from a real AnalyserNode —
// while listening, the orb visibly breathes with the user's actual voice
// instead of running a generic canned loop.
function AIOrb({ state, level = 0 }: { state: OrbState; level?: number }) {
  const glow = {
    idle:      "0 0 40px rgba(92,114,155,0.35), 0 0 80px rgba(92,114,155,0.1), inset 0 0 30px rgba(255,255,255,0.04)",
    thinking:  "0 0 40px rgba(156,106,40,0.5), 0 0 80px rgba(156,106,40,0.2)",
    speaking:  "0 0 60px rgba(92,114,155,0.7), 0 0 120px rgba(99,102,241,0.35), inset 0 0 40px rgba(255,255,255,0.08)",
    listening: "0 0 50px rgba(77,122,89,0.55), 0 0 100px rgba(77,122,89,0.2)",
  }[state];

  const grad = {
    idle:      "radial-gradient(circle at 35% 30%, #93c5fd 0%, #3b82f6 35%, #1e40af 65%, #0f172a 100%)",
    thinking:  "radial-gradient(circle at 35% 30%, #fde68a 0%, #f59e0b 35%, #92400e 65%, #0f172a 100%)",
    speaking:  "radial-gradient(circle at 35% 30%, #a5b4fc 0%, #6366f1 30%, #3b82f6 55%, #1e3a8a 75%, #0f172a 100%)",
    listening: "radial-gradient(circle at 35% 30%, #86efac 0%, #22c55e 35%, #15803d 65%, #0f172a 100%)",
  }[state];

  return (
    <div className="relative flex items-center justify-center select-none" style={{ width: 200, height: 200 }}>

      {/* Outermost ambient glow ring */}
      <div className="absolute rounded-full pointer-events-none"
        style={{
          inset: -20,
          background: state === "listening"
            ? "radial-gradient(circle, rgba(77,122,89,0.08) 0%, transparent 70%)"
            : "radial-gradient(circle, rgba(92,114,155,0.07) 0%, transparent 70%)",
        }} />

      {/* Ripple rings — speaking */}
      {state === "speaking" && [0, 1, 2].map((i) => (
        <div key={i} className="absolute rounded-full border pointer-events-none"
          style={{
            inset: -(i + 1) * 18,
            borderColor: `rgba(99,102,241,${0.25 - i * 0.07})`,
            animation: `ping 1.6s cubic-bezier(0,0,0.2,1) ${i * 0.45}s infinite`,
          }} />
      ))}

      {/* Listening pulse ring */}
      {state === "listening" && (
        <div className="absolute rounded-full border-2 border-green-400/40 pointer-events-none animate-pulse"
          style={{ inset: -12 }} />
      )}

      {/* Thinking spin ring */}
      {state === "thinking" && (
        <div className="absolute rounded-full pointer-events-none"
          style={{
            inset: -6,
            border: "2px solid transparent",
            borderTopColor: "rgba(156,106,40,0.7)",
            borderRightColor: "rgba(156,106,40,0.3)",
            animation: "spin 1.4s linear infinite",
          }} />
      )}

      {/* Orb body */}
      <div className="relative rounded-full overflow-hidden"
        style={{
          width: 200, height: 200,
          background: grad,
          boxShadow: state === "listening" ? `${glow}, 0 0 ${40 + level * 60}px rgba(77,122,89,${0.25 + level * 0.35})` : glow,
          transform: state === "listening" ? `scale(${1 + Math.min(level, 1) * 0.09})` : undefined,
          transition: state === "listening"
            ? "transform 0.1s ease-out, box-shadow 0.1s ease-out, background 0.6s ease"
            : "background 0.6s ease, box-shadow 0.6s ease",
          animation: state === "idle" ? "orb-breathe 4s ease-in-out infinite"
                   : state === "speaking" ? "orb-speak-pulse 1.2s ease-in-out infinite"
                   : undefined,
        }}>
        {/* Specular highlight */}
        <div className="absolute rounded-full bg-white/20 blur-[6px]"
          style={{ width: "42%", height: "28%", top: "14%", left: "18%" }} />
        {/* Inner depth */}
        <div className="absolute rounded-full bg-white/5 blur-xl"
          style={{ inset: "20%" }} />
        {/* Bottom shadow */}
        <div className="absolute bottom-0 left-0 right-0 h-1/3 rounded-b-full"
          style={{ background: "linear-gradient(to top, rgba(0,0,0,0.4), transparent)" }} />
      </div>

      {/* Waveform bars below orb — speaking */}
      {state === "speaking" && (
        <div className="absolute flex gap-[3px] items-end" style={{ bottom: -32, left: "50%", transform: "translateX(-50%)" }}>
          {[3, 5, 8, 12, 9, 6, 10, 7, 4, 8, 5, 3].map((h, i) => (
            <div key={i} className="rounded-full"
              style={{
                width: 3,
                height: h * 2,
                background: "rgba(99,102,241,0.75)",
                animation: `waveform-bar 0.7s ease-in-out ${i * 0.07}s infinite alternate`,
              }} />
          ))}
        </div>
      )}

      {/* Mic bars below orb — listening, driven by real mic amplitude.
          Each bar samples the same level with a different responsiveness
          curve so the row doesn't move as one flat block. */}
      {state === "listening" && (
        <div className="absolute flex gap-[3px] items-end" style={{ bottom: -32, left: "50%", transform: "translateX(-50%)", height: 24 }}>
          {[0.5, 0.75, 1, 1.3, 1, 0.75, 1, 1.3, 1, 0.75, 0.5].map((mult, i) => {
            const h = Math.max(4, Math.min(24, 4 + level * 60 * mult));
            return (
              <div key={i} className="rounded-full"
                style={{
                  width: 3,
                  height: h,
                  background: "rgba(77,122,89,0.8)",
                  transition: "height 0.09s ease-out",
                }} />
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Header mic pulse — tiny live waveform next to the session timer ──────────
function HeaderPulse({ level, active, color = "#5C729B" }: { level: number; active: boolean; color?: string }) {
  return (
    <div className="flex items-end gap-[2px]" style={{ height: 13 }}>
      {[0.6, 1, 0.7, 1.2, 0.7].map((mult, i) => {
        const h = active ? Math.max(3, Math.min(13, 3 + level * 34 * mult)) : 3;
        return (
          <div key={i} className="rounded-full" style={{ width: 2, height: h, background: color, transition: "height 0.1s ease-out" }} />
        );
      })}
    </div>
  );
}

// ── Interviewer Avatar ────────────────────────────────────────────────────────
function InterviewerAvatar({ state }: { state: OrbState }) {
  const s = {
    idle:      { border: "rgba(35,52,92,0.32)", glow: "rgba(35,52,92,0.18)", text: "Ready",       tc: "rgba(255,255,255,0.38)" },
    speaking:  { border: "rgba(35,52,92,0.85)", glow: "rgba(35,52,92,0.48)", text: "Speaking…",   tc: "#60a5fa" },
    listening: { border: "rgba(77,122,89,0.72)",  glow: "rgba(77,122,89,0.32)",  text: "Listening…",  tc: "#4ade80" },
    thinking:  { border: "rgba(156,106,40,0.72)", glow: "rgba(156,106,40,0.32)", text: "Thinking…",   tc: "#fbbf24" },
  }[state];

  return (
    <div
      className="relative overflow-hidden flex-shrink-0"
      style={{
        width: 240, height: 288, borderRadius: 22,
        background: "linear-gradient(165deg, #0e0c2a 0%, #06091a 100%)",
        border: `2px solid ${s.border}`,
        boxShadow: `0 0 36px ${s.glow}, 0 8px 32px rgba(0,0,0,0.7)`,
        transition: "border-color 0.65s ease, box-shadow 0.65s ease",
      }}
    >
      {/* Ambient room glow */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: `radial-gradient(ellipse 120% 60% at 50% 0%, ${s.glow.replace(/[\d.]+\)$/, "0.14)")} 0%, transparent 60%)`,
        transition: "background 0.65s ease",
      }} />

      {/* SVG figure */}
      <svg viewBox="0 0 240 288" className="w-full h-full absolute inset-0">
        <defs>
          <radialGradient id="ivSkin" cx="38%" cy="30%" r="65%">
            <stop offset="0%" stopColor="#d4a97e" />
            <stop offset="100%" stopColor="#b88555" />
          </radialGradient>
          <radialGradient id="ivSuit" cx="50%" cy="0%" r="100%">
            <stop offset="0%" stopColor="#252250" />
            <stop offset="100%" stopColor="#16143a" />
          </radialGradient>
        </defs>

        {/* Suit body */}
        <path d="M 0 288 L 28 220 C 52 208 78 200 96 208 L 120 230 L 144 208 C 162 200 188 208 212 220 L 240 288 Z" fill="url(#ivSuit)" />
        {/* Shirt */}
        <path d="M 96 208 L 120 230 L 120 288 L 88 288 Z" fill="white" opacity="0.9" />
        <path d="M 120 230 L 144 208 L 152 288 L 120 288 Z" fill="white" opacity="0.88" />
        {/* Left lapel */}
        <path d="M 28 220 C 52 208 78 200 96 208 L 120 230 L 88 258 Z" fill="#1e1c46" />
        {/* Right lapel */}
        <path d="M 212 220 C 188 208 162 200 144 208 L 120 230 L 152 258 Z" fill="#1e1c46" />
        {/* Tie */}
        <path d="M 116 234 L 124 234 L 127 278 L 120 287 L 113 278 Z" fill="#7c3aed" />
        <path d="M 116 234 L 124 234 L 120 244 Z" fill="#5b21b6" />

        {/* Neck */}
        <rect x="108" y="178" width="24" height="38" rx="5" fill="url(#ivSkin)" />

        {/* Head */}
        <ellipse cx="120" cy="124" rx="54" ry="60" fill="url(#ivSkin)" />
        {/* Ears */}
        <ellipse cx="66" cy="126" rx="8" ry="11" fill="url(#ivSkin)" />
        <ellipse cx="174" cy="126" rx="8" ry="11" fill="url(#ivSkin)" />

        {/* Hair */}
        <path d="M 66 113 C 68 72 78 58 97 52 C 109 48 120 47 120 47 C 120 47 131 48 143 52 C 162 58 172 72 174 113 C 166 83 154 70 140 65 C 132 62 125 61 120 61 C 115 61 108 62 100 65 C 86 70 74 83 66 113 Z" fill="#1a1035" />
        <path d="M 66 113 C 64 123 65 135 67 142 C 68 135 69 126 69 118 Z" fill="#1a1035" />
        <path d="M 174 113 C 176 123 175 135 173 142 C 172 135 171 126 171 118 Z" fill="#1a1035" />

        {/* Left eye */}
        <ellipse cx="103" cy="117" rx="11" ry="11.5" fill="white" />
        <ellipse cx="104" cy="118" rx="7" ry="7.5" fill="#2a1d5a" />
        <ellipse cx="105" cy="118" rx="4" ry="4.5" fill="#7c3aed" />
        <ellipse cx="107" cy="115" rx="1.5" ry="1.5" fill="white" />
        {/* Right eye */}
        <ellipse cx="137" cy="117" rx="11" ry="11.5" fill="white" />
        <ellipse cx="136" cy="118" rx="7" ry="7.5" fill="#2a1d5a" />
        <ellipse cx="135" cy="118" rx="4" ry="4.5" fill="#7c3aed" />
        <ellipse cx="137" cy="115" rx="1.5" ry="1.5" fill="white" />

        {/* Eyebrows */}
        <path d="M 92 103 C 96 99 104 98 110 100" stroke="#2a1d5a" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M 130 100 C 136 98 144 99 148 103" stroke="#2a1d5a" strokeWidth="2.5" fill="none" strokeLinecap="round" />

        {/* Nose */}
        <path d="M 120 126 L 116 139 C 117 142 123 142 124 139 Z" fill="rgba(0,0,0,0.07)" />

        {/* Mouth — state-based */}
        {state === "speaking" ? (
          <ellipse cx="120" cy="156" rx="10" ry="5.5" fill="#8b5c3a" />
        ) : state === "thinking" ? (
          <path d="M 112 154 Q 120 151 128 154" stroke="#8b5c3a" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        ) : (
          <path d="M 111 153 Q 120 160 129 153" stroke="#8b5c3a" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        )}

        {/* Cheek warmth */}
        <ellipse cx="88" cy="136" rx="14" ry="9" fill="rgba(220,100,80,0.05)" />
        <ellipse cx="152" cy="136" rx="14" ry="9" fill="rgba(220,100,80,0.05)" />
      </svg>

      {/* Speaking waveform */}
      {state === "speaking" && (
        <div className="absolute bottom-[60px] left-1/2 -translate-x-1/2 flex items-end gap-[2px]">
          {[4, 7, 11, 8, 14, 8, 11, 7, 4].map((h, i) => (
            <span key={i} style={{
              display: "block", width: 3, height: h, background: "#60a5fa", borderRadius: 2,
              animation: `waveform-bar 0.55s ease-in-out ${i * 65}ms infinite`,
            }} />
          ))}
        </div>
      )}

      {/* Thinking dots */}
      {state === "thinking" && (
        <div className="absolute bottom-[60px] left-1/2 -translate-x-1/2 flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 rounded-full animate-bounce"
              style={{ background: "#fbbf24", animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      )}

      {/* Listening ripple */}
      {state === "listening" && (
        <div className="absolute bottom-[62px] right-5 w-3 h-3 rounded-full"
          style={{ background: "#4ade80", boxShadow: "0 0 8px rgba(74,222,128,0.7)", animation: "ping 1.2s cubic-bezier(0,0,0.2,1) infinite" }} />
      )}

      {/* Name plate */}
      <div
        className="absolute bottom-0 left-0 right-0 px-4 py-2.5 flex items-center justify-between"
        style={{ background: "linear-gradient(0deg, rgba(6,9,24,0.96) 0%, transparent 100%)" }}
      >
        <div>
          <p className="text-white text-xs font-bold">Alex Chen</p>
          <p className="text-[10px] transition-colors duration-500" style={{ color: s.tc }}>{s.text}</p>
        </div>
        <span className="text-[9px] font-bold px-2 py-0.5 rounded-md"
          style={{ background: "rgba(35,52,92,0.22)", color: "#93c5fd", border: "1px solid rgba(35,52,92,0.35)" }}>
          AI
        </span>
      </div>
    </div>
  );
}

// ── Metric pill ───────────────────────────────────────────────────────────────
function MetricPill({ label, value, prev, color }: {
  label: string; value: number; prev: number; color: string;
}) {
  const diff = value - prev;
  return (
    <div className="flex items-center gap-2.5 flex-1 min-w-0 px-3 sm:px-4 py-3"
      style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1 mb-1">
          <span className="text-[10px] text-white/40 font-semibold uppercase tracking-wider truncate">{label}</span>
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <span className="text-sm font-bold" style={{ color }}>{Math.round(value)}</span>
            {diff > 0.5 ? <ChevronUp className="w-3 h-3 text-green-400" />
              : diff < -0.5 ? <ChevronDown className="w-3 h-3 text-red-400" />
              : <Minus className="w-3 h-3 text-white/20" />}
          </div>
        </div>
        <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
          <div className="h-full rounded-full transition-all duration-700"
            style={{ width: `${value}%`, background: `linear-gradient(90deg, ${color}80, ${color})` }} />
        </div>
      </div>
    </div>
  );
}

// ── Session ───────────────────────────────────────────────────────────────────
function SessionContent() {
  const searchParams = useSearchParams();
  const router       = useRouter();
  const mode         = (searchParams.get("mode") ?? "Conversation") as string;

  const { isRecording, isCameraOn, duration, setRecording, setCameraOn, incrementDuration, resetDuration } = useSessionStore();
  const {
    liveFeedback, updateLiveFeedback, transcript, appendTranscript, reset,
    setSpeechAnalysis, setVisionAnalysis, setAIFeedback, setFullAnalysis, setGazeTunneling,
  } = useFeedbackStore();

  // ── State ─────────────────────────────────────────────────────────────────
  const [sessionStarted, setSessionStarted] = useState(false);
  const [messages,       setMessages]       = useState<Message[]>([]);
  const [input,          setInput]          = useState("");
  const [aiTyping,       setAiTyping]       = useState(false);
  const [aiSpeaking,     setAiSpeaking]     = useState(false);
  const [promptIndex,    setPromptIndex]    = useState(0);
  const [prevFeedback,   setPrevFeedback]   = useState({ ...liveFeedback });
  const [isEnding,       setIsEnding]       = useState(false);
  const [mpStatus,       setMpStatus]       = useState<MpStatus>("idle");
  const [faceDetected,   setFaceDetected]   = useState(false);
  const [poseDetected,   setPoseDetected]   = useState(false);
  const [mood,           setMood]           = useState<{ label: MoodLabel; score: number } | null>(null);
  const [speechActive,   setSpeechActive]   = useState(false);
  const [interimText,    setInterimText]    = useState("");
  const [wpm,            setWpm]            = useState(0);
  const [, setFillerCount]    = useState(0);
  const [voiceEnabled,   setVoiceEnabled]   = useState(true);
  const [currentTopic,   setCurrentTopic]   = useState(RANDOM_TOPICS[0]);

  // Pronunciation
  const [pronounceIndex,    setPronounceIndex]    = useState(0);
  const [pronounceScore,    setPronounceScore]    = useState<number | null>(null);
  const [pronounceFeedback, setPronunceFeedback]  = useState("");
  const [waitingAttempt,    setWaitingAttempt]    = useState(false);

  // Presentation
  const [slideFile,     setSlideFile]     = useState<File | null>(null);
  const [slideAnalyzed, setSlideAnalyzed] = useState(false);
  const [slideOutline,  setSlideOutline]  = useState<string[]>([]);
  const [analyzing,     setAnalyzing]     = useState(false);
  const slideInputRef = useRef<HTMLInputElement>(null);

  // ── DOM refs ─────────────────────────────────────────────────────────────
  const videoRef   = useRef<HTMLVideoElement>(null);
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const streamRef  = useRef<MediaStream | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const animRef    = useRef<number>(0);
  const recognRef  = useRef<any>(null);
  const mpRef      = useRef<any>(null);
  const mediaRecorderRef    = useRef<MediaRecorder | null>(null);
  const recordedChunksRef   = useRef<Blob[]>([]);
  const backendSessionIdRef = useRef<string | null>(null);

  // Live audio metering — real mic amplitude driving the orb + waveform,
  // not a canned animation. audioLevelRef is read every frame by anything
  // that draws imperatively (waveform bars); audioLevel (state) is a
  // throttled ~12Hz copy for React-rendered elements like the orb's scale.
  const audioCtxRef   = useRef<AudioContext | null>(null);
  const analyserRef   = useRef<AnalyserNode | null>(null);
  const audioLevelRef = useRef(0);
  const audioMeterRafRef = useRef<number>(0);
  const [audioLevel, setAudioLevel] = useState(0);

  // ── Value refs ────────────────────────────────────────────────────────────
  const activeRef           = useRef(false);
  const aiTypingRef         = useRef(false);
  const aiSpeakingRef       = useRef(false);
  const voiceEnabledRef     = useRef(true);
  const isRecordingRef      = useRef(false);
  const modeRef             = useRef(mode);
  const eyeContactRef       = useRef(50);
  const postureRef          = useRef(50);
  const moodRef             = useRef<{ label: MoodLabel; score: number } | null>(null);
  const moodBoxRef          = useRef<{ x: number; y: number; w: number; h: number } | null>(null);
  const pronounceRef        = useRef(72);
  const wordListRef         = useRef<string[]>([]);
  const fillerCntRef        = useRef(0);
  const startTimeRef        = useRef(0);
  const lastUpdateRef       = useRef(0);
  const lastPrevRef         = useRef(0);
  const lastTsRef           = useRef(0);
  const lastSpeechTimeRef   = useRef(0);
  const checkinAskedRef     = useRef(false);
  const silenceCheckRef     = useRef<ReturnType<typeof setInterval> | null>(null);
  const startSpeechRef      = useRef<() => void>(() => {});
  const promptIndexRef      = useRef(0);
  const pendingUserSpeechRef = useRef("");
  const autoReplyTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const triggerAIReplyRef   = useRef<(t: string) => void | Promise<void>>(() => {});

  // Gaze Tunneling — raw samples collected live, fused into one metric at
  // session end (see computeGazeTunneling). gazeSamplesRef is eye-contact
  // score sampled every ~500ms alongside the rest of live feedback;
  // disfluencyEventsRef is timestamped the instant a filler word or an
  // immediate word-repetition is recognised in speech.
  const gazeSamplesRef      = useRef<{ t: number; eye: number }[]>([]);
  const disfluencyEventsRef = useRef<{ t: number }[]>([]);
  const lastWordRef         = useRef("");

  // Pronunciation refs
  const pronounceTargetRef  = useRef(PRONUNCIATION_PHRASES[0].phrase);
  const pronounceIndexRef   = useRef(0);
  const pronounceAttemptRef = useRef<(s: string) => void>(() => {});

  // Backchannel refs
  const backchannelUrlsRef  = useRef<string[]>([]);
  const lastBackchannelRef  = useRef(0);
  const backchannelTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const backchannelAudioRef = useRef<HTMLAudioElement | null>(null);

  // Audio ref (main TTS)
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Track conversation history for real AI calls
  const messagesRef     = useRef<Message[]>([]);
  const currentTopicRef = useRef(RANDOM_TOPICS[0]);

  // ── Sync refs ─────────────────────────────────────────────────────────────
  useEffect(() => { aiTypingRef.current      = aiTyping; },       [aiTyping]);
  useEffect(() => { aiSpeakingRef.current    = aiSpeaking; },     [aiSpeaking]);
  useEffect(() => { voiceEnabledRef.current  = voiceEnabled; },   [voiceEnabled]);
  useEffect(() => { isRecordingRef.current   = isRecording; },    [isRecording]);
  useEffect(() => { modeRef.current          = mode; },           [mode]);
  useEffect(() => { promptIndexRef.current   = promptIndex; },    [promptIndex]);
  useEffect(() => { messagesRef.current      = messages; },       [messages]);
  useEffect(() => { currentTopicRef.current  = currentTopic; },   [currentTopic]);

  // ── TFLite log suppression ────────────────────────────────────────────────
  useEffect(() => {
    const orig = console.error.bind(console);
    console.error = (...a: unknown[]) => {
      const s = String(a[0] ?? "");
      if (s.includes("TensorFlow Lite") || s.includes("XNNPACK") || s.startsWith("INFO:")) return;
      orig(...a);
    };
    return () => { console.error = orig; };
  }, []);

  // ── TTS (OpenAI via backend) ──────────────────────────────────────────────
  const speakText = useCallback((text: string, onEnd?: () => void) => {
    if (!voiceEnabledRef.current) { onEnd?.(); return; }
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; audioRef.current = null; }

    setAiSpeaking(true); aiSpeakingRef.current = true;
    if (recognRef.current) { try { recognRef.current.stop(); } catch { /* ok */ } }

    const finish = () => {
      setAiSpeaking(false); aiSpeakingRef.current = false;
      onEnd?.();
      if (activeRef.current && isRecordingRef.current)
        setTimeout(() => startSpeechRef.current(), 350);
    };

    fetch("/api/v1/tts/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 2000), voice: "nova" }),
    })
      .then((r) => { if (!r.ok) throw new Error(`TTS ${r.status}`); return r.blob(); })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => { URL.revokeObjectURL(url); finish(); };
        audio.onerror = () => { URL.revokeObjectURL(url); finish(); };
        audio.play().catch(finish);
      })
      .catch(() => {
        // Browser fallback
        const synth = window.speechSynthesis; synth.cancel();
        const utt = new SpeechSynthesisUtterance(text);
        const v = synth.getVoices().find((v) => v.lang.startsWith("en")) ?? null;
        if (v) utt.voice = v; utt.rate = 0.9;
        utt.onend = finish; utt.onerror = finish; synth.speak(utt);
      });
  }, []);

  // ── Auto-reply after user speech (real OpenAI chat) ─────────────────────
  const triggerAIReply = useCallback(async (spokenText: string) => {
    if (!activeRef.current || aiTypingRef.current || aiSpeakingRef.current) return;
    if (modeRef.current === "Pronunciation" || !spokenText.trim()) return;

    const userMsg: Message = { role: "user", text: spokenText.trim(), ts: Date.now() };
    setMessages((p) => [...p, userMsg]);
    setAiTyping(true);

    // Build conversation history for the API (last 12 msgs + the new user msg)
    const history = [...messagesRef.current, userMsg].slice(-12).map((m) => ({
      role: m.role === "ai" ? "assistant" : "user",
      content: m.text,
    }));

    try {
      const res = await fetch("/api/v1/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history,
          mode: modeRef.current,
          topic: modeRef.current === "Conversation" ? currentTopicRef.current : undefined,
        }),
      });

      if (!res.ok) throw new Error(`Chat API ${res.status}`);
      const { reply } = await res.json() as { reply: string };

      setAiTyping(false);
      setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
      speakText(reply);
    } catch {
      // Fallback: preset prompts when API key is missing or network fails
      const prompts = MODE_PROMPTS[modeRef.current] ?? MODE_PROMPTS.Conversation;
      const idx = promptIndexRef.current;
      setTimeout(() => {
        setAiTyping(false);
        let reply: string;
        if (idx < prompts.length) {
          const acks = MODE_ACKS[modeRef.current] ?? [];
          const ack  = acks[Math.floor(Math.random() * acks.length)] ?? "";
          reply = ack + prompts[idx];
          setPromptIndex(idx + 1); promptIndexRef.current = idx + 1;
        } else {
          reply = modeRef.current === "Interview"
            ? "Excellent — that wraps up our interview session. End the session to see your full assessment."
            : "Great work — you've covered everything beautifully. End the session to review your results.";
        }
        setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
        speakText(reply);
      }, 900 + Math.random() * 500);
    }
  }, [speakText]);

  useEffect(() => { triggerAIReplyRef.current = triggerAIReply; }, [triggerAIReply]);

  // ── Pronunciation attempt handler ─────────────────────────────────────────
  useEffect(() => {
    pronounceAttemptRef.current = (spoken: string) => {
      const target = pronounceTargetRef.current;
      setWaitingAttempt(false);
      const { score, feedback } = scorePhrase(spoken, target);
      setPronounceScore(score); setPronunceFeedback(feedback);
      const nextIdx = pronounceIndexRef.current + 1;
      const next    = PRONUNCIATION_PHRASES[nextIdx];
      const msg = next
        ? `${feedback} Score: ${score} out of 100. Next phrase: "${next.phrase}"`
        : `${feedback} Score: ${score} — amazing work, you've completed all phrases!`;
      setTimeout(() => {
        speakText(msg, () => {
          if (next) {
            pronounceIndexRef.current = nextIdx; pronounceTargetRef.current = next.phrase;
            setPronounceIndex(nextIdx); setPronounceScore(null); setPronunceFeedback("");
            setWaitingAttempt(true);
          }
        });
      }, 700);
    };
  }, [speakText]);

  // ── Backchannels ──────────────────────────────────────────────────────────
  const prefetchBackchannels = useCallback(async () => {
    const urls = await Promise.all(
      BACKCHANNEL_TEXTS.map((text) =>
        fetch("/api/v1/tts/speak", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice: "nova" }),
        }).then((r) => r.ok ? r.blob() : null).then((b) => b ? URL.createObjectURL(b) : null).catch(() => null),
      ),
    );
    backchannelUrlsRef.current = urls.filter(Boolean) as string[];
  }, []);

  const playBackchannel = useCallback(() => {
    const urls = backchannelUrlsRef.current;
    if (!urls.length || !voiceEnabledRef.current || aiSpeakingRef.current) return;
    const audio = new Audio(urls[Math.floor(Math.random() * urls.length)]);
    audio.volume = 0.5; backchannelAudioRef.current = audio;
    audio.play().catch(() => {});
  }, []);

  useEffect(() => {
    if (!speechActive || aiSpeaking || !sessionStarted) {
      if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current);
      return;
    }
    backchannelTimerRef.current = setInterval(() => {
      if (Date.now() - lastBackchannelRef.current >= 14000 + Math.random() * 8000) {
        lastBackchannelRef.current = Date.now(); playBackchannel();
      }
    }, 4000);
    return () => { if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current); };
  }, [speechActive, aiSpeaking, sessionStarted, playBackchannel]);

  // ── MediaPipe ────────────────────────────────────────────────────────────
  const initMediaPipe = useCallback(async () => {
    if (mpRef.current) return;
    setMpStatus("loading");
    try {
      const { FaceLandmarker, PoseLandmarker, FilesetResolver, DrawingUtils } =
        await import("@mediapipe/tasks-vision");
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm");
      const [fl, pl] = await Promise.all([
        FaceLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task", delegate: "GPU" },
          outputFaceBlendshapes: true, runningMode: "VIDEO", numFaces: 1,
        }),
        PoseLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task", delegate: "GPU" },
          runningMode: "VIDEO", numPoses: 1,
        }),
      ]);
      mpRef.current = { faceLandmarker: fl, poseLandmarker: pl, FaceLandmarker, PoseLandmarker, DrawingUtils };
      setMpStatus("ready");
    } catch { setMpStatus("error"); }
  }, []);

  // FaceLandmarker/PoseLandmarker each hold a WASM instance and a GPU
  // delegate that outlive the JS object — letting the ref just get garbage
  // collected leaks both. This was never called anywhere, so every session
  // that got navigated away from (rather than ended) leaked a GPU context;
  // a few of those in one tab is exactly what shows up as "junk" on the
  // next page — stuttering paints, stale WebGL warnings in the console.
  const disposeMediaPipe = useCallback(() => {
    const mp = mpRef.current;
    if (!mp) return;
    try { mp.faceLandmarker?.close(); } catch { /* already gone */ }
    try { mp.poseLandmarker?.close(); } catch { /* already gone */ }
    mpRef.current = null;
  }, []);

  const runDetection = useCallback(() => {
    if (!activeRef.current) return;
    const video = videoRef.current, canvas = canvasRef.current, mp = mpRef.current;
    const now = performance.now();
    if (mp && video && canvas && video.readyState >= 2 && video.videoWidth > 0 && now > lastTsRef.current) {
      const w = canvas.parentElement?.offsetWidth ?? video.videoWidth;
      const h = canvas.parentElement?.offsetHeight ?? video.videoHeight;
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, w, h); lastTsRef.current = now;
        if (!mp._du) mp._du = new mp.DrawingUtils(ctx);
        const du = mp._du;
        try {
          const fr = mp.faceLandmarker.detectForVideo(video, now);
          if (fr.faceLandmarks.length > 0) {
            setFaceDetected(true); const fl = fr.faceLandmarks[0];
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_TESSELATION, { color: "#FFFFFF10", lineWidth: 0.4 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE, { color: "#00E5FF", lineWidth: 1.5 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_LEFT_EYE,  { color: "#00E5FF", lineWidth: 1.5 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_LIPS, { color: "#FF804060", lineWidth: 1 });
            eyeContactRef.current = Math.round(ema(eyeContactRef.current, computeEye(fl), 0.15));

            // Mood — inferred from the same detector's blendshape output.
            const shapes = fr.faceBlendshapes?.[0]?.categories as Blendshape[] | undefined;
            if (shapes?.length) {
              const next = inferMood(shapes);
              const smoothedScore = moodRef.current?.label === next.label
                ? Math.round(ema(moodRef.current.score, next.score, 0.2))
                : next.score;
              moodRef.current = { label: next.label, score: smoothedScore };
            }

            // Face bounding box (canvas pixel space) for the overlay tag.
            let minX = 1, minY = 1, maxX = 0, maxY = 0;
            for (const p of fl) {
              if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
              if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
            }
            const pad = 0.04;
            const bx = clamp((minX - pad) * w, 0, w), by = clamp((minY - pad * 1.4) * h, 0, h);
            const bw = clamp((maxX - minX + pad * 2) * w, 0, w - bx), bh = clamp((maxY - minY + pad * 2.4) * h, 0, h - by);
            moodBoxRef.current = { x: bx, y: by, w: bw, h: bh };

            // Draw bracket-corner box + mood tag, matching a HUD-style ID overlay.
            if (moodRef.current) {
              const mc2 = MOOD_STATES[moodRef.current.label].color;
              const corner = Math.min(18, bw * 0.18, bh * 0.18);
              ctx.strokeStyle = `${mc2}CC`; ctx.lineWidth = 1.6; ctx.lineCap = "round";
              const drawCorner = (cx: number, cy: number, dx: number, dy: number) => {
                ctx.beginPath();
                ctx.moveTo(cx, cy + dy * corner); ctx.lineTo(cx, cy); ctx.lineTo(cx + dx * corner, cy);
                ctx.stroke();
              };
              drawCorner(bx, by, 1, 1);
              drawCorner(bx + bw, by, -1, 1);
              drawCorner(bx, by + bh, 1, -1);
              drawCorner(bx + bw, by + bh, -1, -1);

              const label = `${moodRef.current.label} · ${moodRef.current.score}%`;
              ctx.font = "600 11px Inter, sans-serif";
              const tw = ctx.measureText(label).width;
              const tagX = clamp(bx, 0, w - tw - 16), tagY = Math.max(0, by - 22);
              ctx.fillStyle = `${mc2}E6`;
              ctx.beginPath();
              ctx.roundRect?.(tagX, tagY, tw + 16, 20, 6);
              ctx.fill();
              ctx.fillStyle = "#FFFFFF";
              ctx.fillText(label, tagX + 8, tagY + 14);
            }
          } else { setFaceDetected(false); moodBoxRef.current = null; }
        } catch { /* transient */ }
        try {
          const pr = mp.poseLandmarker.detectForVideo(video, now);
          if (pr.landmarks.length > 0) {
            setPoseDetected(true); const pl = pr.landmarks[0];
            du.drawConnectors(pl, mp.PoseLandmarker.POSE_CONNECTIONS, { color: "#5C729B60", lineWidth: 2.5 });
            du.drawLandmarks(pl.slice(0, 25), { color: "#60EFFF", fillColor: "#1060FF80", radius: 3 });
            postureRef.current = Math.round(ema(postureRef.current, computePosture(pl), 0.1));
          } else { setPoseDetected(false); }
        } catch { /* transient */ }
      }
    }
    if (now - lastUpdateRef.current > 500) {
      const elapsed = (now - startTimeRef.current) / 1000;
      const { score: fluency, wpm: w } = computeFluency(wordListRef.current.length, fillerCntRef.current, elapsed);
      setWpm(w);
      const confidence = clamp(Math.round(eyeContactRef.current * 0.45 + postureRef.current * 0.55));
      if (now - lastPrevRef.current > 5000 && lastPrevRef.current > 0)
        setPrevFeedback({ fluency, pronunciation: pronounceRef.current, eye_contact: eyeContactRef.current, confidence, speaking_pace: w, posture: postureRef.current });
      if (now - lastPrevRef.current > 5000) lastPrevRef.current = now;
      updateLiveFeedback({ fluency, pronunciation: pronounceRef.current, eye_contact: eyeContactRef.current, confidence, speaking_pace: w, posture: postureRef.current });
      setMood(moodRef.current);
      gazeSamplesRef.current.push({ t: elapsed, eye: eyeContactRef.current });
      lastUpdateRef.current = now;
    }
    animRef.current = requestAnimationFrame(runDetection);
  }, [updateLiveFeedback]);

  // ── Web Speech API ────────────────────────────────────────────────────────
  const startSpeech = useCallback(() => {
    const w = window as any;
    const SR = typeof window !== "undefined" ? (w.SpeechRecognition ?? w.webkitSpeechRecognition) : null;
    if (!SR) return;
    const rec: any = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-MY"; rec.maxAlternatives = 1;
    rec.onstart = () => setSpeechActive(true);
    rec.onresult = (ev: any) => {
      lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const text: string = ev.results[i][0].transcript;
        const conf: number = ev.results[i][0].confidence ?? 0.7;
        if (ev.results[i].isFinal) {
          if (modeRef.current === "Pronunciation") {
            pronounceAttemptRef.current(text);
          } else {
            appendTranscript(text);
            const words = text.trim().split(/\s+/).filter(Boolean);
            wordListRef.current.push(...words);
            const tNow = (performance.now() - startTimeRef.current) / 1000;
            const cleanWords = words.map((w: string) => w.toLowerCase().replace(/[^a-z']/g, ""));
            let fillerHits = 0;
            cleanWords.forEach((cw: string, i: number) => {
              if (!cw) return;
              if (FILLER_WORDS.has(cw)) { fillerHits++; disfluencyEventsRef.current.push({ t: tNow }); }
              // Immediate word repetition ("I I", "the the") — a classic
              // stutter/repetition proxy, checked across the recognition
              // batch boundary too via lastWordRef.
              const prev = i === 0 ? lastWordRef.current : cleanWords[i - 1];
              if (cw === prev) disfluencyEventsRef.current.push({ t: tNow });
            });
            if (cleanWords.length) lastWordRef.current = cleanWords[cleanWords.length - 1];
            fillerCntRef.current += fillerHits;
            setFillerCount(fillerCntRef.current);
            pronounceRef.current = Math.round(ema(pronounceRef.current, conf * 100, 0.3));
            pendingUserSpeechRef.current += (pendingUserSpeechRef.current ? " " : "") + text.trim();
            if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
            autoReplyTimerRef.current = setTimeout(() => {
              const spoken = pendingUserSpeechRef.current.trim();
              pendingUserSpeechRef.current = "";
              if (spoken) triggerAIReplyRef.current(spoken);
            }, 2500);
          }
          setInterimText("");
        } else { interim += text; }
      }
      if (interim) setInterimText(interim);
    };
    rec.onerror = (ev: any) => {
      if (ev.error === "no-speech" || ev.error === "aborted") return;
      setSpeechActive(false);
    };
    rec.onend = () => {
      setSpeechActive(false);
      if (activeRef.current && !aiSpeakingRef.current) {
        try { rec.start(); } catch { /* ok */ }
      }
    };
    try { rec.start(); recognRef.current = rec; } catch { /* ok */ }
  }, [appendTranscript]);

  useEffect(() => { startSpeechRef.current = startSpeech; }, [startSpeech]);

  const stopSpeech = useCallback(() => {
    if (recognRef.current) {
      recognRef.current.onend = null;
      try { recognRef.current.stop(); } catch { /* ok */ }
      recognRef.current = null;
    }
    setSpeechActive(false); setInterimText("");
  }, []);

  const interruptAI = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; audioRef.current = null; }
    window.speechSynthesis?.cancel();
    setAiSpeaking(false); aiSpeakingRef.current = false;
    setTimeout(() => startSpeechRef.current(), 120);
  }, []);

  // ── Live audio metering ──────────────────────────────────────────────────
  const startAudioMeter = useCallback((stream: MediaStream) => {
    try {
      const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AC();
      const source  = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.55;
      source.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.frequencyBinCount);
      let lastUi = 0;
      const tick = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        const avg = sum / data.length / 255;
        audioLevelRef.current = audioLevelRef.current * 0.72 + avg * 0.28;
        const now = performance.now();
        if (now - lastUi > 80) { setAudioLevel(audioLevelRef.current); lastUi = now; }
        audioMeterRafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch { /* audio metering is a nice-to-have, session still works without it */ }
  }, []);

  const stopAudioMeter = useCallback(() => {
    if (audioMeterRafRef.current) cancelAnimationFrame(audioMeterRafRef.current);
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null; analyserRef.current = null;
    audioLevelRef.current = 0; setAudioLevel(0);
  }, []);

  // ── Camera ────────────────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
      startAudioMeter(stream);

      // Record the session (audio+video together) so it can be uploaded for
      // real backend analysis once the session ends.
      try {
        recordedChunksRef.current = [];
        const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
          ? "video/webm;codecs=vp9,opus"
          : MediaRecorder.isTypeSupported("video/webm") ? "video/webm" : "";
        const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        mr.ondataavailable = (e) => { if (e.data.size > 0) recordedChunksRef.current.push(e.data); };
        mr.start(1000);
        mediaRecorderRef.current = mr;
      } catch { /* MediaRecorder unsupported — session still works, just without backend analysis */ }
    } catch { /* ok */ }
  }, [setCameraOn, startAudioMeter]);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const mr = mediaRecorderRef.current;
      if (!mr || mr.state === "inactive") { resolve(null); return; }
      mr.onstop = () => {
        resolve(recordedChunksRef.current.length
          ? new Blob(recordedChunksRef.current, { type: "video/webm" })
          : null);
      };
      mr.stop();
    });
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
    stopAudioMeter();
  }, [setCameraOn, stopAudioMeter]);

  // ── Slide upload ──────────────────────────────────────────────────────────
  const handleSlideUpload = useCallback((file: File) => {
    setSlideFile(file); setAnalyzing(true);
    setTimeout(() => { setSlideOutline(mockSlideOutline(file.name)); setAnalyzing(false); setSlideAnalyzed(true); }, 2200);
  }, []);

  // ── Session start / end ───────────────────────────────────────────────────
  const startSession = useCallback(async () => {
    wordListRef.current = []; fillerCntRef.current = 0;
    eyeContactRef.current = 50; postureRef.current = 50; pronounceRef.current = 72;
    lastUpdateRef.current = 0; lastPrevRef.current = 0; lastTsRef.current = 0;
    lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
    gazeSamplesRef.current = []; disfluencyEventsRef.current = []; lastWordRef.current = "";
    activeRef.current = true; startTimeRef.current = performance.now();
    pronounceIndexRef.current = 0; pronounceTargetRef.current = PRONUNCIATION_PHRASES[0].phrase;
    setPronounceIndex(0); setPronounceScore(null); setPronunceFeedback("");
    pendingUserSpeechRef.current = "";

    setSessionStarted(true); setRecording(true); setFillerCount(0); setWpm(0);
    resetDuration(); reset();

    const [backendSession] = await Promise.all([
      practiceService.startSession(mode as SessionType).catch(() => null),
      startCamera(),
    ]);
    backendSessionIdRef.current = backendSession?.id ?? null;

    prefetchBackchannels();
    timerRef.current = setInterval(() => incrementDuration(), 1000);
    startSpeech();
    initMediaPipe().then(() => { if (activeRef.current) animRef.current = requestAnimationFrame(runDetection); });

    const prompts  = MODE_PROMPTS[mode] ?? MODE_PROMPTS.Conversation;
    const firstMsg = mode === "Pronunciation"
      ? `${prompts[0]} Here is your first phrase: "${PRONUNCIATION_PHRASES[0].phrase}". I'll say it aloud first.`
      : prompts[0];

    setTimeout(() => {
      setAiTyping(true);
      setTimeout(() => {
        setAiTyping(false);
        if (mode !== "Pronunciation") { setMessages([{ role: "ai", text: firstMsg, ts: Date.now() }]); setPromptIndex(1); }
        speakText(firstMsg, () => { if (mode === "Pronunciation") setWaitingAttempt(true); });
      }, 1200);
    }, 600);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, speakText]);

  const endSession = useCallback(async () => {
    setIsEnding(true); activeRef.current = false;
    if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
    pendingUserSpeechRef.current = "";
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; audioRef.current = null; }
    if (backchannelAudioRef.current) { backchannelAudioRef.current.pause(); backchannelAudioRef.current = null; }
    if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current);
    backchannelUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
    window.speechSynthesis?.cancel();
    if (timerRef.current) clearInterval(timerRef.current);
    if (silenceCheckRef.current) clearInterval(silenceCheckRef.current);
    cancelAnimationFrame(animRef.current);
    stopSpeech();

    const recordedBlob = await stopRecording();
    stopCamera(); setRecording(false);

    const sessionId = backendSessionIdRef.current;
    if (sessionId) {
      try {
        if (recordedBlob) {
          await Promise.all([
            speechService.uploadAudio(sessionId, recordedBlob),
            visionService.uploadVideo(sessionId, recordedBlob),
          ]);
        }
        await practiceService.endSession(sessionId, duration);
        const result = await analysisService.run(sessionId);
        setFullAnalysis(result);

        setSpeechAnalysis({
          id: "", session_id: sessionId,
          fluency_score: result.speech.fluency_score,
          pronunciation_score: result.speech.pronunciation_score,
          speaking_rate: result.speech.speaking_rate,
          filler_word_count: result.speech.filler_count,
          stuttering_score: result.speech.stuttering_score,
        });
        setVisionAnalysis({
          id: "", session_id: sessionId,
          eye_contact_score: result.vision.eye_contact_score,
          confidence_score: result.vision.confidence_score,
          posture_score: result.vision.posture_score,
          emotion_label: result.vision.dominant_emotion,
        });
        setAIFeedback({
          id: "", session_id: sessionId,
          summary:
            `Overall score: ${result.communication_score.overall_score}% (${result.communication_score.grade}). ` +
            `Strengths: ${result.communication_score.strengths.join(", ") || "Keep practicing!"}. ` +
            `Focus areas: ${result.communication_score.improvement_areas.join(", ") || "None identified"}.`,
          recommendations: result.recommendations.exercises.map((e) => e.title),
          created_at: new Date().toISOString(),
        });
        updateLiveFeedback({
          fluency: result.speech.fluency_score,
          pronunciation: result.speech.pronunciation_score,
          eye_contact: result.vision.eye_contact_score,
          confidence: result.vision.confidence_score,
          speaking_pace: result.speech.speaking_rate,
          posture: result.vision.posture_score,
        });
      } catch {
        // Real analysis failed (e.g. backend unreachable) — /assessment falls
        // back to its existing mock data, so the page stays usable.
      }
    }

    // Client-side only — doesn't depend on the backend call above, so it's
    // still computed even if analysis upload failed.
    setGazeTunneling(computeGazeTunneling(gazeSamplesRef.current, disfluencyEventsRef.current));

    router.push("/assessment");
  }, [
    stopSpeech, stopRecording, stopCamera, setRecording, router, duration,
    setSpeechAnalysis, setVisionAnalysis, setAIFeedback, setFullAnalysis, setGazeTunneling, updateLiveFeedback,
  ]);

  // ── Silence detection ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionStarted) return;
    silenceCheckRef.current = setInterval(() => {
      if (!activeRef.current || aiTypingRef.current || aiSpeakingRef.current) return;
      if ((performance.now() - startTimeRef.current) / 1000 < 20) return;
      if ((Date.now() - lastSpeechTimeRef.current) / 1000 > 22 && !checkinAskedRef.current) {
        checkinAskedRef.current = true;
        const msg = CHECKIN_MESSAGES[Math.floor(Date.now() / 1000) % CHECKIN_MESSAGES.length];
        if (modeRef.current !== "Pronunciation") setMessages((p) => [...p, { role: "ai", text: msg, ts: Date.now() }]);
        speakText(msg);
      }
    }, 5000);
    return () => { if (silenceCheckRef.current) clearInterval(silenceCheckRef.current); };
  }, [sessionStarted, speakText]);

  // ── Toggles ───────────────────────────────────────────────────────────────
  const toggleMic = () => {
    if (!sessionStarted) return;
    if (isRecording) { streamRef.current?.getAudioTracks().forEach((t) => (t.enabled = false)); stopSpeech(); }
    else { streamRef.current?.getAudioTracks().forEach((t) => (t.enabled = true)); startSpeech(); }
    setRecording(!isRecording);
  };

  const toggleCamera = () => {
    if (!sessionStarted) return;
    if (isCameraOn) { streamRef.current?.getVideoTracks().forEach((t) => (t.enabled = false)); setCameraOn(false); }
    else { streamRef.current?.getVideoTracks().forEach((t) => (t.enabled = true)); setCameraOn(true); }
  };

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || !sessionStarted || aiTyping || mode === "Pronunciation") return;
    if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
    pendingUserSpeechRef.current = "";
    lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
    setInput("");
    const words = text.split(/\s+/).filter(Boolean);
    wordListRef.current.push(...words);
    fillerCntRef.current += words.filter((w) => FILLER_WORDS.has(w.toLowerCase())).length;
    appendTranscript(text);
    triggerAIReplyRef.current(text);
  }, [input, sessionStarted, aiTyping, mode, appendTranscript]);

  const shuffleTopic = useCallback(() => {
    const next = RANDOM_TOPICS[Math.floor(Math.random() * RANDOM_TOPICS.length)];
    setCurrentTopic(next);
    if (sessionStarted) {
      const reply = `Let's switch it up! Here's a new topic: ${next}`;
      setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
      speakText(reply);
    }
  }, [sessionStarted, speakText]);

  // ── Scroll + cleanup ──────────────────────────────────────────────────────
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, aiTyping]);
  useEffect(() => {
    return () => {
      activeRef.current = false;
      window.speechSynthesis?.cancel();
      if (timerRef.current) clearInterval(timerRef.current);
      if (silenceCheckRef.current) clearInterval(silenceCheckRef.current);
      cancelAnimationFrame(animRef.current);
      stopSpeech(); stopCamera(); disposeMediaPipe();
      // Leaving without clicking "End" — a MediaRecorder still attached to
      // (now-stopped) tracks won't emit further data, but stop it
      // explicitly so it isn't left in "recording" state indefinitely.
      const mr = mediaRecorderRef.current;
      if (mr && mr.state !== "inactive") { try { mr.stop(); } catch { /* already stopped */ } }
    };
  }, [stopCamera, stopSpeech, disposeMediaPipe]);

  // ── Derived ───────────────────────────────────────────────────────────────
  const fmt = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const MODE_COLORS: Record<string, string> = {
    Conversation: "#5C729B", Interview: "#79738C", Presentation: "#9C6A28", Pronunciation: "#4D7A59",
  };
  const mc = MODE_COLORS[mode] ?? "#5C729B";

  const orbState: OrbState =
    aiTyping   ? "thinking"  :
    aiSpeaking ? "speaking"  :
    speechActive && sessionStarted ? "listening" : "idle";

  const stateLabel =
    aiTyping    ? "Thinking…"      :
    aiSpeaking  ? "AI speaking"    :
    speechActive && sessionStarted ? "Listening…" :
    sessionStarted ? "Your turn"   : "Ready to start";

  const currentPhrase   = PRONUNCIATION_PHRASES[pronounceIndex];
  const currentQuestion = messages.filter((m) => m.role === "ai").at(-1)?.text ?? null;
  const showYourTurn    = sessionStarted && !aiTyping && !aiSpeaking
    && messages.length > 0 && messages[messages.length - 1].role === "ai"
    && mode !== "Pronunciation";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="session-dark flex flex-col px-3 sm:px-6 py-4 h-auto lg:h-[calc(100dvh-60px)] overflow-y-auto lg:overflow-hidden">

      {/* ── Analyzing overlay ──────────────────────────────────────────── */}
      {isEnding && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)" }}
        >
          <div
            className="flex flex-col items-center gap-4 p-8 rounded-2xl text-center"
            style={{ background: "rgba(10,13,40,0.98)", border: "1px solid rgba(35,52,92,0.3)", boxShadow: "0 24px 60px rgba(0,0,0,0.6)" }}
          >
            <Loader2 className="w-8 h-8 animate-spin text-blue-300" />
            <div>
              <p className="text-sm font-bold text-white">Analyzing your session…</p>
              <p className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>
                Running speech and vision AI on your recording. This can take a moment.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 flex-shrink-0 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold px-3 py-1.5 rounded-full"
            style={{ background: `${mc}20`, color: mc, border: `1px solid ${mc}30` }}>
            {mode} Practice
          </span>
          <span
            title="Scores and corrections are held until you finish speaking — we never interrupt mid-sentence."
            className="hidden sm:flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full cursor-help"
            style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.4)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <EarOff className="w-3 h-3" /> Feedback after, not during
          </span>
          {sessionStarted && (
            <span className="flex items-center gap-2 font-mono text-sm font-semibold text-white/70">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"
                style={{ boxShadow: "0 0 6px rgba(156,74,64,0.7)" }} />
              {fmt(duration)}
              <HeaderPulse level={audioLevel} active={isRecording} color={mc} />
            </span>
          )}
          {sessionStarted && mpStatus === "loading" && (
            <span className="flex items-center gap-1.5 text-xs text-amber-400/80">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Initialising AI vision…
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Voice */}
          <button onClick={() => setVoiceEnabled((v) => !v)}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all"
            style={voiceEnabled
              ? { borderColor: `${mc}50`, color: mc, background: `${mc}12` }
              : { borderColor: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.35)" }}>
            {voiceEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            {voiceEnabled ? "Voice On" : "Voice Off"}
          </button>

          {/* Interrupt */}
          {aiSpeaking && (
            <button onClick={interruptAI}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl text-white transition-all press-effect"
              style={{ background: "rgba(156,74,64,0.85)", boxShadow: "0 0 16px rgba(156,74,64,0.4)" }}>
              ✕ Interrupt
            </button>
          )}

          {!sessionStarted ? (
            <button onClick={startSession}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold text-white transition-all press-effect"
              style={{ background: mc }}>
              <Mic className="w-4 h-4" /> Start Session
            </button>
          ) : (
            <button onClick={endSession} disabled={isEnding}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all press-effect disabled:opacity-50"
              style={{ background: "rgba(156,74,64,0.8)", border: "1px solid rgba(156,74,64,0.4)" }}>
              {isEnding ? <Loader2 className="w-4 h-4 animate-spin" /> : <PhoneOff className="w-4 h-4" />}
              End
            </button>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      {mode === "Interview" ? (

        /* ── Interview Room ─────────────────────────────────────────────── */
        <div className="flex flex-col lg:flex-row flex-1 gap-4 min-h-0">

          {/* LEFT: Interviewer panel */}
          <div className="flex flex-col gap-3 w-full lg:w-[56%] lg:flex-shrink-0">

            {/* Interviewer card */}
            <div className="flex-1 glass-card rounded-2xl relative overflow-hidden" style={{ minHeight: 0 }}>

              {/* Top bar: company context + timer */}
              <div className="absolute top-0 left-0 right-0 px-5 py-3 flex items-center justify-between z-10"
                style={{ background: "linear-gradient(180deg, rgba(8,10,28,0.96) 0%, transparent 100%)" }}>
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: "rgba(35,52,92,0.3)", border: "1px solid rgba(35,52,92,0.4)" }}>
                    <Briefcase className="w-3.5 h-3.5 text-blue-300" />
                  </div>
                  <div>
                    <p className="text-white text-xs font-bold">SpeechMate Corp · Technical Interview</p>
                    <p className="text-[10px]" style={{ color: "rgba(255,255,255,0.4)" }}>Software Engineer Position</p>
                  </div>
                </div>
                {sessionStarted && (
                  <span className="flex items-center gap-1.5 font-mono text-xs font-semibold text-white/60">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"
                      style={{ boxShadow: "0 0 6px rgba(156,74,64,0.7)" }} />
                    {fmt(duration)}
                  </span>
                )}
              </div>

              {/* Interviewer avatar — centred */}
              <div className="w-full h-full flex items-center justify-center" style={{ paddingTop: 56, paddingBottom: 16 }}>
                <InterviewerAvatar state={orbState} />
              </div>

              {/* User camera PiP */}
              <div className="absolute bottom-3 left-3 rounded-xl overflow-hidden"
                style={{ width: 132, height: 94, border: "2px solid rgba(35,52,92,0.3)", boxShadow: "0 4px 14px rgba(0,0,0,0.6)" }}>
                <div className="relative w-full h-full bg-black/70">
                  <video ref={videoRef} autoPlay muted playsInline
                    className={cn("w-full h-full object-cover", !isCameraOn && "hidden")} />
                  <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
                  {!isCameraOn && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <VideoOff className="w-4 h-4 text-white/20" />
                    </div>
                  )}
                  <div className="absolute top-1.5 left-1.5">
                    <span className="text-[8px] font-bold bg-black/70 text-white/60 px-1.5 py-0.5 rounded-md">YOU</span>
                  </div>
                  {sessionStarted && (
                    <div className="absolute top-1.5 right-1.5 flex flex-col gap-0.5 items-end">
                      {faceDetected && <span className="text-[8px] font-bold bg-black/60 text-cyan-400 px-1 py-0.5 rounded-md">FACE ●</span>}
                    </div>
                  )}
                  {sessionStarted && (
                    <div className="absolute top-1.5 left-1.5">
                      <span className="text-[8px] font-bold bg-black/60 text-red-400 px-1 py-0.5 rounded-md flex items-center gap-0.5">
                        <span className="w-1 h-1 rounded-full bg-red-500 animate-pulse" /> LIVE
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Mic + cam controls */}
              <div className="absolute bottom-3 right-3 flex items-center gap-2">
                <button onClick={toggleMic} disabled={!sessionStarted}
                  className={cn("w-9 h-9 rounded-full flex items-center justify-center transition-all press-effect",
                    !sessionStarted ? "opacity-30 cursor-not-allowed" : "")}
                  style={isRecording
                    ? { background: "rgba(156,74,64,0.85)", boxShadow: "0 0 14px rgba(156,74,64,0.5)" }
                    : { background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}>
                  {isRecording ? <Mic className="w-4 h-4 text-white" /> : <MicOff className="w-4 h-4 text-white/40" />}
                </button>
                <button onClick={toggleCamera} disabled={!sessionStarted}
                  className={cn("w-9 h-9 rounded-full flex items-center justify-center transition-all press-effect",
                    !sessionStarted ? "opacity-30 cursor-not-allowed" : "text-white/40")}
                  style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}>
                  {isCameraOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                </button>
              </div>

              {/* AI speaking overlay badge */}
              {aiSpeaking && (
                <div className="absolute top-[56px] right-4 flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl"
                  style={{ background: "rgba(35,52,92,0.25)", border: "1px solid rgba(35,52,92,0.4)" }}>
                  <Volume2 className="w-3 h-3 text-blue-300 animate-pulse" />
                  <span className="text-[10px] font-semibold text-blue-300">Alex is speaking</span>
                </div>
              )}
            </div>

            {/* Current question card */}
            {currentQuestion && (
              <div className="glass-card rounded-2xl p-4 flex-shrink-0">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                  <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider">Current Question</p>
                </div>
                <p className="text-sm text-white/85 leading-relaxed"
                  style={{ display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" } as React.CSSProperties}>
                  {currentQuestion}
                </p>
              </div>
            )}
          </div>

          {/* RIGHT: Metrics + responses */}
          <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-0">

            {/* Live performance */}
            <div className="glass-card rounded-2xl p-4 flex-shrink-0">
              <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider mb-3">Live Performance</p>
              <div className="space-y-2.5">
                {[
                  { label: "Fluency",       value: sessionStarted ? liveFeedback.fluency       : 0, color: "#5C729B" },
                  { label: "Eye Contact",   value: sessionStarted ? liveFeedback.eye_contact   : 0, color: "#4D7A59" },
                  { label: "Confidence",    value: sessionStarted ? liveFeedback.confidence    : 0, color: "#9C6A28" },
                  { label: "Pronunciation", value: sessionStarted ? liveFeedback.pronunciation : 0, color: "#79738C" },
                ].map(({ label, value, color }) => (
                  <div key={label}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-white/45 font-medium">{label}</span>
                      <span className="text-xs font-bold" style={{ color }}>{sessionStarted ? value : "–"}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${value}%`, background: `linear-gradient(90deg, ${color}80, ${color})` }} />
                    </div>
                  </div>
                ))}
                {wpm > 0 && (
                  <div className="pt-1.5" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-white/45 font-medium">Speaking Pace</span>
                      <span className="text-xs font-bold text-white/70">
                        {wpm} WPM
                        <span className="ml-1.5 text-[9px] font-semibold"
                          style={{ color: wpm > 160 ? "#ef4444" : wpm < 100 ? "#f59e0b" : "#22c55e" }}>
                          {wpm > 160 ? "↑ Too fast" : wpm < 100 ? "↓ Too slow" : "✓ Good"}
                        </span>
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Response transcript */}
            <div className="flex-1 glass-card rounded-2xl p-4 overflow-y-auto min-h-0">
              <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider mb-3">Your Responses</p>
              {!sessionStarted || messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-4">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
                    style={{ background: "rgba(35,52,92,0.15)", border: "1px solid rgba(35,52,92,0.25)" }}>
                    <Activity className="w-5 h-5 text-blue-300" />
                  </div>
                  <p className="text-xs text-white/30 leading-relaxed">
                    {sessionStarted
                      ? "Alex is preparing your first question…"
                      : "Start the session. Alex will conduct a realistic mock interview — speak your answers aloud."}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {messages.map((msg, i) => (
                    <div key={i} className={cn("flex gap-2", msg.role === "user" && "flex-row-reverse")}
                      style={{ animation: "slide-up 0.3s cubic-bezier(0.16,1,0.3,1) forwards" }}>
                      {msg.role === "ai" && (
                        <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-[9px] font-bold text-white"
                          style={{ background: "#5A5470", minWidth: 24 }}>A</div>
                      )}
                      <div className="max-w-[85%] px-3 py-2 text-xs leading-relaxed"
                        style={msg.role === "ai"
                          ? { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.8)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px 12px 12px 3px" }
                          : { background: "rgba(35,52,92,0.85)", color: "white", borderRadius: "12px 12px 3px 12px" }}>
                        {msg.text}
                      </div>
                    </div>
                  ))}

                  {aiTyping && (
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                        style={{ background: "#5A5470", minWidth: 24 }}>A</div>
                      <div className="px-3 py-2.5 flex items-center gap-1"
                        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px 12px 12px 3px" }}>
                        {[0, 1, 2].map((i) => (
                          <span key={i} className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }} />
                        ))}
                      </div>
                    </div>
                  )}

                  {showYourTurn && (
                    <div className="flex items-center gap-3 py-1">
                      <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
                      <span className="text-[10px] text-white/30 font-medium whitespace-nowrap">
                        {speechActive ? "🎙 Speak your answer" : "Your turn"}
                      </span>
                      <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {/* Live transcript strip */}
            {(transcript || interimText) && sessionStarted && (
              <div className="flex-shrink-0 px-3 py-2 rounded-xl"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <p className="text-[10px] text-white/30 font-semibold uppercase tracking-wider mb-0.5">Live Transcript</p>
                <p className="text-xs text-white/55 line-clamp-1">
                  {transcript}
                  {interimText && <span className="text-white/30 italic"> {interimText}</span>}
                </p>
              </div>
            )}

            {/* Input */}
            <div className="flex-shrink-0 flex gap-2">
              <input type="text" value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                disabled={!sessionStarted || aiTyping || aiSpeaking}
                placeholder={
                  !sessionStarted   ? "Start the interview first…" :
                  aiSpeaking        ? "Alex is speaking — listen carefully…" :
                  aiTyping          ? "Alex is formulating a question…" :
                  speechActive      ? "Speaking captured — or type here…" :
                  "Speak your answer aloud, or type it here…"
                }
                className="flex-1 px-4 py-3 rounded-xl text-sm text-white/80 outline-none transition-all disabled:opacity-40 placeholder:text-white/25"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
                onFocus={(e) => (e.target.style.borderColor = "rgba(96,165,250,0.5)")}
                onBlur={(e) => (e.target.style.borderColor = "rgba(255,255,255,0.08)")}
              />
              <button onClick={sendMessage}
                disabled={!sessionStarted || !input.trim() || aiTyping || aiSpeaking}
                className="w-11 h-11 flex items-center justify-center rounded-xl text-white transition-all disabled:opacity-30 flex-shrink-0 press-effect"
                style={{ background: "#23345C" }}>
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

      ) : (

        /* ── Default 2-column layout (Conversation / Presentation / Pronunciation) ── */
        <div className="flex flex-col lg:flex-row flex-1 gap-4 min-h-0">

          {/* LEFT: Orb + camera PiP */}
          <div className="w-full lg:w-[300px] lg:flex-shrink-0 flex flex-col gap-3">

          {/* Orb card */}
          <div className="flex-1 glass-card rounded-2xl flex flex-col items-center justify-center gap-6 relative overflow-hidden"
            style={{ minHeight: 320 }}>
            {/* Orb */}
            <div style={{ paddingBottom: 40 }}>
              <AIOrb state={orbState} level={audioLevel} />
            </div>

            {/* State label */}
            <div className="absolute bottom-16 flex flex-col items-center gap-1">
              <p className="text-sm font-semibold"
                style={{
                  color: orbState === "listening" ? "#4ade80"
                       : orbState === "speaking"  ? "#93c5fd"
                       : orbState === "thinking"  ? "#fbbf24"
                       : "rgba(255,255,255,0.5)",
                }}>
                {stateLabel}
              </p>
            </div>

            {/* Mic + camera controls */}
            <div className="absolute bottom-4 flex items-center gap-3">
              <div className="relative">
                {/* Ripple ring — real amplitude, not a canned pulse loop */}
                {isRecording && (
                  <div className="absolute rounded-full pointer-events-none"
                    style={{
                      inset: -6 - audioLevel * 14,
                      border: "1.5px solid rgba(156,74,64,0.4)",
                      opacity: Math.min(1, audioLevel * 2.5),
                      transition: "inset 0.1s ease-out, opacity 0.1s ease-out",
                    }} />
                )}
                <button onClick={toggleMic} disabled={!sessionStarted}
                  className={cn(
                    "relative w-10 h-10 rounded-full flex items-center justify-center transition-all press-effect",
                    !sessionStarted ? "opacity-30 cursor-not-allowed" : "",
                    isRecording
                      ? "text-white"
                      : "text-white/40 hover:text-white/70",
                  )}
                  style={isRecording ? {
                    background: "rgba(156,74,64,0.85)",
                    boxShadow: `0 0 ${16 + audioLevel * 20}px rgba(156,74,64,${0.5 + audioLevel * 0.3})`,
                    transform: `scale(${1 + audioLevel * 0.08})`,
                    transition: "box-shadow 0.1s ease-out, transform 0.1s ease-out",
                  } : { background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}>
                  {isRecording ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                </button>
              </div>
              <button onClick={toggleCamera} disabled={!sessionStarted}
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center transition-all press-effect",
                  !sessionStarted ? "opacity-30 cursor-not-allowed" : "text-white/40 hover:text-white/70",
                )}
                style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}>
                {isCameraOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Camera PiP */}
          <div className="glass-card rounded-2xl overflow-hidden flex-shrink-0" style={{ height: 140 }}>
            <div className="relative w-full h-full bg-black/60">
              <video ref={videoRef} autoPlay muted playsInline
                className={cn("w-full h-full object-cover", !isCameraOn && "hidden")} />
              <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
              {!isCameraOn && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <VideoOff className="w-6 h-6 text-white/20" />
                </div>
              )}
              {sessionStarted && (
                <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
                  {faceDetected && <span className="text-[9px] font-bold bg-black/60 text-cyan-400 px-1.5 py-0.5 rounded-md">FACE ●</span>}
                  {poseDetected && <span className="text-[9px] font-bold bg-black/60 text-blue-400 px-1.5 py-0.5 rounded-md">POSE ●</span>}
                </div>
              )}
              {sessionStarted && (
                <div className="absolute top-2 left-2">
                  <span className="text-[9px] font-bold bg-black/60 text-red-400 px-1.5 py-0.5 rounded-md flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-red-500 animate-pulse" /> LIVE
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Mood — read from the same face tracking already running above */}
          {sessionStarted && (
            <div className="glass-card rounded-2xl p-3 flex-shrink-0">
              <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider mb-2">Presence &amp; Mood</p>
              <div className="flex flex-wrap gap-1.5">
                {(Object.keys(MOOD_STATES) as MoodLabel[]).map((label) => {
                  const active = mood?.label === label;
                  const c = MOOD_STATES[label].color;
                  return (
                    <span key={label}
                      className="flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-full transition-all duration-300"
                      style={active
                        ? { background: c, color: "#fff" }
                        : { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.35)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      {active && <span className="w-1 h-1 rounded-full bg-white" />}
                      {label}{active ? ` · ${mood!.score}%` : ""}
                    </span>
                  );
                })}
              </div>
              {!faceDetected && (
                <p className="text-[10px] text-white/30 mt-2">Face not detected — centre yourself in frame.</p>
              )}
            </div>
          )}

          {/* Topic shuffler — Conversation mode */}
          {mode === "Conversation" && (
            <div className="glass-card rounded-2xl p-3 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider">Current Topic</p>
                <button onClick={shuffleTopic}
                  className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg transition-all press-effect"
                  style={{ color: mc, background: `${mc}15`, border: `1px solid ${mc}25` }}>
                  <Shuffle className="w-3 h-3" /> Shuffle
                </button>
              </div>
              <p className="text-xs text-white/70 leading-relaxed line-clamp-3">{currentTopic}</p>
            </div>
          )}

          {/* Slide outline (Presentation) */}
          {mode === "Presentation" && sessionStarted && slideAnalyzed && (
            <div className="glass-card rounded-2xl p-3 flex-shrink-0 max-h-[140px] overflow-y-auto">
              <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider mb-2">Slide Outline</p>
              {slideOutline.map((item, i) => (
                <div key={i} className="flex gap-1.5 mb-1.5">
                  <span className="text-[10px] font-bold" style={{ color: mc }}>{i+1}.</span>
                  <p className="text-[10px] text-white/55 leading-relaxed line-clamp-1">{item.split(":")[0]}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Conversation / pronunciation / slides */}
        <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-0">

          {/* ── PRONUNCIATION: phrase card ─────────────────────────────── */}
          {mode === "Pronunciation" && sessionStarted && (
            <div className="flex-1 glass-card rounded-2xl p-6 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider">
                  Phrase {pronounceIndex + 1} / {PRONUNCIATION_PHRASES.length}
                </p>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                  style={{ background: `${mc}20`, color: mc, border: `1px solid ${mc}30` }}>
                  {currentPhrase.focus}
                </span>
              </div>

              <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
                <p className="text-white/30 text-xs mb-3">Repeat this phrase:</p>
                <p className="text-2xl font-semibold text-white leading-relaxed mb-2">
                  &ldquo;{currentPhrase.phrase}&rdquo;
                </p>
                <p className="text-xs text-white/40 mb-8">
                  <span className="font-semibold text-white/60">Tip:</span> {currentPhrase.hint}
                </p>

                {pronounceScore !== null && (
                  <div className="w-full rounded-2xl p-5 mb-5 text-center"
                    style={{
                      background: pronounceScore >= 75 ? "rgba(77,122,89,0.1)" : pronounceScore >= 50 ? "rgba(156,106,40,0.1)" : "rgba(156,74,64,0.1)",
                      border: `1px solid ${pronounceScore >= 75 ? "rgba(77,122,89,0.25)" : pronounceScore >= 50 ? "rgba(156,106,40,0.25)" : "rgba(156,74,64,0.25)"}`,
                    }}>
                    <div className="flex justify-center gap-1 mb-2">
                      {[...Array(5)].map((_, i) => (
                        <Star key={i} className={cn("w-4 h-4", i < Math.round(pronounceScore / 20) ? "fill-amber-400 text-amber-400" : "text-white/15")} />
                      ))}
                    </div>
                    <p className="text-3xl font-bold text-white">{pronounceScore}<span className="text-sm text-white/40">/100</span></p>
                    <p className="text-xs text-white/50 mt-1">{pronounceFeedback}</p>
                  </div>
                )}

                <div className="flex gap-3">
                  <button onClick={() => { speakText(currentPhrase.phrase, () => setWaitingAttempt(true)); }}
                    disabled={aiSpeaking}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all press-effect disabled:opacity-40"
                    style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)" }}>
                    <Volume2 className="w-4 h-4" />
                    {aiSpeaking ? "Playing…" : "Hear it"}
                  </button>
                  {waitingAttempt && !aiSpeaking && (
                    <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold"
                      style={{ background: `${mc}18`, border: `1px solid ${mc}30`, color: mc }}>
                      <Mic className="w-4 h-4 animate-pulse" /> Your turn — speak now
                    </div>
                  )}
                </div>
              </div>

              {/* Progress dots */}
              <div className="flex justify-center gap-2 mt-4">
                {PRONUNCIATION_PHRASES.map((_, i) => (
                  <span key={i} className="rounded-full transition-all duration-300"
                    style={{
                      width: i === pronounceIndex ? 20 : 8, height: 8,
                      background: i === pronounceIndex ? mc : i < pronounceIndex ? `${mc}60` : "rgba(255,255,255,0.12)",
                    }} />
                ))}
              </div>
            </div>
          )}

          {/* ── PRESENTATION: slide upload (pre-session) ────────────────── */}
          {mode === "Presentation" && !sessionStarted && (
            <div className="flex-1 glass-card rounded-2xl p-6 flex flex-col">
              <p className="text-sm font-semibold text-white/80 mb-1">Upload Your Slides</p>
              <p className="text-xs text-white/40 mb-5">AI will analyse your deck and generate a coaching script outline.</p>

              {!slideFile ? (
                <div onClick={() => slideInputRef.current?.click()}
                  className="flex-1 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all group"
                  style={{ borderColor: "rgba(255,255,255,0.1)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${mc}60`)}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}>
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                    style={{ background: `${mc}18` }}>
                    <Upload className="w-7 h-7" style={{ color: mc }} />
                  </div>
                  <p className="text-sm font-semibold text-white/70">Click to upload</p>
                  <p className="text-xs text-white/30 mt-1">PDF · PPTX · KEY · ODP</p>
                  <input ref={slideInputRef} type="file" accept=".pdf,.pptx,.ppt,.key,.odp" className="hidden"
                    onChange={(e) => { if (e.target.files?.[0]) handleSlideUpload(e.target.files[0]); }} />
                </div>
              ) : analyzing ? (
                <div className="flex-1 flex flex-col items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin mb-3" style={{ color: mc }} />
                  <p className="text-sm font-semibold text-white/70">Analysing slides…</p>
                </div>
              ) : slideAnalyzed ? (
                <div className="flex-1 flex flex-col overflow-y-auto">
                  <div className="flex items-center gap-2 mb-3 pb-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    <FileText className="w-4 h-4" style={{ color: mc }} />
                    <p className="text-xs font-semibold text-white/70 truncate flex-1">{slideFile.name}</p>
                    <button onClick={() => { setSlideFile(null); setSlideAnalyzed(false); }}
                      className="text-[10px] text-white/30 hover:text-white/60">Change</button>
                  </div>
                  <p className="text-[10px] text-white/35 font-semibold uppercase tracking-wider mb-3">Script Outline</p>
                  {slideOutline.map((item, i) => (
                    <div key={i} className="flex gap-2.5 p-3 rounded-xl mb-2"
                      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <span className="w-5 h-5 rounded-full text-[10px] font-bold text-white flex items-center justify-center flex-shrink-0"
                        style={{ background: mc }}>{i+1}</span>
                      <p className="text-xs text-white/60 leading-relaxed">{item}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          )}

          {/* ── CONVERSATION / INTERVIEW / PRESENTATION: chat ──────────── */}
          {mode !== "Pronunciation" && (sessionStarted || mode !== "Presentation") && (
            <>
              {/* Chat messages */}
              <div className={cn("glass-card rounded-2xl p-5 overflow-y-auto min-h-0",
                sessionStarted ? "flex-1" : mode === "Presentation" ? "hidden" : "flex-1")}>
                {!sessionStarted || messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center px-8">
                    <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                      style={{ background: `${mc}15`, border: `1px solid ${mc}25` }}>
                      <Activity className="w-7 h-7" style={{ color: mc }} />
                    </div>
                    <p className="text-sm text-white/40 leading-relaxed">
                      {sessionStarted
                        ? "Your AI coach is preparing…"
                        : "Start the session. Your AI coach will guide the conversation — just speak naturally."}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, i) => (
                      <div key={i} className={cn("flex gap-3", msg.role === "user" && "flex-row-reverse")}
                        style={{ animation: "slide-up 0.3s cubic-bezier(0.16,1,0.3,1) forwards" }}>
                        {msg.role === "ai" && (
                          <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ background: mc }}>
                            <Activity className="w-3.5 h-3.5 text-white" />
                          </div>
                        )}
                        <div className={cn("max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
                          msg.role === "ai" ? "rounded-tl-sm" : "rounded-tr-sm")}
                          style={msg.role === "ai"
                            ? { background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.85)", border: "1px solid rgba(255,255,255,0.08)" }
                            : { background: `${mc}d0`, color: "white" }}>
                          {msg.text}
                        </div>
                      </div>
                    ))}

                    {/* AI thinking */}
                    {aiTyping && (
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ background: mc }}>
                          <Activity className="w-3.5 h-3.5 text-white" />
                        </div>
                        <div className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5"
                          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
                          {[0,1,2].map((i) => (
                            <span key={i} className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce"
                              style={{ animationDelay: `${i * 0.15}s` }} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI speaking indicator in chat */}
                    {aiSpeaking && !aiTyping && (
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ background: mc }}>
                          <Volume2 className="w-3.5 h-3.5 text-white animate-pulse" />
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl rounded-tl-sm"
                          style={{ background: `${mc}15`, border: `1px solid ${mc}25` }}>
                          <span className="text-xs font-medium" style={{ color: mc }}>Speaking…</span>
                          <div className="flex items-end gap-[2px]">
                            {[3,5,8,5,3,6,8].map((h,i) => (
                              <span key={i} className="rounded-full" style={{
                                display: "block", width: 2, height: h,
                                background: mc, animation: `waveform-bar 0.6s ease-in-out ${i*80}ms infinite`,
                              }} />
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Your turn divider */}
                    {showYourTurn && (
                      <div className="flex items-center gap-3 py-1">
                        <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
                        <span className="text-[10px] text-white/30 font-medium whitespace-nowrap">
                          {speechActive ? "🎙 Speak your answer" : "Your turn — speak or type"}
                        </span>
                        <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </div>

              {/* Interim transcript */}
              {(transcript || interimText) && sessionStarted && (
                <div className="flex-shrink-0 px-4 py-2.5 rounded-xl"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                  <p className="text-[10px] text-white/30 font-semibold uppercase tracking-wider mb-0.5">Transcript</p>
                  <p className="text-xs text-white/60 line-clamp-2">
                    {transcript}
                    {interimText && <span className="text-white/30 italic"> {interimText}</span>}
                  </p>
                </div>
              )}

              {/* Input */}
              <div className="flex-shrink-0 flex gap-3">
                <input type="text" value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  disabled={!sessionStarted || aiTyping || aiSpeaking}
                  placeholder={
                    !sessionStarted ? "Start the session first…" :
                    aiSpeaking ? "AI Coach is speaking — listen…" :
                    aiTyping   ? "AI Coach is responding…" :
                    speechActive ? "Speaking captured — or type here…" :
                    "Speak aloud, or type your response…"
                  }
                  className="flex-1 px-4 py-3 rounded-xl text-sm text-white/80 outline-none transition-all disabled:opacity-40 placeholder:text-white/25"
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = `${mc}50`)}
                  onBlur={(e) => (e.target.style.borderColor = "rgba(255,255,255,0.08)")}
                />
                <button onClick={sendMessage}
                  disabled={!sessionStarted || !input.trim() || aiTyping || aiSpeaking}
                  className="w-11 h-11 flex items-center justify-center rounded-xl text-white transition-all disabled:opacity-30 flex-shrink-0 press-effect"
                  style={{ background: mc }}>
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </>
          )}
        </div>
        </div>
      )}

      {/* ── Bottom metric strip (Yoodli-inspired) ────────────────────────── */}
      <div className="flex-shrink-0 mt-3 glass-card rounded-xl grid grid-cols-2 sm:flex sm:overflow-hidden">
        <MetricPill label="Fluency"       value={sessionStarted ? liveFeedback.fluency : 0}       prev={prevFeedback.fluency}       color="#5C729B" />
        <MetricPill label="Pronunciation" value={sessionStarted ? liveFeedback.pronunciation : 0} prev={prevFeedback.pronunciation} color="#79738C" />
        <MetricPill label="Eye Contact"   value={sessionStarted ? liveFeedback.eye_contact : 0}   prev={prevFeedback.eye_contact}   color="#4D7A59" />
        <MetricPill label="Confidence"    value={sessionStarted ? liveFeedback.confidence : 0}    prev={prevFeedback.confidence}    color="#9C6A28" />
        <div className="col-span-2 sm:col-span-1 flex items-center gap-2.5 px-3 sm:px-4 py-3 flex-1">
          <div className="flex-1">
            <div className="flex items-center justify-between gap-1 mb-1">
              <span className="text-[10px] text-white/40 font-semibold uppercase tracking-wider truncate">Pace</span>
              <span className="text-sm font-bold text-white/80 flex-shrink-0">{wpm > 0 ? `${wpm} WPM` : "–"}</span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
              {wpm > 0 && (
                <div className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.min(100,(wpm/200)*100)}%`,
                    background: wpm > 160 ? "linear-gradient(90deg, #f9731660, #ef4444)" :
                               wpm < 100  ? "linear-gradient(90deg, #f59e0b60, #f59e0b)" :
                                            "linear-gradient(90deg, #22c55e60, #22c55e)",
                  }} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-[calc(100vh-60px)]">
        <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: "#5C729B", borderTopColor: "transparent" }} />
      </div>
    }>
      <SessionContent />
    </Suspense>
  );
}
