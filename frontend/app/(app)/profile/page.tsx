"use client";

// Profile: who you are and what you're practising for. The AI coach reads these
// fields, so they're saved to the backend; the stats on the left are real.

import { useState, useSyncExternalStore } from "react";
import { Check, Loader2 } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useMyStats } from "@/hooks/useMyStats";
import { authService } from "@/services/auth";
import { Button, Card, Field, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";
import { mascot } from "@/lib/mascot";
import type { FeedbackStyle, StudyLevel } from "@/types";

const GOAL_OPTIONS = [
  "Academic Presentations", "Job Interviews", "Public Speaking", "Business Communication", "Daily Conversation",
];

const SKILL_OPTIONS = ["Beginner", "Intermediate", "Advanced"] as const;
type SkillLevel = (typeof SKILL_OPTIONS)[number];
// What each level changes in practice (backend services/learner.py says the same to the AI)
const SKILL_HINT: Record<SkillLevel, string> = {
  Beginner: "Short, simple questions, one idea at a time",
  Intermediate: "Everyday-professional questions that ask for reasons and examples",
  Advanced: "Probing, multi-part questions and tougher follow-ups",
};

const STUDY_OPTIONS: { value: StudyLevel; label: string; hint: string }[] = [
  { value: "Secondary", label: "Secondary school", hint: "SPM level" },
  { value: "Pre-university", label: "Pre-university", hint: "Foundation, matriculation, diploma, STPM" },
  { value: "Undergraduate", label: "Undergraduate", hint: "Degree" },
  { value: "Postgraduate", label: "Postgraduate", hint: "Master's, PhD" },
  { value: "Working professional", label: "Working professional", hint: "In a job" },
];
const FIELD_SUGGESTIONS = ["Computer Science", "Engineering", "Business", "Accounting", "Medicine", "Law", "Education", "Data Science", "Design", "Marketing"];

const STYLE_OPTIONS: { value: FeedbackStyle; label: string; example: string }[] = [
  { value: "encouraging", label: "Encouraging", example: "“Great start! One thing to try next…”" },
  { value: "balanced", label: "Balanced", example: "“Clear structure. Add one specific example.”" },
  { value: "direct", label: "Direct", example: "“Fix this first: your answer had no result.”" },
];

const CHALLENGE_OPTIONS = ["Filler Words", "Pronunciation", "Eye Contact", "Speaking Pace", "Confidence", "Posture"];

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active}
      className="px-3 py-2 text-sm transition-colors"
      style={{
        background: active ? "var(--surface-2)" : "var(--surface)",
        border: `1px solid ${active ? "var(--accent-ink)" : "var(--line-strong)"}`,
        color: "var(--ink)", fontWeight: active ? 600 : 400,
      }}>
      {children}
    </button>
  );
}

export default function ProfilePage() {
  const { user, profile, setUser, setProfile } = useUserStore();
  const { stats } = useMyStats();
  // The signed-in user comes from localStorage, which the server render can't see
  const hydrated = useSyncExternalStore(() => () => {}, () => true, () => false);

  const [name,       setName]       = useState(user?.full_name ?? "");
  const [goal,       setGoal]       = useState(user?.communication_goal ?? profile?.communication_goal ?? "");
  const [skill,      setSkill]      = useState<SkillLevel>((user?.skill_level ?? profile?.skill_level ?? "Beginner") as SkillLevel);
  const [challenges, setChallenges] = useState<string[]>(user?.challenges ?? profile?.challenges ?? []);
  const [study,      setStudy]      = useState<StudyLevel | "">(user?.study_level ?? "");
  const [field,      setField]      = useState(user?.field_of_study ?? "");
  const [style,      setStyle]      = useState<FeedbackStyle>(user?.feedback_style ?? "balanced");
  const [saving,     setSaving]     = useState(false);
  const [saved,      setSaved]      = useState(false);
  const [saveError,  setSaveError]  = useState<string | null>(null);

  if (!hydrated) return null;
  if (!user) {
    return (
      <div className="px-4 sm:px-6 py-6 max-w-[1100px] mx-auto">
        <PageHeader title="Profile" />
        <Notice>Sign in to see and edit your profile.</Notice>
      </div>
    );
  }

  const toggleChallenge = (c: string) =>
    setChallenges((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setSaveError("Please enter your name."); return; }
    setSaveError(null); setSaving(true);
    try {
      const updated = await authService.updateProfile({
        full_name: name.trim(), communication_goal: goal, skill_level: skill, challenges,
        ...(study ? { study_level: study } : {}), field_of_study: field.trim(), feedback_style: style,
      });
      mascot("success", "Profile saved. I'll pitch things at your level.");
      setUser(updated);
      if (profile) setProfile({ ...profile, communication_goal: goal, skill_level: skill, challenges });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Couldn't save your profile.");
      mascot("error");
    } finally {
      setSaving(false);
    }
  };

  // How complete the profile is: each part makes the coaching fit better
  const filled = [name.trim(), study, field.trim(), goal, challenges.length ? "y" : ""].filter(Boolean).length;
  const complete = Math.round((filled / 5) * 100);
  // The same picture the AI gets (services/learner.py), in plain words
  const studyLabel = STUDY_OPTIONS.find((o) => o.value === study)?.label.toLowerCase();
  const preview = [
    studyLabel ? `you're ${/^[aeiou]/.test(studyLabel) ? "an" : "a"} ${studyLabel}${field.trim() ? ` in ${field.trim()}` : ""}` : field.trim() ? `your field is ${field.trim()}` : null,
    `questions are pitched for a ${skill.toLowerCase()} speaker (${SKILL_HINT[skill].toLowerCase()})`,
    goal ? `aimed at ${goal.toLowerCase()}` : null,
    challenges.length ? `with extra attention to ${challenges.join(", ").toLowerCase()}` : null,
    `and feedback is ${style}`,
  ].filter(Boolean).join("; ") + ".";

  const STATS: [string, string][] = [
    ["Sessions", stats ? String(stats.sessions) : "—"],
    ["Minutes practised", stats ? String(stats.practiceMinutes) : "—"],
    ["Latest score", stats?.latestScore != null ? String(stats.latestScore) : "—"],
    ["Day streak", stats ? String(stats.streakDays) : "—"],
  ];

  return (
    <div className="px-4 sm:px-6 py-6 max-w-[1100px] mx-auto">
      <PageHeader title="Profile">Your coach uses these details to pitch questions and feedback at the right level.</PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 items-start">
        <Card>
          <p className="text-lg font-semibold" style={{ color: "var(--ink)" }}>{user.full_name}</p>
          <p className="text-sm break-all" style={{ color: "var(--muted)" }}>{user.email}</p>
          <dl className="mt-5 pt-4 grid grid-cols-2 gap-4" style={{ borderTop: "1px solid var(--line-2)" }}>
            {STATS.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs" style={{ color: "var(--muted)" }}>{k}</dt>
                <dd className="font-display text-2xl tabular-nums" style={{ color: "var(--ink)" }}>{v}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--line-2)" }}>
            <div className="flex items-center justify-between text-xs">
              <span style={{ color: "var(--muted)" }}>Profile complete</span>
              <span className="font-semibold tabular-nums" style={{ color: "var(--ink)" }}>{complete}%</span>
            </div>
            <div className="mt-1.5 h-2 rounded-full overflow-hidden" style={{ background: "var(--line)" }}
              role="progressbar" aria-valuenow={complete} aria-valuemin={0} aria-valuemax={100} aria-label="Profile complete">
              <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${complete}%`, background: complete === 100 ? "var(--ok)" : "var(--accent)" }} />
            </div>
          </div>
          {user.created_at && (
            <p className="text-xs mt-5" style={{ color: "var(--muted)" }}>
              Member since {new Date(user.created_at).toLocaleDateString("en-MY", { month: "long", year: "numeric" })}
            </p>
          )}
        </Card>

        <form onSubmit={handleSave}>
          <Card className="space-y-6">
            <Field label="Full name">
              <input className={inputClass} style={inputStyle} value={name} maxLength={100} required
                autoComplete="name" onChange={(e) => setName(e.target.value)} />
            </Field>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>Level of study</legend>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {STUDY_OPTIONS.map((o) => (
                  <Chip key={o.value} active={study === o.value} onClick={() => setStudy(o.value)}>
                    <span className="block text-left">{o.label}<span className="block text-xs font-normal" style={{ color: "var(--muted)" }}>{o.hint}</span></span>
                  </Chip>
                ))}
              </div>
            </fieldset>

            <Field label="Field of study or work">
              <input className={inputClass} style={inputStyle} value={field} maxLength={100} list="field-suggestions"
                placeholder="e.g. Computer Science, Nursing, Marketing" onChange={(e) => setField(e.target.value)} />
              <datalist id="field-suggestions">{FIELD_SUGGESTIONS.map((f) => <option key={f} value={f} />)}</datalist>
            </Field>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>Communication goal</legend>
              <div className="flex flex-wrap gap-2">
                {GOAL_OPTIONS.map((g) => <Chip key={g} active={goal === g} onClick={() => setGoal(g)}>{g}</Chip>)}
              </div>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>Skill level</legend>
              <div className="flex flex-wrap gap-2">
                {SKILL_OPTIONS.map((s) => (
                  <Chip key={s} active={skill === s} onClick={() => setSkill(s)}>
                    <span className="block text-left">{s}<span className="block text-xs font-normal" style={{ color: "var(--muted)" }}>{SKILL_HINT[s]}</span></span>
                  </Chip>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>
                Main challenges <span className="text-xs font-normal" style={{ color: "var(--muted)" }}>select all that apply</span>
              </legend>
              <div className="flex flex-wrap gap-2">
                {CHALLENGE_OPTIONS.map((c) => <Chip key={c} active={challenges.includes(c)} onClick={() => toggleChallenge(c)}>{c}</Chip>)}
              </div>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>How should feedback sound?</legend>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {STYLE_OPTIONS.map((o) => (
                  <Chip key={o.value} active={style === o.value} onClick={() => setStyle(o.value)}>
                    <span className="block text-left">{o.label}<span className="block text-xs font-normal italic mt-0.5" style={{ color: "var(--muted)" }}>{o.example}</span></span>
                  </Chip>
                ))}
              </div>
            </fieldset>

            {/* What the coach will do with all this, updated as you choose */}
            <div className="p-4 rounded-lg text-sm" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }} aria-live="polite">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] mb-1" style={{ color: "var(--muted)" }}>How your coach uses this</p>
              <p style={{ color: "var(--ink-2)" }}>{preview.charAt(0).toUpperCase() + preview.slice(1)}</p>
              <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
                Used for the AI partner, interview and Q&amp;A questions, and your feedback; it goes to the AI only inside those requests.
              </p>
            </div>

            {saveError && <Notice tone="bad">{saveError}</Notice>}
            <div className="flex justify-end pt-2" style={{ borderTop: "1px solid var(--line-2)" }}>
              <Button type="submit" disabled={saving} className="mt-4" aria-live="polite">
                {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                  : saved ? <><Check className="w-4 h-4" /> Saved</> : "Save changes"}
              </Button>
            </div>
          </Card>
        </form>
      </div>
    </div>
  );
}
