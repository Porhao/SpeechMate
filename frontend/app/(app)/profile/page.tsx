"use client";

// Profile: who you are and what you're practising for. The AI coach reads these
// fields, so they're saved to the backend; the stats on the left are real.

import { useState, useSyncExternalStore } from "react";
import { Check, Loader2 } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useMyStats } from "@/hooks/useMyStats";
import { authService } from "@/services/auth";
import { Button, Card, Field, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";

const LANGUAGE_OPTIONS = [
  { value: "English",         label: "English" },
  { value: "Bahasa Malaysia", label: "Bahasa Malaysia" },
  { value: "Bilingual",       label: "Bilingual (BM + English)" },
];

const GOAL_OPTIONS = [
  "Academic Presentations", "Job Interviews", "Public Speaking", "Business Communication", "Daily Conversation",
];

const SKILL_OPTIONS = ["Beginner", "Intermediate", "Advanced"] as const;
type SkillLevel = (typeof SKILL_OPTIONS)[number];

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
  const [language,   setLanguage]   = useState(user?.language ?? "English");
  const [goal,       setGoal]       = useState(user?.communication_goal ?? profile?.communication_goal ?? "");
  const [skill,      setSkill]      = useState<SkillLevel>((user?.skill_level ?? profile?.skill_level ?? "Beginner") as SkillLevel);
  const [challenges, setChallenges] = useState<string[]>(user?.challenges ?? profile?.challenges ?? []);
  const [saving,     setSaving]     = useState(false);
  const [saved,      setSaved]      = useState(false);
  const [saveError,  setSaveError]  = useState<string | null>(null);

  if (!hydrated) return null;
  if (!user) {
    return (
      <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto">
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
        full_name: name.trim(), language, communication_goal: goal, skill_level: skill, challenges,
      });
      setUser(updated);
      if (profile) setProfile({ ...profile, communication_goal: goal, skill_level: skill, challenges });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Couldn't save your profile.");
    } finally {
      setSaving(false);
    }
  };

  const STATS: [string, string][] = [
    ["Sessions", stats ? String(stats.sessions) : "—"],
    ["Minutes practised", stats ? String(stats.practiceMinutes) : "—"],
    ["Latest score", stats?.latestScore != null ? String(stats.latestScore) : "—"],
    ["Day streak", stats ? String(stats.streakDays) : "—"],
  ];

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto">
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
          {user.created_at && (
            <p className="text-xs mt-5" style={{ color: "var(--muted)" }}>
              Member since {new Date(user.created_at).toLocaleDateString("en-MY", { month: "long", year: "numeric" })}
            </p>
          )}
        </Card>

        <form onSubmit={handleSave}>
          <Card className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Full name">
                <input className={inputClass} style={inputStyle} value={name} maxLength={100} required
                  autoComplete="name" onChange={(e) => setName(e.target.value)} />
              </Field>
              <Field label="Language preference">
                <select className={inputClass} style={inputStyle} value={language} onChange={(e) => setLanguage(e.target.value)}>
                  {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>Communication goal</legend>
              <div className="flex flex-wrap gap-2">
                {GOAL_OPTIONS.map((g) => <Chip key={g} active={goal === g} onClick={() => setGoal(g)}>{g}</Chip>)}
              </div>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>Skill level</legend>
              <div className="flex flex-wrap gap-2">
                {SKILL_OPTIONS.map((s) => <Chip key={s} active={skill === s} onClick={() => setSkill(s)}>{s}</Chip>)}
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
