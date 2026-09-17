"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  ChevronDown,
  RotateCcw,
  Mic,
  Eye,
  Activity,
  Brain,
  CheckCircle2,
  Volume2,
  Languages,
  Smile,
  ShieldCheck,
  Calendar,
  FileText,
  Sparkles,
  AlertTriangle,
  MessageSquareWarning,
  Link2,
} from "lucide-react";
import { useFeedbackStore } from "@/store/useFeedbackStore";
import { useSessionStore } from "@/store/useSessionStore";
import type { FullAnalysisResult, GazeTunnelingResult } from "@/types";

type PronunciationFlag = NonNullable<FullAnalysisResult["language"]["pronunciation_flags"]>[number];

function gradeColor(s: number) {
  if (s >= 90) return "#3F6B4C";
  if (s >= 80) return "#23345C";
  if (s >= 70) return "#8A5A22";
  return "#8C3B32";
}
function gradeLabel(s: number) {
  if (s >= 90) return "Excellent";
  if (s >= 80) return "Good";
  if (s >= 70) return "Fair";
  return "Needs Work";
}
function formatDuration(secs: number) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function ScoreGauge({ score }: { score: number }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color = gradeColor(score);
  return (
    <svg width="148" height="148" viewBox="0 0 148 148">
      <circle cx="74" cy="74" r={r} fill="none" stroke="#F0EDE5" strokeWidth="10" />
      <circle
        cx="74" cy="74" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeLinecap="round"
        transform="rotate(-90 74 74)"
      />
      <text x="74" y="68" textAnchor="middle" fill="#17181C" fontSize="28" fontWeight="700">{score}</text>
      <text x="74" y="86" textAnchor="middle" fill={color} fontSize="12" fontWeight="600">{gradeLabel(score)}</text>
      <text x="74" y="100" textAnchor="middle" fill="#9B988E" fontSize="10">/ 100</text>
    </svg>
  );
}

function MetricCard({
  label, score, prev, color, icon: Icon,
}: {
  label: string; score: number; prev: number; color: string; icon: React.ElementType;
}) {
  const diff = score - prev;
  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}18` }}>
          <Icon className="w-3.5 h-3.5" style={{ color }} />
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "#9B988E" }}>{label}</span>
      </div>
      <div className="flex items-end justify-between mb-2">
        <span className="text-2xl font-bold" style={{ color }}>{score}</span>
        <div className="flex items-center gap-0.5 text-xs">
          {diff > 0 ? (
            <><TrendingUp className="w-3 h-3" style={{ color: "#3F6B4C" }} /><span className="font-semibold" style={{ color: "#3F6B4C" }}>+{diff}</span></>
          ) : diff < 0 ? (
            <><TrendingDown className="w-3 h-3" style={{ color: "#8C3B32" }} /><span className="font-semibold" style={{ color: "#8C3B32" }}>{diff}</span></>
          ) : (
            <><Minus className="w-3 h-3" style={{ color: "#CDC9BE" }} /><span style={{ color: "#CDC9BE" }} className="font-semibold">—</span></>
          )}
        </div>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#F0EDE5" }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <p className="text-[10px] mt-1.5" style={{ color: "#CDC9BE" }}>Previous: {prev}</p>
    </div>
  );
}

function SectionHeader({ icon: Icon, color, title, meta }: { icon: React.ElementType; color: string; title: string; meta?: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${color}16` }}>
        <Icon className="w-3.5 h-3.5" style={{ color }} />
      </div>
      <h3 className="text-sm font-semibold" style={{ color: "#17181C" }}>{title}</h3>
      {meta && <span className="text-[10px] ml-auto" style={{ color: "#CDC9BE" }}>{meta}</span>}
    </div>
  );
}

const PREV = { fluency: 79, pronunciation: 74, confidence: 73, eyeContact: 77, posture: 63 };

const FALLBACK_RECOMMENDATIONS = [
  {
    title: "Eye Contact Drill",
    description: "Practice the 3-2-1 method: hold eye contact 3 seconds left, 2 center, 1 right per talking point. Do this for 10 minutes daily.",
    tag: "Eye Contact",
    tagColor: "#3F6B4C",
  },
  {
    title: "Pause Power",
    description: "Insert deliberate 1.5-second pauses at key transitions instead of filler words like 'um' or 'uh'. Silence signals confidence.",
    tag: "Fluency",
    tagColor: "#23345C",
  },
  {
    title: "Posture Anchoring",
    description: "Stand with feet shoulder-width apart and hands visible at waist level. Avoid crossing arms or rocking side to side.",
    tag: "Posture",
    tagColor: "#5A5470",
  },
];

const MOCK_AI_SUMMARY =
  "You delivered a confident session with solid pacing and clear articulation. Your fluency has improved significantly from previous sessions — keep up the daily practice streak. Focus on maintaining eye contact more consistently throughout, particularly during slide transitions. Your posture showed improvement in the second half; try to maintain that upright stance from the very start.";

// Sample of what a real pipeline run flags — kept separate from real
// pronunciation_flags data so the two-category distinction is demoable
// even before a recorded session exists.
const FALLBACK_PRONUNCIATION_FLAGS: PronunciationFlag[] = [
  { word: "th→t (\"three\" → \"tree\")", category: "regional",       note: "Consistent Malaysian English th-stopping — not scored as an error" },
  { word: "final consonant cluster dropped (\"asked\" → \"ask\")", category: "regional", note: "Common regional simplification, doesn't affect meaning here" },
  { word: "\"comfortable\" → \"comf-table\"", category: "intelligibility", note: "Syllable dropped enough that it briefly confused word recognition" },
  { word: "\"specific\" → \"pacific\"", category: "intelligibility", note: "Changes the word entirely — likely to be misheard" },
];

// Demo shape for a session that hasn't been recorded yet — same 5-second
// windowing a real session produces, with a deliberately visible gaze↔disfluency
// pattern so the feature reads clearly before anyone has generated real data.
const FALLBACK_GAZE_TUNNELING: GazeTunnelingResult = {
  windowSeconds: 5,
  correlation: 0.58,
  coOccurrencePct: 64,
  totalEvents: 11,
  label: "Strong link",
  windows: [
    { t: 0,  eyeContact: 82, disfluencyCount: 0 },
    { t: 5,  eyeContact: 78, disfluencyCount: 1 },
    { t: 10, eyeContact: 74, disfluencyCount: 0 },
    { t: 15, eyeContact: 51, disfluencyCount: 2 },
    { t: 20, eyeContact: 48, disfluencyCount: 2 },
    { t: 25, eyeContact: 66, disfluencyCount: 1 },
    { t: 30, eyeContact: 79, disfluencyCount: 0 },
    { t: 35, eyeContact: 80, disfluencyCount: 0 },
    { t: 40, eyeContact: 55, disfluencyCount: 3 },
    { t: 45, eyeContact: 58, disfluencyCount: 1 },
    { t: 50, eyeContact: 76, disfluencyCount: 1 },
    { t: 55, eyeContact: 81, disfluencyCount: 0 },
  ],
};

export default function AssessmentPage() {
  const router = useRouter();
  const { liveFeedback, aiFeedback, fullAnalysis, gazeTunneling } = useFeedbackStore();
  const { sessionType, duration } = useSessionStore();
  const [mounted, setMounted] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const mode = sessionType ?? "Presentation";
  const dur = duration > 30 ? duration : 1240;

  const fl = liveFeedback.fluency > 0 ? Math.round(liveFeedback.fluency) : 82;
  const pr = liveFeedback.pronunciation > 0 ? Math.round(liveFeedback.pronunciation) : 76;
  const co = liveFeedback.confidence > 0 ? Math.round(liveFeedback.confidence) : 72;
  const ec = liveFeedback.eye_contact > 0 ? Math.round(liveFeedback.eye_contact) : 80;
  const po = liveFeedback.posture > 0 ? Math.round(liveFeedback.posture) : 68;

  const overall = Math.round(fl * 0.25 + pr * 0.25 + co * 0.20 + ec * 0.15 + po * 0.15);
  const overallColor = gradeColor(overall);

  const radarData = [
    { subject: "Fluency",       current: fl, previous: PREV.fluency },
    { subject: "Pronunciation", current: pr, previous: PREV.pronunciation },
    { subject: "Confidence",    current: co, previous: PREV.confidence },
    { subject: "Eye Contact",   current: ec, previous: PREV.eyeContact },
    { subject: "Posture",       current: po, previous: PREV.posture },
  ];

  const aiSummary = aiFeedback?.summary ?? MOCK_AI_SUMMARY;
  const gt = gazeTunneling && gazeTunneling.windows.length > 0 ? gazeTunneling : FALLBACK_GAZE_TUNNELING;
  const gtIsSample = !(gazeTunneling && gazeTunneling.windows.length > 0);
  const gtColor = gt.label === "Strong link" ? "#3F6B4C" : gt.label === "Some link" ? "#8A5A22" : "#5A5470";

  // Real backend data — undefined until a real session has been analyzed
  const lang = fullAnalysis?.language;
  const speech = fullAnalysis?.speech;
  const vision = fullAnalysis?.vision;
  const commScore = fullAnalysis?.communication_score;
  const rec = fullAnalysis?.recommendations;
  const transcript = fullAnalysis?.transcript;
  const pronunciationFlags = lang?.pronunciation_flags?.length ? lang.pronunciation_flags : FALLBACK_PRONUNCIATION_FLAGS;
  const regionalFlags = pronunciationFlags.filter((f) => f.category === "regional");
  const intelligibilityFlags = pronunciationFlags.filter((f) => f.category === "intelligibility");

  const exercises = rec?.exercises?.length
    ? rec.exercises.map((e) => ({
        title: e.title, description: e.description,
        tag: e.practice_type, tagColor: gradeColor(70),
      }))
    : null;

  const strengths = commScore?.strengths ?? [];
  const improvementAreas = commScore?.improvement_areas ?? [];

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-5">

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/practice")}
            className="w-9 h-9 flex items-center justify-center rounded-xl transition-colors"
            style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="font-display text-xl" style={{ color: "#17181C" }}>Session Results</h1>
            <p className="text-xs" style={{ color: "#9B988E" }}>
              {mode} · {formatDuration(dur)} · {new Date().toLocaleDateString("en-MY", { dateStyle: "medium" })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/progress")}
            className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-xl transition-colors press-effect"
            style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#4B4C52" }}
          >
            <Activity className="w-4 h-4" /> View Progress
          </button>
          <button
            onClick={() => router.push("/practice")}
            className="flex items-center gap-1.5 text-sm text-white px-4 py-2 rounded-xl transition-all press-effect"
            style={{ background: "#23345C" }}
          >
            <RotateCcw className="w-4 h-4" /> Practice Again
          </button>
        </div>
      </div>

      {/* Hero — overall score band, tinted by grade */}
      <div
        className="rounded-2xl p-5 grid grid-cols-1 sm:grid-cols-[180px_1fr] gap-4"
        style={{ background: `${overallColor}08`, border: `1px solid ${overallColor}22` }}
      >
        <div className="rounded-2xl p-5 flex flex-col items-center justify-center" style={{ background: "#FFFFFF", border: "1px solid #E6E2D8" }}>
          <ScoreGauge score={overall} />
          <p className="text-xs mt-3 font-medium" style={{ color: "#6E6C63" }}>Overall Score</p>
          <div className="flex items-center gap-1 mt-1.5">
            <TrendingUp className="w-3.5 h-3.5" style={{ color: "#3F6B4C" }} />
            <span className="text-xs font-semibold" style={{ color: "#3F6B4C" }}>+5 from last session</span>
          </div>
        </div>

        <div className="flex flex-col justify-center gap-3">
          {vision?.confidence_label && (
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" style={{ color: overallColor }} />
              <span className="text-xs font-semibold" style={{ color: "#34343A" }}>
                Confidence: <span style={{ color: overallColor }}>{vision.confidence_label}</span>
              </span>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {strengths.length > 0 ? strengths.map((s) => (
              <span key={s} className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: "rgba(63,107,76,0.10)", color: "#2E4F38" }}>
                <TrendingUp className="w-3 h-3" /> {s}
              </span>
            )) : (
              <span className="text-xs" style={{ color: "#9B988E" }}>Strengths appear here once a real session is analyzed.</span>
            )}
            {improvementAreas.map((a) => (
              <span key={a} className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: "rgba(138,90,34,0.10)", color: "#6B4419" }}>
                <AlertTriangle className="w-3 h-3" /> {a}
              </span>
            ))}
          </div>
          {vision?.dominant_emotion && (
            <div className="flex items-center gap-2">
              <Smile className="w-4 h-4" style={{ color: "#5A5470" }} />
              <span className="text-xs" style={{ color: "#6E6C63" }}>
                Dominant emotion detected: <span className="font-semibold" style={{ color: "#34343A" }}>{vision.dominant_emotion}</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Gaze Tunneling — headline metric, not buried among the smaller
          cards below. Nobody else fuses where you looked with when your
          speech broke down into one correlated signal. */}
      <div className="rounded-2xl p-5 sm:p-6" style={{ background: "#17181C" }}>
        <div className="flex flex-col lg:flex-row lg:items-center gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "rgba(255,255,255,0.08)" }}>
                <Link2 className="w-3.5 h-3.5 text-white" />
              </div>
              <h2 className="font-display text-white text-base">Gaze Tunneling</h2>
              <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full flex-shrink-0"
                style={{ background: `${gtColor}30`, color: gtColor === "#5A5470" ? "#B3AFC4" : gtColor === "#8A5A22" ? "#D9B679" : "#8FBF9C" }}>
                {gt.label}
              </span>
              {gtIsSample && (
                <span className="text-[10px] flex-shrink-0" style={{ color: "rgba(255,255,255,0.35)" }}>sample</span>
              )}
            </div>
            <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.65)" }}>
              {gt.totalEvents > 0 ? (
                <>
                  <span className="font-semibold text-white">{gt.coOccurrencePct}%</span> of this session&apos;s
                  disfluencies (filler words, repeated words) happened within {gt.windowSeconds}s of a dip in eye
                  contact — a <span className="font-semibold text-white">{gt.correlation.toFixed(2)}</span> correlation
                  between looking away and speech breaking down, on one fused timeline instead of two separate scores.
                </>
              ) : (
                "Not enough tracked speech and gaze data this session to compute a correlation."
              )}
            </p>
          </div>

          {/* Fused timeline: eye contact (area) vs disfluency events (bars), same x-axis */}
          <div className="w-full lg:w-[380px] flex-shrink-0">
            {mounted ? (
              <ResponsiveContainer width="100%" height={140}>
                <ComposedChart data={gt.windows} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="t" tickFormatter={(t) => `${t}s`} tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis yAxisId="eye" domain={[0, 100]} hide />
                  <YAxis yAxisId="dis" domain={[0, "dataMax + 1"]} hide />
                  <Tooltip
                    contentStyle={{ borderRadius: 10, border: "1px solid rgba(255,255,255,0.12)", background: "#0B0C10", fontSize: 11 }}
                    labelStyle={{ color: "rgba(255,255,255,0.5)" }}
                    itemStyle={{ color: "#fff" }}
                    formatter={(v, name) => [String(v), name === "eyeContact" ? "Eye contact" : "Disfluencies"]}
                  />
                  <Area yAxisId="eye" type="monotone" dataKey="eyeContact" stroke="#5C729B" fill="#5C729B" fillOpacity={0.22} strokeWidth={1.5} />
                  <Bar yAxisId="dis" dataKey="disfluencyCount" fill="#9C4A40" radius={[2, 2, 0, 0]} barSize={10} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[140px]" />
            )}
            <div className="flex items-center gap-4 mt-1">
              <span className="flex items-center gap-1.5 text-[10px]" style={{ color: "rgba(255,255,255,0.4)" }}>
                <span className="w-2 h-2 rounded-full" style={{ background: "#5C729B" }} /> Eye contact
              </span>
              <span className="flex items-center gap-1.5 text-[10px]" style={{ color: "rgba(255,255,255,0.4)" }}>
                <span className="w-2 h-2 rounded-sm" style={{ background: "#9C4A40" }} /> Disfluencies
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
        <MetricCard label="Fluency"       score={fl} prev={PREV.fluency}       color="#23345C" icon={Mic}      />
        <MetricCard label="Pronunciation" score={pr} prev={PREV.pronunciation} color="#5A5470" icon={Volume2}  />
        <MetricCard label="Confidence"    score={co} prev={PREV.confidence}    color="#8A5A22" icon={Brain}    />
        <MetricCard label="Eye Contact"   score={ec} prev={PREV.eyeContact}    color="#3F6B4C" icon={Eye}      />
        <MetricCard label="Posture"       score={po} prev={PREV.posture}       color="#8C3B32" icon={Activity} />
      </div>

      {/* Radar + Side Stats */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4">
        <div className="glass-card rounded-2xl p-4 sm:p-6">
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#17181C" }}>Performance vs Previous Session</h2>
          {mounted ? (
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData} margin={{ top: 10, right: 36, bottom: 10, left: 36 }}>
                <PolarGrid stroke="#F0EDE5" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: "#6E6C63", fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="This Session" dataKey="current" stroke="#23345C" fill="#23345C" fillOpacity={0.18} strokeWidth={2} />
                <Radar name="Previous" dataKey="previous" stroke="#CDC9BE" fill="#F1EEE6" strokeWidth={1.5} strokeDasharray="4 2" />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: "#6E6C63" }} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[260px] flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-[#23345C] border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="glass-card rounded-2xl p-5">
            <SectionHeader icon={Mic} color="#5A5470" title="Speech Analytics" />
            <div className="space-y-3.5">
              {([
                { label: "Speaking Rate", value: `${speech?.speaking_rate ?? 142} WPM`, note: "Ideal: 120–160 WPM", ok: true },
                {
                  label: "Filler Words",
                  value: speech ? `${speech.filler_count} words` : "8 words",
                  note: speech ? `${speech.filler_per_minute}/min · top: "${speech.top_filler}"` : "um, uh, like, you know",
                  ok: (speech?.filler_per_minute ?? 2) < 5,
                },
                {
                  label: "Stuttering",
                  value: speech?.stuttering_severity ?? "3 events",
                  note: speech ? "Detected by signal analysis" : "Detected by signal analysis",
                  ok: (speech?.stuttering_score ?? 0) < 25,
                },
              ] as const).map(({ label, value, note, ok }) => (
                <div key={label} className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium" style={{ color: "#17181C" }}>{label}</p>
                    <p className="text-[10px]" style={{ color: "#CDC9BE" }}>{note}</p>
                  </div>
                  <span className="text-sm font-bold" style={{ color: ok ? "#3F6B4C" : "#8A5A22" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card rounded-2xl p-5">
            <SectionHeader icon={Eye} color="#3F6B4C" title="Vision Analytics" />
            <div className="space-y-3.5">
              {([
                { label: "Eye Contact",       value: `${ec}%`,  ok: ec >= 70 },
                { label: "Emotion",           value: vision?.dominant_emotion ?? "Focused", ok: true },
                { label: "Posture Stability", value: `${po}%`,  ok: po >= 70 },
              ] as const).map(({ label, value, ok }) => (
                <div key={label} className="flex items-center justify-between">
                  <p className="text-xs font-medium" style={{ color: "#17181C" }}>{label}</p>
                  <span className="text-sm font-bold capitalize" style={{ color: ok ? "#3F6B4C" : "#8C3B32" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Malaysian language & accent insight */}
      <div className="glass-card rounded-2xl p-6">
        <SectionHeader icon={Languages} color="#3C6E78" title="Language & Accent Detection"
          meta={lang ? undefined : "Sample — accent-fair scoring in action"} />
        <div className="space-y-5">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full"
              style={{ background: "rgba(60,110,120,0.10)", color: "#2E5760" }}>
              {lang?.accent_type ?? "Malaysian English"}
            </span>
            {(lang?.is_code_switching ?? true) && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: "rgba(90,84,112,0.10)", color: "#48435C" }}>
                Code-switching detected
              </span>
            )}
            <span className="text-xs" style={{ color: "#9B988E" }}>
              Primary language: <span className="font-semibold" style={{ color: "#34343A" }}>{(lang?.primary_language ?? "en").toUpperCase()}</span>
            </span>
          </div>
          <div>
            <div className="flex items-center justify-between text-[10px] mb-1.5" style={{ color: "#9B988E" }}>
              <span>English {Math.round((lang?.english_ratio ?? 0.78) * 100)}%</span>
              <span>Bahasa Melayu {Math.round((lang?.malay_ratio ?? 0.22) * 100)}%</span>
            </div>
            <div className="h-2.5 rounded-full overflow-hidden flex" style={{ background: "#F0EDE5" }}>
              <div style={{ width: `${(lang?.english_ratio ?? 0.78) * 100}%`, background: "#23345C" }} />
              <div style={{ width: `${(lang?.malay_ratio ?? 0.22) * 100}%`, background: "#3C6E78" }} />
            </div>
          </div>

          <div style={{ borderTop: "1px solid #F0EDE5" }} />

          {/* The accent-fair distinction, made visible rather than blended
              into one score: what's flagged as regional phonology (never
              penalized) versus what would actually cost intelligibility. */}
          <div>
            <p className="text-xs font-semibold mb-1" style={{ color: "#17181C" }}>
              What "mispronunciation" actually means here
            </p>
            <p className="text-xs leading-relaxed mb-4" style={{ color: "#6E6C63" }}>
              Every flagged sound is sorted into one of two buckets — not blended into a single
              pronunciation score. Regional phonology is recognised and left alone; only sounds
              that would genuinely confuse a listener count against you.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="rounded-xl p-4" style={{ background: "rgba(63,107,76,0.05)", border: "1px solid rgba(63,107,76,0.20)" }}>
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-4 h-4 flex-shrink-0" style={{ color: "#3F6B4C" }} />
                  <span className="text-xs font-bold uppercase tracking-wide" style={{ color: "#3F6B4C" }}>
                    Regional variation · not penalised
                  </span>
                </div>
                <div className="space-y-2.5">
                  {regionalFlags.map((f, i) => (
                    <div key={i}>
                      <p className="text-xs font-semibold" style={{ color: "#17181C" }}>{f.word}</p>
                      <p className="text-[11px] leading-relaxed mt-0.5" style={{ color: "#6E6C63" }}>{f.note}</p>
                    </div>
                  ))}
                  {regionalFlags.length === 0 && (
                    <p className="text-[11px]" style={{ color: "#9B988E" }}>None flagged this session.</p>
                  )}
                </div>
              </div>
              <div className="rounded-xl p-4" style={{ background: "rgba(140,59,50,0.05)", border: "1px solid rgba(140,59,50,0.20)" }}>
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" style={{ color: "#8C3B32" }} />
                  <span className="text-xs font-bold uppercase tracking-wide" style={{ color: "#8C3B32" }}>
                    Affects intelligibility · flagged
                  </span>
                </div>
                <div className="space-y-2.5">
                  {intelligibilityFlags.map((f, i) => (
                    <div key={i}>
                      <p className="text-xs font-semibold" style={{ color: "#17181C" }}>{f.word}</p>
                      <p className="text-[11px] leading-relaxed mt-0.5" style={{ color: "#6E6C63" }}>{f.note}</p>
                    </div>
                  ))}
                  {intelligibilityFlags.length === 0 && (
                    <p className="text-[11px]" style={{ color: "#9B988E" }}>None flagged this session.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Weekly coaching plan */}
      <div className="glass-card rounded-2xl p-6">
        <SectionHeader icon={Calendar} color="#8A5A22" title="Your Coaching Plan"
          meta={rec ? undefined : "Available after a real session"} />
        {rec ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "#9B988E" }}>Weekly Focus</p>
              <p className="text-sm font-semibold" style={{ color: "#17181C" }}>{rec.weekly_focus}</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "#9B988E" }}>Daily Target</p>
              <p className="text-sm font-semibold" style={{ color: "#17181C" }}>{rec.daily_target_minutes} minutes</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "#9B988E" }}>Forecast</p>
              <p className="text-sm font-semibold" style={{ color: "#17181C" }}>{rec.progress_forecast}</p>
            </div>
            {rec.tips.length > 0 && (
              <div className="col-span-1 sm:col-span-3 pt-3 space-y-1.5" style={{ borderTop: "1px solid #F0EDE5" }}>
                {rec.tips.map((tip, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: "#8A5A22" }} />
                    <p className="text-xs leading-relaxed" style={{ color: "#4B4C52" }}>{tip}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm" style={{ color: "#9B988E" }}>
            Your personalized weekly focus, daily practice target, and progress forecast will appear here once a real session is analyzed.
          </p>
        )}
      </div>

      {/* AI Feedback */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "#23345C" }}>
            <Brain className="w-3.5 h-3.5 text-white" />
          </div>
          <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>AI Coach Feedback</h2>
          <span className="text-[10px] ml-auto" style={{ color: "#CDC9BE" }}>Powered by GPT-4o</span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "#4B4C52" }}>{aiSummary}</p>
      </div>

      {/* Transcript */}
      {transcript && (
        <div className="glass-card rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowTranscript((v) => !v)}
            className="w-full flex items-center gap-2 p-6 text-left"
          >
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "rgba(110,108,99,0.12)" }}>
              <FileText className="w-3.5 h-3.5" style={{ color: "#4B4C52" }} />
            </div>
            <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>Session Transcript</h2>
            <ChevronDown
              className="w-4 h-4 ml-auto transition-transform"
              style={{ color: "#9B988E", transform: showTranscript ? "rotate(180deg)" : "none" }}
            />
          </button>
          {showTranscript && (
            <div className="px-6 pb-6">
              <p className="text-sm leading-relaxed rounded-xl p-4" style={{ background: "#F5F2EB", border: "1px solid #F0EDE5", color: "#34343A" }}>
                {transcript}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-semibold" style={{ color: "#17181C" }}>Recommended Exercises</h2>
          {!exercises && (
            <span className="flex items-center gap-1 text-[10px]" style={{ color: "#CDC9BE" }}>
              <MessageSquareWarning className="w-3 h-3" /> sample — real recommendations appear after a session
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {(exercises ?? FALLBACK_RECOMMENDATIONS).map((r, i) => (
            <div key={i} className="glass-card rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4" style={{ color: r.tagColor }} />
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide"
                  style={{ backgroundColor: `${r.tagColor}18`, color: r.tagColor }}
                >
                  {r.tag}
                </span>
              </div>
              <h3 className="text-sm font-semibold mb-1.5" style={{ color: "#17181C" }}>{r.title}</h3>
              <p className="text-xs leading-relaxed" style={{ color: "#6E6C63" }}>{r.description}</p>
              <button
                onClick={() => router.push("/coach")}
                className="mt-4 text-xs font-medium flex items-center gap-0.5 hover:gap-1 transition-all"
                style={{ color: r.tagColor }}
              >
                Ask AI Coach <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
