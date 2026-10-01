"use client";

// Mock interview, step 1: tell the AI about the job (and optionally upload a resume),
// preview the curated questions, then start the interview session.

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";
import { interviewService, liveService } from "@/services/live";
import { authService } from "@/services/auth";
import { Button, Card, Field, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";
import type { InterviewSetup, PracticePlan } from "@/types";

const LEVELS: { id: InterviewSetup["level"]; label: string }[] = [
  { id: "internship", label: "Internship" },
  { id: "graduate", label: "Fresh graduate" },
  { id: "junior", label: "Junior (1–3 yrs)" },
  { id: "mid", label: "Mid-level" },
  { id: "senior", label: "Senior" },
];
const TYPES: { id: InterviewSetup["interview_type"]; label: string; desc: string }[] = [
  { id: "behavioural", label: "Behavioural", desc: "Teamwork, challenges, motivation (STAR answers)" },
  { id: "technical", label: "Technical", desc: "Role-specific problem solving and depth" },
  { id: "mixed", label: "Mixed", desc: "A bit of both, like most real interviews" },
];

function Choice<T extends string>({ value, options, onChange }: {
  value: T; options: { id: T; label: string; desc?: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(${options.some((o) => o.desc) ? 180 : 120}px, 1fr))` }}>
      {options.map((o) => {
        const active = o.id === value;
        return (
          <button key={o.id} type="button" onClick={() => onChange(o.id)} aria-pressed={active}
            className="text-left px-3 py-2.5 text-sm transition-colors"
            style={{
              background: active ? "var(--surface-2)" : "var(--surface)",
              border: `1px solid ${active ? "var(--accent-ink)" : "var(--line-strong)"}`,
              color: "var(--ink)", fontWeight: active ? 600 : 400,
            }}>
            {o.label}
            {o.desc && <span className="block text-xs font-normal mt-0.5" style={{ color: "var(--muted)" }}>{o.desc}</span>}
          </button>
        );
      })}
    </div>
  );
}

export default function InterviewSetupPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [setup, setSetup] = useState<InterviewSetup>({ position: "", level: "graduate", interview_type: "mixed" });
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [plan, setPlan] = useState<PracticePlan | null>(null);
  const [planBusy, setPlanBusy] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof InterviewSetup>(k: K, v: InterviewSetup[K]) => {
    setSetup((s) => ({ ...s, [k]: v }));
    setPlan(null);  // the questions depend on the setup
  };
  const ready = setup.position.trim().length >= 2;
  const clean = (): InterviewSetup => ({
    ...setup,
    position: setup.position.trim(),
    company: setup.company?.trim() || undefined,
    background: setup.background?.trim() || undefined,
    job_description: setup.job_description?.trim() || undefined,
  });

  const uploadResume = async (file: File) => {
    setResumeBusy(true); setError(null);
    try {
      const { text } = await interviewService.readResume(file);
      setSetup((s) => ({ ...s, resume_text: text })); setResumeName(file.name); setPlan(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't read that resume");
    } finally { setResumeBusy(false); }
  };

  const preview = async () => {
    setPlanBusy(true); setError(null);
    try { setPlan(await interviewService.plan(clean())); }
    catch (e) { setError(e instanceof Error ? e.message : "Couldn't prepare the questions"); }
    finally { setPlanBusy(false); }
  };

  const start = async () => {
    if (!authService.isSignedIn()) { router.push("/login"); return; }
    setStarting(true); setError(null);
    try {
      const s = await liveService.start({ session_type: "Interview", interview: clean(), plan: plan ?? undefined });
      router.push(`/session?mode=Interview&live=${s.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't start the interview");
      setStarting(false);
    }
  };

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[1100px] mx-auto">
      <PageHeader eyebrow="Mock interview" title="Tell us about the interview">
        The interviewer prepares questions for this role, your level and your background. Add your resume and
        they&apos;ll ask about your real experience. You&apos;ll get feedback on every answer afterwards.
      </PageHeader>

      <div className="grid lg:grid-cols-[1fr_400px] gap-6 items-start">
        <div className="space-y-5">
          <Card title="1 · The role">
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Position you applied for">
                <input className={inputClass} style={inputStyle} value={setup.position} maxLength={120}
                  placeholder="e.g. Data Analyst" onChange={(e) => set("position", e.target.value)} />
              </Field>
              <Field label="Company" optional>
                <input className={inputClass} style={inputStyle} value={setup.company ?? ""} maxLength={120}
                  placeholder="e.g. Maybank" onChange={(e) => set("company", e.target.value)} />
              </Field>
            </div>
            <div className="mt-4 space-y-4">
              <Field label="Level"><Choice value={setup.level} options={LEVELS} onChange={(v) => set("level", v)} /></Field>
              <Field label="Interview type"><Choice value={setup.interview_type} options={TYPES} onChange={(v) => set("interview_type", v)} /></Field>
              <Field label="Job description" optional hint="Paste the key requirements: questions will target them.">
                <textarea className={inputClass} style={inputStyle} rows={4} maxLength={4000} value={setup.job_description ?? ""}
                  onChange={(e) => set("job_description", e.target.value)} />
              </Field>
            </div>
          </Card>

          <Card title="2 · About you">
            <Field label="Your background" optional hint="Studies, experience, projects, what you're proud of.">
              <textarea className={inputClass} style={inputStyle} rows={4} maxLength={2000} value={setup.background ?? ""}
                placeholder="e.g. Final-year Computer Science student at UM; built a sales dashboard during my internship at…"
                onChange={(e) => set("background", e.target.value)} />
            </Field>
            <div className="mt-4">
              <p className="text-sm font-medium mb-1.5" style={{ color: "var(--ink)" }}>
                Resume <span className="text-xs font-normal" style={{ color: "var(--muted)" }}>optional · PDF, DOCX or TXT</span>
              </p>
              {setup.resume_text ? (
                <div className="flex items-start gap-3 p-3" style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
                  <FileText className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: "var(--accent-ink)" }} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--ink)" }}>{resumeName}</p>
                    <p className="text-xs mt-0.5 line-clamp-2" style={{ color: "var(--muted)" }}>{setup.resume_text.slice(0, 220)}…</p>
                  </div>
                  <button onClick={() => { set("resume_text", undefined); setResumeName(null); }} aria-label="Remove resume"
                    className="p-1" style={{ color: "var(--muted)" }}><Trash2 className="w-4 h-4" /></button>
                </div>
              ) : (
                <button type="button" onClick={() => fileRef.current?.click()} disabled={resumeBusy}
                  className="w-full flex items-center justify-center gap-2 py-5 text-sm"
                  style={{ border: "1px dashed var(--line-strong)", color: "var(--ink-2)", background: "var(--surface)" }}>
                  {resumeBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {resumeBusy ? "Reading your resume…" : "Upload resume"}
                </button>
              )}
              <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadResume(f); e.target.value = ""; }} />
              <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>
                Only the text is kept, with this interview session; deleting the session deletes it.
              </p>
            </div>
          </Card>
          {error && <Notice tone="bad">{error}</Notice>}
        </div>

        {/* Plan preview + start */}
        <div className="lg:sticky lg:top-20 space-y-4">
          <Card title="3 · Your questions" action={plan && (
            <button onClick={preview} disabled={planBusy} className="flex items-center gap-1 text-xs font-semibold" style={{ color: "var(--accent-ink)" }}>
              <RefreshCw className={`w-3.5 h-3.5 ${planBusy ? "animate-spin" : ""}`} /> New set
            </button>
          )}>
            {!plan ? (
              <div className="space-y-3">
                <p className="text-sm" style={{ color: "var(--ink-2)" }}>
                  Preview the questions before you start, or start straight away and be surprised.
                </p>
                <Button variant="secondary" className="w-full" onClick={preview} disabled={!ready || planBusy}>
                  {planBusy ? <><Loader2 className="w-4 h-4 animate-spin" /> Preparing questions…</> : "Preview questions"}
                </Button>
                {planBusy && <p className="text-xs" style={{ color: "var(--muted)" }}>The local AI can take up to a minute.</p>}
              </div>
            ) : (
              <ol className="space-y-3">
                {plan.questions.map((q, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center text-[11px] font-bold text-white" style={{ background: "var(--accent)" }}>{i + 1}</span>
                    <div>
                      <p className="text-sm leading-snug" style={{ color: "var(--ink)" }}>{q.question}</p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>Tests: {q.assesses}</p>
                    </div>
                  </li>
                ))}
                {plan.source === "rules" && (
                  <p className="text-xs pt-1" style={{ color: "var(--muted)" }}>
                    The AI model isn&apos;t available, so these come from a standard question bank.
                  </p>
                )}
              </ol>
            )}
          </Card>
          <Button className="w-full h-12 text-base" onClick={start} disabled={!ready || starting}>
            {starting ? <><Loader2 className="w-4 h-4 animate-spin" /> Preparing your interview…</> : "Start interview"}
          </Button>
          {!ready && <p className="text-xs text-center" style={{ color: "var(--muted)" }}>Enter the position to continue.</p>}
          <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
            You&apos;ll need your camera and microphone. The interview takes about 10–15 minutes; end it any time.
          </p>
        </div>
      </div>
    </div>
  );
}
