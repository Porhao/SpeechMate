"use client";

// The session page's display pieces: message bubble, mic pulse, voice glow, volume meter,
// live transcript and the partner's character. Stateless apart from UserBubble's edit box.

import { useState, useSyncExternalStore, type ReactNode } from "react";
import { VoiceBeam as VoiceGlow } from "voice-glow";
import { BotAvatar } from "bot-avatars";
import { Pencil } from "lucide-react";
import { subscribeTheme } from "@/lib/theme";
import type { SessionType } from "@/types";

export type OrbState = "idle" | "thinking" | "speaking" | "listening";

// ── The user's own message, with "Fix" for when speech recognition misheard ──
export function UserBubble({ text, className, style, onFix }: {
  text: string; className: string; style: React.CSSProperties; onFix: (text: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  if (editing) {
    return (
      <form className="flex-1 max-w-[85%] flex flex-col gap-1.5" onSubmit={(e) => { e.preventDefault(); onFix(draft); setEditing(false); }}>
        <textarea autoFocus value={draft} onChange={(e) => setDraft(e.target.value)} rows={2} aria-label="What you actually said"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onFix(draft); setEditing(false); } if (e.key === "Escape") setEditing(false); }}
          className="w-full px-3 py-2 rounded-md text-sm outline-none" style={{ background: "var(--surface)", border: "1px solid var(--accent-ink)", color: "var(--ink)" }} />
        <span className="flex gap-2 justify-end">
          <button type="button" onClick={() => setEditing(false)} className="text-xs font-semibold px-3 py-1.5 rounded-md" style={{ color: "var(--muted)" }}>Cancel</button>
          <button type="submit" className="text-xs font-semibold px-3 py-1.5 rounded-md text-white" style={{ background: "var(--accent)" }}>Save</button>
        </span>
      </form>
    );
  }
  return (
    <div className="group flex flex-row-reverse items-start gap-1.5 max-w-[85%]">
      <div className={className} style={style}>{text}</div>
      <button onClick={() => { setDraft(text); setEditing(true); }} title="Misheard? Correct what you said"
        aria-label={`Fix this message: ${text}`}
        className="mt-1 flex items-center gap-1 text-[11px] font-semibold px-1.5 py-1 rounded-md opacity-60 group-hover:opacity-100 focus-visible:opacity-100 hover:bg-[var(--surface-3)]"
        style={{ color: "var(--muted)" }}>
        <Pencil className="w-3 h-3" /> Fix
      </button>
    </div>
  );
}

// ── Header mic pulse — tiny live waveform next to the session timer ──────────
export function HeaderPulse({ level, active, color = "#3E6FB0" }: { level: number; active: boolean; color?: string }) {
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

// ── Voice beam — a sound-reactive glow along the input bar's bottom edge (voice-glow) ──
// Follows the user's own mic (low / mid / high bands) while they can speak, holds a soft
// glow while the partner thinks, and fades out otherwise. The centre lobe is the mode colour.
// The package stops its breathing, flow and hue drift under reduced motion.
export function VoiceBeam({ stream, listening, thinking, color, children }: {
  stream: MediaStream | null; listening: boolean; thinking: boolean; color: string; children: ReactNode;
}) {
  const theme = useResolvedTheme();
  return (
    <VoiceGlow className="flex-1 min-w-0" theme={theme} colors={[color]}
      stream={listening ? stream : null} level={thinking ? 0.35 : 0} active={listening || thinking}>
      {children}
    </VoiceGlow>
  );
}

// ── Volume meter — how loud the user is, live, against a comfortable band ──────
// ponytail: thresholds on the browser's average spectrum level (0–1), set by ear on a laptop mic;
// calibrate per mic, or map to the analysis' loudness metric if the two need to agree.
export const VOL_FULL = 0.4, VOL_QUIET = 0.03, VOL_LOUD = 0.3;
export function VolumeMeter({ level, muted, speaking }: { level: number; muted: boolean; speaking: boolean }) {
  const [label, color] =
    muted ? ["Muted", "var(--muted)"] :
    !speaking ? ["Waiting for you", "var(--muted)"] :
    level < VOL_QUIET ? ["Too quiet", "var(--warn)"] :
    level > VOL_LOUD ? ["Very loud", "var(--warn)"] : ["Good", "var(--ok)"];
  const pct = (v: number) => `${Math.min(100, (v / VOL_FULL) * 100)}%`;
  return (
    <span className="flex items-center gap-2" role="status" aria-label={`Your volume: ${label}`}>
      Volume
      <span className="relative w-32 h-2 rounded-full overflow-hidden" style={{ background: "var(--line)" }}>
        {/* the comfortable band */}
        <span className="absolute inset-y-0" style={{ left: pct(VOL_QUIET), width: `calc(${pct(VOL_LOUD)} - ${pct(VOL_QUIET)})`, background: "color-mix(in srgb, var(--ok) 25%, transparent)" }} />
        <span className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-100"
          style={{ width: muted ? 0 : pct(level), background: color }} />
      </span>
      <b style={{ color }}>{label}</b>
    </span>
  );
}

// ── Live transcript — the user's words, phrase by phrase as they are transcribed ──
// A two-line window pinned to the newest words: older lines slide up under a fade, and the
// newest phrase fades in. The status ("Hearing you…", "Transcribing…") sits in the label.
export function LiveTranscript({ transcript, newest, status, color }: {
  transcript: string; newest: { text: string; key: number } | null; status: string; color: string;
}) {
  const fresh = newest && transcript.endsWith(newest.text) ? newest : null;
  const older = fresh ? transcript.slice(0, -fresh.text.length).trimEnd() : transcript;
  return (
    <div className="flex-shrink-0 px-4 py-2.5 rounded-xl" aria-live="polite"
      style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
      <p className="flex items-center gap-1.5 text-[10px] text-[var(--faint)] font-semibold uppercase tracking-wider mb-1">
        {status === "Hearing you…" && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />}
        Live transcript
        {status && <span className="normal-case tracking-normal font-normal italic">· {status}</span>}
      </p>
      <div className="live-transcript-window text-sm leading-snug text-[var(--ink-2)]">
        <p>
          {older}
          {fresh && <span key={fresh.key} className="live-phrase-in text-[var(--ink)]">{older ? " " : ""}{fresh.text}</span>}
        </p>
      </div>
    </div>
  );
}

// ── Partner character (bot-avatars) ───────────────────────────────────────────
// One character per mode. It sleeps before the session, looks around while you talk,
// and hops while it thinks or speaks.
export const PARTNER_BOTS = {
  Conversation: { type: "cat", face: "mouth", headphones: true },
  Interview:    { type: "mech", face: "mouth", glasses: "square", bowTie: true },
  Presentation: { type: "droid", face: "mouth", hat: "beret", glasses: "round" },
} as const;

export function useResolvedTheme() {
  return useSyncExternalStore(subscribeTheme, () => document.documentElement.dataset.theme === "dark" ? "dark" : "light", () => "light" as const);
}

export function PartnerBot({ mode, state, started, size, theme }: {
  mode: SessionType; state: OrbState; started: boolean; size: number; theme?: "light" | "dark";
}) {
  const appTheme = useResolvedTheme();
  return (
    <BotAvatar {...PARTNER_BOTS[mode]} size={size} theme={theme ?? appTheme}
      state={!started ? "sleeping" : state === "speaking" || state === "thinking" ? "working" : "default"} />
  );
}
