"use client";

// Privacy & security: what SpeechMate collects, where each piece goes, how long it's kept,
// how it's protected, your rights under Malaysia's PDPA 2010, and your controls.
// Every statement here matches the backend (docs/project/Security.md); keep them in step.

import Link from "next/link";
import { Cloud, Database, Eye, FileText, KeyRound, Lock, Mic, ShieldCheck, Timer, UserRound, Video, type LucideIcon } from "lucide-react";
import { Card, PageHeader } from "@/components/ui/kit";
import PrivacyControls from "@/components/privacy/PrivacyControls";

type Where = "server" | "cloud" | "browser";
const WHERE: Record<Where, { label: string; color: string }> = {
  browser: { label: "Your browser", color: "var(--ok)" },
  server: { label: "SpeechMate server", color: "var(--teal-ink)" },
  cloud: { label: "Cloud AI", color: "var(--warn)" },
};

const DATA: { icon: LucideIcon; what: string; why: string; where: [Where, string][]; kept: string }[] = [
  { icon: UserRound, what: "Account and profile", why: "Signing you in; pitching questions and feedback at your level",
    where: [["server", "name, email, password (hashed), study level, field, goals"], ["cloud", "your level, field and goals go to Gemini only inside a request, never your name or email"]],
    kept: "Until you delete your account" },
  { icon: Mic, what: "Your voice", why: "The transcript, pace, fillers, pronunciation",
    where: [["cloud", "Groq transcribes each spoken turn and the session's speech"], ["server", "pitch, pauses and pronunciation are measured here"]],
    kept: "Turn audio isn't stored; the session recording is deleted once analysed, unless you keep recordings" },
  { icon: Video, what: "Camera video", why: "Eye contact, posture, gestures, expression",
    where: [["browser", "the live face and pose tracking"], ["server", "the recording is analysed here; video never goes to a cloud AI"]],
    kept: "With the recording (see above)" },
  { icon: FileText, what: "What you say (transcripts)", why: "The AI partner's replies; feedback on your answers",
    where: [["cloud", "Google Gemini writes the replies and the feedback"], ["server", "stored with the session"]],
    kept: "Until you delete the session" },
  { icon: FileText, what: "Resume", why: "Interview questions that fit your background",
    where: [["server", "only the extracted text, inside that interview session; the file isn't kept"], ["cloud", "the text goes to Gemini to plan the questions"]],
    kept: "With the interview session" },
  { icon: FileText, what: "Slides", why: "Deck insights, the slide-by-slide check, Q&A questions",
    where: [["server", "the deck and its slide images, visible only to you"], ["cloud", "the slide text goes to Gemini"]],
    kept: "Until you delete the deck" },
  { icon: Database, what: "Results and scores", why: "Your results page, progress and tasks",
    where: [["server", "stored with each session"]], kept: "Until you delete the session" },
];

const SECURITY: { icon: LucideIcon; title: string; body: string }[] = [
  { icon: KeyRound, title: "Passwords", body: "Stored only as a bcrypt hash; nobody can read your password, including us. Deleting your account asks for it again." },
  { icon: Timer, title: "Sign-in", body: "A short-lived sign-in token (30 minutes), renewed by a refresh token in a protected cookie that page scripts can't read (7 days)." },
  { icon: Lock, title: "Only you see your data", body: "Every session, result, deck and slide image is checked against your account; anyone else gets “not found”. Slide images are fetched with your sign-in, not public links." },
  { icon: Cloud, title: "Nothing goes to the cloud without consent", body: "Speech recognition, the AI partner and deck uploads refuse to run until you agree, and need an account." },
  { icon: ShieldCheck, title: "Limits against abuse", body: "Rate limits on sign-in and on every AI feature, and size caps on uploads (decks 100 MB, resumes 5 MB, recordings 500 MB)." },
  { icon: Eye, title: "Honest results", body: "AI answers are checked before you see them, and “stronger answers” may not invent facts you never said. Anything that couldn't be measured is shown as unavailable, never guessed." },
];

const RIGHTS: [string, React.ReactNode][] = [
  ["See your data", <>Every session and result is on <Link href="/progress" className="underline">Progress</Link>; download everything below.</>],
  ["Correct it", <>Edit your details on <Link href="/profile" className="underline">Profile</Link>; delete any session or deck.</>],
  ["Withdraw consent", "Any time, below. Cloud features stop until you agree again; your stored results stay."],
  ["Erase it", "Delete your account below: every row and file is removed."],
];

export default function PrivacyPage() {
  return (
    <div className="px-4 sm:px-6 py-6 max-w-[960px] mx-auto space-y-5">
      <PageHeader eyebrow="Privacy & security" title="Your data, plainly">
        What SpeechMate collects, where it goes, how long it&apos;s kept and how it&apos;s protected, under Malaysia&apos;s
        Personal Data Protection Act 2010. Your controls are at the bottom.
      </PageHeader>

      {/* The short version */}
      <div className="grid sm:grid-cols-3 gap-3">
        {[
          ["Video stays with us", "Camera analysis runs in your browser and on our server; video never goes to a cloud AI."],
          ["Recordings don't linger", "Deleted as soon as their results are ready, unless you choose to keep them."],
          ["You're in control", "Agree or withdraw, download everything, or delete your account at any time."],
        ].map(([t, b]) => (
          <div key={t} className="p-4 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
            <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{t}</p>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--ink-2)" }}>{b}</p>
          </div>
        ))}
      </div>

      <Card title="What we collect and where it goes">
        <div className="flex flex-wrap gap-3 mb-4 text-xs" aria-label="Legend">
          {(Object.keys(WHERE) as Where[]).map((w) => (
            <span key={w} className="inline-flex items-center gap-1.5" style={{ color: "var(--ink-2)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: WHERE[w].color }} />{WHERE[w].label}
            </span>
          ))}
        </div>
        <ul className="divide-y divide-[var(--line-2)]">
          {DATA.map(({ icon: Icon, what, why, where, kept }) => (
            <li key={what} className="py-4 first:pt-0 last:pb-0 grid sm:grid-cols-[220px_1fr] gap-x-6 gap-y-2">
              <div className="flex gap-3">
                <span className="w-9 h-9 flex-shrink-0 rounded-lg flex items-center justify-center" style={{ background: "var(--surface-3)" }}>
                  <Icon className="w-4 h-4" style={{ color: "var(--ink-2)" }} />
                </span>
                <div>
                  <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{what}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{why}</p>
                </div>
              </div>
              <div className="space-y-1.5 text-sm">
                {where.map(([w, text]) => (
                  <p key={text} className="flex gap-2" style={{ color: "var(--ink-2)" }}>
                    <span className="mt-1.5 w-2 h-2 flex-shrink-0 rounded-full" style={{ background: WHERE[w].color }} aria-hidden />
                    <span><b className="font-semibold" style={{ color: "var(--ink)" }}>{WHERE[w].label}:</b> {text}</span>
                  </p>
                ))}
                <p className="text-xs" style={{ color: "var(--muted)" }}><b>Kept:</b> {kept}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="The cloud services we use">
        <div className="grid sm:grid-cols-2 gap-4 text-sm" style={{ color: "var(--ink-2)" }}>
          <div>
            <p className="font-semibold" style={{ color: "var(--ink)" }}>Groq (speech-to-text)</p>
            <p className="mt-1">Receives audio of what you say and returns the words. Nothing else about you.</p>
          </div>
          <div>
            <p className="font-semibold" style={{ color: "var(--ink)" }}>Google Gemini (language AI)</p>
            <p className="mt-1">
              Receives text: your answers, the partner conversation, resume and slide text, and your level and goals. On
              Gemini&apos;s free tier Google may use requests to improve its products (see{" "}
              <a href="https://ai.google.dev/gemini-api/terms" target="_blank" rel="noreferrer" className="underline">Google&apos;s terms</a>);
              a paid key avoids that.
            </p>
          </div>
        </div>
        <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
          We never sell your data or use it for advertising. A fully local setup that sends nothing to the cloud is possible on a
          suitable computer (see the project README).
        </p>
      </Card>

      <Card title="How your data is protected">
        <div className="grid sm:grid-cols-2 gap-x-6 gap-y-4">
          {SECURITY.map(({ icon: Icon, title, body }) => (
            <div key={title} className="flex gap-3">
              <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: "var(--accent-ink)" }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--ink)" }}>{title}</p>
                <p className="text-xs mt-0.5 leading-relaxed" style={{ color: "var(--ink-2)" }}>{body}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Your rights">
        <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {RIGHTS.map(([k, v]) => (
            <div key={k}>
              <dt className="font-semibold" style={{ color: "var(--ink)" }}>{k}</dt>
              <dd className="mt-0.5" style={{ color: "var(--ink-2)" }}>{v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <div id="controls" className="scroll-mt-24" />
      <Card title="Your controls">
        <PrivacyControls />
      </Card>
    </div>
  );
}
