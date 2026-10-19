// The session's script and helpers: what the partner says when it has no LLM or plan,
// and the live mood and pace read-outs. Plain data and pure functions (no React).

// ── Random topics (RandomTopicGen-inspired) ───────────────────────────────────
export const RANDOM_TOPICS = [
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

// ── Mode content ──────────────────────────────────────────────────────────────
export const MODE_PROMPTS: Record<string, string[]> = {
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
  // Only used when the deck's Q&A plan couldn't be loaded
  Presentation: [
    "Thank you for your presentation. Let's open the floor. What is the one thing you want the audience to remember?",
    "Could you give a concrete example that supports your main point?",
    "What are the limitations of your approach?",
    "What would you do next if you had more time?",
  ],
};

export const MODE_TITLES: Record<string, string> = {
  Conversation: "Daily conversation",
  Interview: "Mock interview",
  Presentation: "Presentation Q&A",
};

export const MODE_ACKS: Record<string, string[]> = {
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
    "Thanks, that's clear. ",
    "Good answer. Another question from the audience: ",
    "Interesting. Next question: ",
  ],
};

export const CHECKIN_MESSAGES = [
  "Just checking in — are you still there? Take your time, no rush at all.",
  "It looks like you've gone quiet. Everything okay? We can continue whenever you're ready.",
  "No pressure — would you like me to repeat the question, or shall we try a different topic?",
];

// ── Helpers ───────────────────────────────────────────────────────────────────
export const BACKCHANNEL_TEXTS = ["Mm-hmm.", "I see.", "Right.", "Yeah.", "Go on.", "Interesting."];
// Hesitation sounds only: ordinary words ("like", "so", "right") and Manglish particles
// aren't disfluencies (the server's analysis handles fillers in context)
export const FILLER_WORDS = new Set(["um", "umm", "uh", "uhh", "er", "err", "erm", "ah", "hmm"]);

export const clamp  = (v: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, v));
export const ema    = (prev: number, next: number, a = 0.2) => prev * (1 - a) + next * a;

// ── Mood inference ────────────────────────────────────────────────────────────
// Rule-based, not a trained classifier — reads MediaPipe's ARKit-style face
// blendshape coefficients (52 facial-muscle activation scores from the same
// FaceLandmarker already running for the mesh overlay) and scores five
// presentation-relevant states against each other. Good enough to be an
// honest, real-time signal without pretending to be a full emotion model.
export type Blendshape = { categoryName: string; score: number };

export const MOOD_STATES = {
  Engaged:     { color: "#3E6FB0" },
  Confident:   { color: "#2F7A4F" },
  Enthusiastic:{ color: "#A8620F" },
  Tense:       { color: "#C2342C" },
  Uncertain:   { color: "#6B4FC4" },
} as const;
export type MoodLabel = keyof typeof MOOD_STATES;

export function inferMood(cats: Blendshape[]): { label: MoodLabel; score: number } {
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

/** Speaking pace so far, shown under the transcript (the analysis measures it properly). */
export function paceWpm(words: number, elapsedSec: number): number {
  return elapsedSec < 2 || words < 3 ? 0 : Math.round((words / elapsedSec) * 60);
}
