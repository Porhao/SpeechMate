"use client";

// Reference: how every number in SpeechMate is worked out, in plain words first with the
// technical method, a worked example and the sources behind it one click away. Kept in sync
// with the backend code paths in each row's "source" (and docs/confidence-model.md).

import { useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { PageHeader } from "@/components/ui/kit";

type Pillar = "voice" | "language" | "body" | "confidence" | "summary";
type Row = {
  metric: string; meaning: string; method: string; unit: string; range: string; source: string;
  pillar?: Pillar; example?: string; refs?: number[];
};

const PILLARS: { id: Pillar | "all"; label: string }[] = [
  { id: "all", label: "Everything" }, { id: "voice", label: "Voice" }, { id: "language", label: "Language" },
  { id: "body", label: "Body language" }, { id: "confidence", label: "Confidence" }, { id: "summary", label: "Scores & feedback" },
];

const LIVE: Row[] = [
  { metric: "Transcript", meaning: "What you said, word for word (fillers kept)", pillar: "language", refs: [1, 2],
    method: "Mesolitica Malaysian Whisper large-v3-turbo via faster-whisper (int8, 8 CPU threads, beam 5, automatic language detection, voice-activity filter). During a session each turn is resampled to 16 kHz by the browser's filtered resampler and sent with what it answers (the AI's last line, the role or deck) so topic words are heard right. Fallback: OpenAI Whisper.",
    unit: "text + word timings", range: "Benchmark: 6.1% WER (Malay 6.4%, Malaysian English 4.0%, Manglish 17.0%)", source: "live/asr.py",
    example: "Asked “What tools did you use?”, Whisper is told the question, so “Power BI” is less likely to come out as “power be eye”." },
  { metric: "Speaking rate", meaning: "How fast you talk", pillar: "voice", refs: [3, 4],
    method: "Words ÷ your own talking time × 60. Silences of 3 s or more are turn changes (the AI talking), so they don't count as your time.",
    unit: "words/min", range: "120–160 comfortable · flagged > 165 or < 110", source: "live/speech.py",
    example: "300 words in a 4-minute conversation where the AI talked for 1.5 minutes → 300 ÷ 2.5 = 120 words/min." },
  { metric: "Articulation rate", meaning: "Pace while actually speaking", pillar: "voice", refs: [4],
    method: "Words ÷ the time your words take (all pauses removed) × 60", unit: "words/min", range: "—", source: "live/speech.py",
    example: "120 words with 50 s of actual sound → 144 words/min." },
  { metric: "Pauses", meaning: "Short silences between your words", pillar: "voice", refs: [4],
    method: "Gaps of 0.25–3 s between word timestamps (or ffmpeg silence detection at −35 dB when timings are missing). Start/end silence and gaps of 3 s+ (turn changes) are ignored.",
    unit: "count, seconds", range: "~15–20 a minute is normal speech", source: "live/speech.py",
    example: "Gaps of 0.4, 0.9 and 2.1 s are pauses; a 7 s gap while the AI answers is not." },
  { metric: "Fluency score", meaning: "Pace and continuity combined", pillar: "voice", refs: [4],
    method: "100 − |wpm − 135| × 0.5 − min(2 × pauses, 30)", unit: "0–100", range: "≥ 80 Excellent · ≥ 65 Good · ≥ 50 Fair", source: "live/speech.py",
    example: "120 wpm and 10 pauses → 100 − 7.5 − 20 = 72.5 → Good." },
  { metric: "Filler words", meaning: "um, uh, err… and “like”, “you know”, “macam”, “sebenarnya”", pillar: "language", refs: [5],
    method: "Hesitation sounds always count; discourse markers only at a clause start or next to a comma, so “I like data”, “tapi” and particles like “lah” are not fillers.",
    unit: "count, per minute", range: "< 3/min fine · flagged ≥ 3/min", source: "live/speech.py",
    example: "15 fillers in a 5-minute session → 3 a minute → flagged." },
  { metric: "Stuttering", meaning: "Repetitions, blocks and stretched sounds", pillar: "language", refs: [6, 7],
    method: "Repetition: the same word twice within 0.6 s. Block: a 1.2–3 s silence mid-answer (longer is a turn change). Prolongation: a steady voiced sound ≥ 0.35 s (librosa RMS + zero-crossing rate). Score = 8 × events.",
    unit: "0–100 (higher = more)", range: "0 None · < 25 Mild · < 50 Moderate · ≥ 50 Severe", source: "live/speech.py",
    example: "“I I think” (1 repetition) + two 1.5 s blocks = 3 events × 8 = 24 → Mild." },
  { metric: "Pronunciation", meaning: "How clearly words were articulated", pillar: "voice", refs: [8],
    method: "Wav2Vec2 (facebook/wav2vec2-base-960h) CTC confidence averaged over each word's span; words < 75 marked unclear; +5% allowance for Malaysian English.",
    unit: "0–100", range: "Flagged < 80 or ≥ 3 unclear words", source: "live/pronunciation.py",
    example: "A raw 80 for mostly-English Malaysian speech → 84 after the accent allowance." },
  { metric: "Vocal variety", meaning: "Does your voice move, or is it flat?", pillar: "voice", refs: [9],
    method: "Pitch (librosa YIN, 70–400 Hz) over voiced 20 ms frames; the spread of pitch in semitones around your median (octave errors trimmed).",
    unit: "semitones (SD)", range: "2–7 lively · < 2 sounds monotone", source: "live/extra_metrics.py",
    example: "A spread of 1.5 semitones → sounds monotone; 4 → lively." },
  { metric: "Volume & steadiness", meaning: "Loud enough, and steady?", pillar: "voice",
    method: "RMS level of voiced frames in dBFS; steadiness = SD of that level across the recording.", unit: "dBFS ± dB",
    range: "Louder than −35 dBFS · variation ≤ 7 dB", source: "live/extra_metrics.py",
    example: "−40 dBFS → too quiet: move closer to the mic or speak up." },
  { metric: "Vocabulary richness", meaning: "How varied your words are", pillar: "language", refs: [10],
    method: "Moving-average type-token ratio (MATTR) over 50-word windows: fair across short and long sessions.",
    unit: "0–1", range: "≥ 0.65 good", source: "live/extra_metrics.py",
    example: "34 different words in a typical 50-word stretch → 0.68 → good." },
  { metric: "Hedging", meaning: "Phrases that make you sound unsure", pillar: "language", refs: [11],
    method: "“I think, maybe, kind of, sort of, I guess, probably, perhaps, I'm not sure, mungkin…” per 100 words.", unit: "per 100 words",
    range: "< 1 fine · flagged ≥ 2", source: "live/extra_metrics.py",
    example: "3 hedges in 150 words → 2 per 100 → flagged." },
  { metric: "Language mix", meaning: "English vs Bahasa Melayu, Manglish particles", pillar: "language",
    method: "Word ratio against a ~190-word BM/Manglish lexicon; code-switching when both languages are ≥ 15%.", unit: "ratios",
    range: "Informational, not scored", source: "live/language.py",
    example: "60 of 100 words English, 40 Malay → 60% / 40%, code-switching." },
  { metric: "Eye contact", meaning: "How often you look at the lens", pillar: "body", refs: [19, 12, 13],
    method: "MediaPipe Face Mesh iris position on 60 sampled frames → camera / left / right / down; score = % of frames toward the camera.",
    unit: "0–100", range: "Flagged < 70", source: "live/vision.py",
    example: "42 of 60 frames at the lens → 70%." },
  { metric: "Posture", meaning: "Upright, level, steady", pillar: "body", refs: [19, 14],
    method: "MediaPipe Pose: head tilt from the ear line, shoulder height difference, torso movement across frames; score = mean of the three.",
    unit: "0–100", range: "Flagged < 75", source: "live/vision.py",
    example: "Head 80, shoulders 90, stability 70 → 80." },
  { metric: "Hand gestures", meaning: "Do you use your hands?", pillar: "body", refs: [14],
    method: "MediaPipe Pose wrists on sampled frames: share of frames where a visible hand moved > 15% of shoulder width since the last frame.",
    unit: "% of frames", range: "20–60% natural · hands out of view cap the score, they aren't penalised", source: "live/extra_metrics.py",
    example: "Hands moving in 15 of 60 frames → 25% → natural." },
  { metric: "Head steadiness", meaning: "Nodding or bobbing a lot?", pillar: "body", refs: [14],
    method: "SD of the nose position relative to the shoulder midpoint, normalised by shoulder width.", unit: "0–100", range: "≥ 70", source: "live/extra_metrics.py" },
  { metric: "Response time", meaning: "How quickly you start answering", pillar: "confidence",
    method: "In the browser: time from the end of the AI's turn to the first sound of your answer (median over the session).",
    unit: "seconds", range: "≤ 2 s good · flagged > 3 s", source: "session page",
    example: "You started after 1.2, 2.5 and 4.0 s → median 2.5 s → okay." },
  { metric: "Facial expression", meaning: "Dominant emotion and tension", pillar: "confidence", refs: [15],
    method: "Face crop (MediaPipe) → ViT expression classifier (trpakov/vit-face-expression) on ~12 frames; tension = share of fearful + angry + sad.",
    unit: "label, 0–100", range: "Tension flagged ≥ 30", source: "live/vision.py",
    example: "3 of 12 frames read as tense → tension 25 → fine." },
  { metric: "Lighting & contrast", meaning: "How well you're lit on camera", pillar: "body",
    method: "In the browser, once a second: face-region brightness (MediaPipe face box), whole-frame brightness, face vs. background (backlight) and contrast.",
    unit: "0–255 luminance, contrast", range: "Face 90–190 · contrast ≥ 30 · face ≥ background − 15", source: "lib/lighting.ts",
    example: "Face brightness 70 with a bright window behind → too dark, backlit." },
  { metric: "Confidence", meaning: "How confident you come across", pillar: "confidence", refs: [16, 17, 13],
    method: "Weighted average of 11 cues, each scored 0–100: pace 10%, hesitation pauses 12%, word repetitions 8%, stutter blocks 7%, fillers 8%, response time 5%, confident expression 10%, relaxed face 8%, posture 11%, body steadiness 7%, eye contact 14%. Counts are per minute of your own talking time. Cues not measured are left out (re-weighted); under 30% of the evidence gives no score. See docs/confidence-model.md.",
    unit: "0–100", range: "≥ 75 High · ≥ 50 Medium · < 50 Low", source: "live/scoring.py",
    example: "Pace 100 (140 wpm), pauses 100 (15/min), posture 80, eye contact 50; nothing else measured → (100×.10 + 100×.12 + 80×.11 + 50×.14) ÷ .47 = 80.4 → High, from 47% of the evidence." },
  { metric: "Overall score", meaning: "One summary number", pillar: "summary",
    method: "0.25 fluency + 0.25 pronunciation + 0.20 confidence + 0.15 eye contact + 0.15 posture, re-weighted over the parts measured (listed as “scored on”).",
    unit: "0–100", range: "≥ 85 Excellent · ≥ 70 Good · ≥ 55 Fair", source: "live/scoring.py",
    example: "Fluency 70, pronunciation 80, confidence 65, eye contact 60, posture 75 → 70.8 → Good." },
  { metric: "Gaze tunneling", meaning: "Do you look away when you stumble?", pillar: "confidence", refs: [18],
    method: "Pearson r between gaze aversion and disfluency events per 5 s window, computed in the browser during the session.",
    unit: "r (−1…1)", range: "> 0.4 strong link · > 0.15 some link", source: "session page",
    example: "r = 0.45 → you tend to look away right when you hesitate." },
  { metric: "Pillars", meaning: "The four simple scores on your results", pillar: "summary",
    method: "Voice & delivery (fluency, pace, pronunciation, vocal variety, volume) · Language & clarity (fillers, vocabulary, hedging, repetitions) · Body language (eye contact, posture, gestures, head) · Confidence & presence (confidence, expression, response time, gaze tunneling). Each metric is mapped to 0–100 against its comfortable range; a pillar is the mean of the metrics actually measured.",
    unit: "0–100", range: "≥ 75 Strong · ≥ 55 Okay · < 55 Work on this", source: "live/extra_metrics.py",
    example: "Voice metrics 80, 60 and 70 → Voice & delivery 70 → Okay." },
  { metric: "Answer feedback", meaning: "Was what you said any good? (Interview, Q&A)", pillar: "summary",
    method: "Each AI question is paired with your answer (shown as “You said”). The LLM rates whether it answered the question, how easy it was to follow (STAR for interviews; answer-first for Q&A) and its real details 1–5, quotes your words, gives one concrete next step, and rewrites a stronger answer using only facts you said. Without an LLM: keyword overlap, STAR cue words, numbers and length.",
    unit: "1–5 each", range: "—", source: "practice_plans.py",
    example: "“I helped my team” → Next time: say what you did and the result, e.g. “I rebuilt the report and cut errors by half”." },
  { metric: "Language tips", meaning: "Grammar and word choice (Conversation)", pillar: "summary",
    method: "The LLM picks up to 5 real issues from your turns (Malaysian English expressions are not “errors”), each with what you said, a more natural version and why, plus conversation tips tied to what you said. Without an LLM: reply length and asking questions back.",
    unit: "—", range: "—", source: "practice_plans.py",
    example: "You said “I'm so thinking that…” → Try saying “I'm not sure whether…”." },
  { metric: "Recommendations", meaning: "What to work on next", pillar: "summary",
    method: "Each measured issue becomes a candidate with its evidence, a drill and a target relative to your current value, ranked by distance from the comfortable range; the local LLM picks and words the top 3 but may only use measured candidates. The first is shown as “Your #1 focus”.",
    unit: "—", range: "Max 3 per session", source: "live/coaching.py",
    example: "Eye contact 30% (comfortable ≥ 70%) → #1 focus: hold eye contact with the lens; next time aim above 45%." },
];

const PRACTICE: Row[] = [
  { metric: "Deck insights", meaning: "What the deck says, before you present it",
    method: "Slide text (python-pptx / pdftotext) → LLM summary, main message, structure, the key point each slide must land, suggestions; words per slide (text-heavy > 70 words or > 9 lines). The Q&A questions are prepared at the same time.",
    unit: "—", range: "Talk length estimate: 0.75–1.5 min per slide", source: "deck_insights.py",
    example: "A 10-slide deck → aim for about 8–15 minutes; slide 4 with 120 words is flagged as text-heavy." },
  { metric: "Slide match", meaning: "Did what you said fit the slide on screen?",
    method: "The browser notes when each slide went up; the transcript's word timings are split at those moments, so each slide gets the words spoken while it showed (revisits add up). Rules: share of the slide's key words (key point weighted double, title, text) you said. The local LLM then rates the match 1–5, says what you covered (quoting you), what you left out and one tip.",
    unit: "% key words, 1–5", range: "≥ 40% covered well · ≥ 20% partly · below = missed the point; on screen but silent = nothing said", source: "live/talk.py",
    example: "Slide 2's point is “Most students sleep under six hours”; you only said “so here is our survey” → 1 of 6 key words → missed the point; tip: say the finding out loud." },
  { metric: "Time per slide", meaning: "How long each slide was on screen", method: "Sum of the spans between slide changes (a revisited slide adds up); slides never shown are listed as not shown.",
    unit: "seconds", range: "≈ 45–90 s per slide is comfortable", source: "live/talk.py",
    example: "Slide 1 shown 0:00–0:40 and again 3:10–3:30 → 60 s." },
  { metric: "Q&A questions", meaning: "What the audience would ask",
    method: "LLM writes 5–6 audience questions from the deck insights (clarify, challenge, evidence, limitations, next steps), each tied to a slide with what a strong answer contains; fallback: the insights' likely questions + key points",
    unit: "—", range: "—", source: "practice_plans.py" },
];


// The sources behind the methods above (APA 7). Check page numbers against the originals
// before quoting them in a report.
const REFERENCES: string[] = [
  "Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. Proceedings of the 40th International Conference on Machine Learning (ICML), PMLR 202.",
  "Conneau, A., Ma, M., Khanuja, S., Zhang, Y., Axelrod, V., Dalmia, S., Riesa, J., Rivera, C., & Bapna, A. (2023). FLEURS: Few-shot learning evaluation of universal representations of speech. 2022 IEEE Spoken Language Technology Workshop (SLT).",
  "Tauroza, S., & Allison, D. (1990). Speech rates in British English. Applied Linguistics, 11(1), 90–105.",
  "Kormos, J., & Dénes, M. (2004). Exploring measures and perceptions of fluency in the speech of second language learners. System, 32(2), 145–164.",
  "Clark, H. H., & Fox Tree, J. E. (2002). Using uh and um in spontaneous speaking. Cognition, 84(1), 73–111.",
  "Shriberg, E. E. (1994). Preliminaries to a theory of speech disfluencies [Doctoral dissertation, University of California, Berkeley].",
  "Riley, G. D. (2009). SSI-4: Stuttering Severity Instrument (4th ed.). Pro-Ed.",
  "Baevski, A., Zhou, H., Mohamed, A., & Auli, M. (2020). wav2vec 2.0: A framework for self-supervised learning of speech representations. Advances in Neural Information Processing Systems, 33.",
  "de Cheveigné, A., & Kawahara, H. (2002). YIN, a fundamental frequency estimator for speech and music. The Journal of the Acoustical Society of America, 111(4), 1917–1930.",
  "Covington, M. A., & McFall, J. D. (2010). Cutting the Gordian knot: The moving-average type–token ratio (MATTR). Journal of Quantitative Linguistics, 17(2), 94–100.",
  "Hyland, K. (1998). Hedging in scientific research articles. John Benjamins.",
  "Kartynnik, Y., Ablavatski, A., Grishchenko, I., & Grundmann, M. (2019). Real-time facial surface geometry from monocular video on mobile GPUs. arXiv:1907.06724.",
  "Kleinke, C. L. (1986). Gaze and eye contact: A research review. Psychological Bulletin, 100(1), 78–100.",
  "Bazarevsky, V., Grishchenko, I., Raveendran, K., Zhu, T., Zhang, F., & Grundmann, M. (2020). BlazePose: On-device real-time body pose tracking. arXiv:2006.10204.",
  "Dosovitskiy, A., Beyer, L., Kolesnikov, A., Weissenborn, D., Zhai, X., Unterthiner, T., Dehghani, M., Minderer, M., Heigold, G., Gelly, S., Uszkoreit, J., & Houlsby, N. (2021). An image is worth 16x16 words: Transformers for image recognition at scale. International Conference on Learning Representations (ICLR).",
  "Scherer, K. R., London, H., & Wolf, J. J. (1973). The voice of confidence: Paralinguistic cues and audience evaluation. Journal of Research in Personality, 7(1), 31–44.",
  "Kimble, C. E., & Seidel, S. D. (1991). Vocal signs of confidence. Journal of Nonverbal Behavior, 15(2), 99–105.",
  "Doherty-Sneddon, G., & Phelps, F. G. (2005). Gaze aversion: A response to cognitive or social difficulty? Memory & Cognition, 33(4), 727–733.",
  "Lugaresi, C., Tang, J., Nash, H., McClanahan, C., Uboweja, E., Hays, M., Zhang, F., Chang, C.-L., Yong, M. G., Lee, J., Chang, W.-T., Hua, W., Georg, M., & Grundmann, M. (2019). MediaPipe: A framework for building perception pipelines. arXiv:1906.08172.",
];

function MetricCard({ r }: { r: Row }) {
  return (
    <details className="group rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
      <summary className="list-none cursor-pointer p-4 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-semibold" style={{ color: "var(--ink)" }}>{r.metric}</p>
          <p className="text-sm mt-0.5" style={{ color: "var(--ink-2)" }}>{r.meaning}</p>
          <p className="text-xs mt-2 inline-block px-2.5 py-1 rounded-full" style={{ background: "var(--surface-3)", color: "var(--ink-2)" }}>{r.range}</p>
        </div>
        <span className="flex items-center gap-1 text-xs font-semibold flex-shrink-0 mt-1" style={{ color: "var(--accent-ink)" }}>
          <span className="hidden sm:inline group-open:hidden">Show how</span>
          <span className="hidden sm:group-open:inline">Hide</span>
          <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
        </span>
      </summary>
      <div className="px-4 pb-4 space-y-3 text-sm" style={{ borderTop: "1px solid var(--line-2)" }}>
        <p className="pt-3 leading-relaxed" style={{ color: "var(--ink-3)" }}><b>How it&rsquo;s worked out:</b> {r.method}</p>
        {r.example && (
          <p className="p-3 rounded-md leading-relaxed" style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}>
            <b>Worked example:</b> {r.example}
          </p>
        )}
        <p className="text-xs flex flex-wrap gap-x-4 gap-y-1" style={{ color: "var(--muted)" }}>
          <span>Unit: {r.unit}</span>
          <span>Code: <code className="font-mono">{r.source}</code></span>
          {r.refs?.length ? <span>Sources: {r.refs.map((n) => <a key={n} href={`#ref-${n}`} className="underline mr-1" style={{ color: "var(--accent-ink)" }}>[{n}]</a>)}</span> : null}
        </p>
      </div>
    </details>
  );
}

function MetricList({ rows, withFilters }: { rows: Row[]; withFilters?: boolean }) {
  const [q, setQ] = useState("");
  const [pillar, setPillar] = useState<Pillar | "all">("all");
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => (pillar === "all" || r.pillar === pillar)
      && (!needle || `${r.metric} ${r.meaning} ${r.method}`.toLowerCase().includes(needle)));
  }, [rows, q, pillar]);
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <label className="relative flex-1 max-w-sm">
          <span className="sr-only">Search metrics</span>
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted)" }} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search, e.g. pauses, eye contact…"
            className="w-full pl-9 pr-3 py-2.5 rounded-md text-sm outline-none" style={{ background: "var(--surface)", border: "1px solid var(--line-strong)", color: "var(--ink)" }} />
        </label>
        {withFilters && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by pillar">
            {PILLARS.map((p) => (
              <button key={p.id} onClick={() => setPillar(p.id)} aria-pressed={pillar === p.id}
                className={`nav-pill px-3.5 py-1.5 rounded-full text-sm font-medium ${pillar === p.id ? "nav-pill-active" : ""}`}>
                {p.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {shown.length === 0
        ? <p className="text-sm" style={{ color: "var(--muted)" }}>Nothing matches “{q}”.</p>
        : <div className="grid md:grid-cols-2 gap-3 items-start">{shown.map((r) => <MetricCard key={r.metric} r={r} />)}</div>}
    </div>
  );
}

type AIRow = { fn: string; used: string; model: string; input: string; output: string; fallback: string; quality: string };

// Every AI function in the system: what runs it, and how its quality is checked
const AI_FUNCTIONS: AIRow[] = [
  { fn: "Speech recognition", used: "All three", model: "Mesolitica Malaysian Whisper large-v3-turbo (faster-whisper, CPU int8)",
    input: "16 kHz audio", output: "Transcript + word timings", fallback: "OpenAI Whisper → typed input (live turns)", quality: "WER by language (benchmarked 6.1%)" },
  { fn: "Code-switch re-check", used: "All three", model: "Mesolitica wav2vec2-xls-r-300m-mixed",
    input: "Audio not confidently English", output: "Malay / mixed transcript", fallback: "Whisper transcript + warning", quality: "WER on mixed speech" },
  { fn: "AI partner (conversation)", used: "Conversation", model: "Ollama qwen2.5:3b",
    input: "Last 12 turns + topic", output: "2–3 spoken sentences", fallback: "Scripted prompts", quality: "UAT naturalness rating" },
  { fn: "Interview question plan", used: "Interview", model: "Ollama qwen2.5:3b (JSON, validated)",
    input: "Role, company, level, type, background, job description, resume text", output: "6–8 questions + what each tests + what a strong answer has",
    fallback: "Behavioural / technical question bank", quality: "Relevance rating by users / supervisor" },
  { fn: "Q&A question plan", used: "Presentation", model: "Ollama qwen2.5:3b (JSON, validated)",
    input: "Deck insights + audience", output: "5–6 audience questions tied to slides (prepared once, right after the deck is analysed, so the Q&A starts instantly)", fallback: "Likely questions + key points from the insights", quality: "Relevance rating" },
  { fn: "Interviewer / moderator turns", used: "Interview, Presentation", model: "Server-side plan + qwen2.5:3b for the one-line reaction",
    input: "Plan, progress, last answer", output: "Reaction + next planned question, or one follow-up if the answer was < 25 words", fallback: "Fixed reaction + planned question", quality: "Plan adherence is guaranteed by code" },
  { fn: "Partner voice", used: "All three (live)", model: "Kokoro-82M (Kokoro-FastAPI)", input: "Reply text", output: "Speech", fallback: "OpenAI TTS → Malaysian TTS → browser voice", quality: "MOS-style naturalness rating" },
  { fn: "Deck insights", used: "Presentation", model: "Ollama qwen2.5:3b", input: "Slide text (.pptx / .pdf)", output: "Summary, structure, key point per slide, suggestions, likely questions",
    fallback: "Rule-based from slide text", quality: "Supervisor rating of summaries" },
  { fn: "Pronunciation", used: "All three", model: "Wav2Vec2 base-960h CTC confidence", input: "Audio + transcript", output: "0–100 + unclear words", fallback: "Unavailable", quality: "Correlation with human ratings ≥ 0.7" },
  { fn: "Prosody", used: "All three", model: "librosa YIN + RMS (signal processing)", input: "Audio", output: "Pitch variation, loudness, steadiness", fallback: "Unavailable", quality: "Agreement with Praat on sample clips" },
  { fn: "Eye contact, posture, gestures", used: "All three", model: "MediaPipe Face Mesh (iris) + Pose", input: "60 sampled video frames", output: "Scores 0–100, gaze direction, hand movement", fallback: "Unavailable", quality: "Accuracy vs. manual coding ≥ 0.8" },
  { fn: "Facial expression", used: "All three", model: "ViT trpakov/vit-face-expression", input: "~12 face crops", output: "Emotion distribution, tension", fallback: "Unavailable", quality: "Accuracy vs. manual labels" },
  { fn: "Answer / language feedback", used: "All three", model: "Ollama qwen2.5:3b (JSON, validated)", input: "Question–answer pairs + plan", output: "Per-answer ratings, improvement, stronger answer; or language corrections",
    fallback: "Rule-based (STAR cues, specificity, length)", quality: "Likert: specific, actionable, accurate" },
  { fn: "Coaching plan", used: "All three", model: "Measured candidates → qwen2.5:3b picks top 3", input: "Every measured issue + goal", output: "3 drills with evidence and targets", fallback: "Ranked rule-based list", quality: "Likert: actionable; can't invent unmeasured issues" },
  { fn: "Talk vs slides", used: "Presentation", model: "Ollama qwen2.5:3b (JSON, validated)", input: "Each slide's title, text and key point + what you said while it showed",
    output: "Per slide: match 1–5, what you covered, what you left out, a tip; summary", fallback: "Key-word coverage per slide", quality: "Agreement with a supervisor's per-slide rating" },
];

const EVALUATION = [
  { component: "Speech recognition", metric: "Word error rate (WER), split by Malay / English / mixed", truth: "FLEURS ms_my (real speakers) + Malaysian-accented and Manglish clips",
    target: "Clear WER reduction vs. a standard Whisper baseline", result: "Done — 6.1% vs 51.3% (docs/benchmarks)" },
  { component: "Pronunciation", metric: "Pearson / Spearman correlation with human ratings; precision/recall of unclear words", truth: "2–3 raters on ~20 clips",
    target: "Correlation ≥ 0.7", result: "Planned" },
  { component: "Stutter & filler detection", metric: "Precision, recall, F1; false-positive rate reported separately", truth: "Manually annotated repetitions, blocks, prolongations, fillers",
    target: "F1 ≥ 0.75, low false positives", result: "Planned" },
  { component: "Eye contact / gaze", metric: "Agreement with a human coding the same video; gaze-tunneling correlation vs. rated naturalness", truth: "Manually coded video",
    target: "Accuracy ≥ 0.8", result: "Planned" },
  { component: "Posture & expression", metric: "Classification accuracy vs. observation", truth: "Manual labels per clip",
    target: "—", result: "Planned" },
  { component: "Confidence", metric: "Spearman correlation of the 11-cue score with the mean of 2–3 raters' 1–7 confidence ratings; rater agreement (ICC); per-cue correlations", truth: "30–50 recorded answers rated blind (docs/confidence-model.md)",
    target: "ρ ≥ 0.5", result: "Planned" },
  { component: "Overall score", metric: "Correlation with a supervisor's rating", truth: "Supervisor ratings", target: "—", result: "Planned" },
  { component: "Feedback quality", metric: "5-point Likert: specificity, actionability, perceived accuracy (no BLEU/ROUGE — it's coaching text)", truth: "User acceptance testing",
    target: "Significant gain over generic advice", result: "Planned" },
];

const TABS = [
  { id: "live", label: "Session metrics" },
  { id: "practice", label: "Presentation practice" },
  { id: "ai", label: "AI functions" },
  { id: "evaluation", label: "Project evaluation" },
] as const;

function AIMatrix() {
  return (
    <div className="overflow-x-auto" style={{ border: "1px solid var(--line)" }}>
      <table className="w-full text-sm min-w-[980px]">
        <thead>
          <tr style={{ background: "var(--surface-2)" }}>
            {["AI function", "Used in", "Model", "Input → output", "If unavailable", "How quality is checked"].map((h) => (
              <th key={h} className="text-left text-[11px] font-semibold uppercase tracking-wide px-3 py-2 text-[var(--muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {AI_FUNCTIONS.map((r) => (
            <tr key={r.fn} className="align-top" style={{ borderTop: "1px solid var(--line)", background: "var(--surface)" }}>
              <td className="px-3 py-2.5 font-semibold text-[var(--ink)] w-[14%]">{r.fn}</td>
              <td className="px-3 py-2.5 text-[var(--ink-2)] w-[11%]">{r.used}</td>
              <td className="px-3 py-2.5 text-[var(--ink-3)] w-[17%]">{r.model}</td>
              <td className="px-3 py-2.5 text-[var(--ink-3)]">{r.input} → {r.output}</td>
              <td className="px-3 py-2.5 text-[var(--ink-2)] w-[15%]">{r.fallback}</td>
              <td className="px-3 py-2.5 text-[var(--ink-2)] w-[15%]">{r.quality}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MethodologyPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("live");

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1200px] mx-auto space-y-6">
      <PageHeader eyebrow="Reference" title="How it’s measured">
        Every number in SpeechMate in plain words, with how it&rsquo;s worked out, a worked example and the research behind
        it one click away. Anything a model couldn&rsquo;t measure is shown as unavailable in your results, never estimated.
      </PageHeader>

      <nav className="flex flex-wrap gap-1.5" aria-label="Reference sections">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} aria-pressed={tab === t.id}
            className={`nav-pill px-4 py-2 rounded-full text-sm font-medium ${tab === t.id ? "nav-pill-active" : ""}`}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "live" && <MetricList rows={LIVE} withFilters />}
      {tab === "practice" && <MetricList rows={PRACTICE} />}
      {tab === "ai" && <AIMatrix />}
      {tab === "evaluation" && (
        <div className="overflow-x-auto" style={{ border: "1px solid var(--line)" }}>
          <table className="w-full text-sm min-w-[860px]">
            <thead>
              <tr style={{ background: "var(--surface-2)" }}>
                {["Component", "Evaluation metric", "Ground truth", "Target", "Status"].map((h) => (
                  <th key={h} className="text-left text-[11px] font-semibold uppercase tracking-wide px-3 py-2 text-[var(--muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {EVALUATION.map((r) => (
                <tr key={r.component} className="align-top" style={{ borderTop: "1px solid var(--line)", background: "var(--surface)" }}>
                  <td className="px-3 py-2.5 font-semibold text-[var(--ink)] w-[16%]">{r.component}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-3)]">{r.metric}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-2)]">{r.truth}</td>
                  <td className="px-3 py-2.5 text-[var(--ink-2)]">{r.target}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap" style={{ color: r.result.startsWith("Done") ? "var(--ok)" : "var(--muted)" }}>{r.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section aria-labelledby="refs" className="pt-6" style={{ borderTop: "1px solid var(--line)" }}>
        <h2 id="refs" className="font-display text-2xl" style={{ color: "var(--ink)" }}>References</h2>
        <p className="text-sm mt-1 mb-4" style={{ color: "var(--muted)" }}>The research and tools behind the methods above (APA 7). Numbers in [brackets] link here.</p>
        <ol className="space-y-3 max-w-3xl">
          {REFERENCES.map((r, i) => (
            <li key={i} id={`ref-${i + 1}`} className="flex gap-3 text-sm leading-relaxed scroll-mt-28" style={{ color: "var(--ink-3)" }}>
              <span className="font-semibold tabular-nums flex-shrink-0" style={{ color: "var(--muted)" }}>[{i + 1}]</span>{r}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
