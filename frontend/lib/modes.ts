// The practice functions, in one place: what each is called, its colour, who the partner is, where it's
// set up, and how a session of it is named and opened. Nav, home, lists, results and the session page
// read this. The recorded session types match the backend's SessionType (backend/app/schemas/live.py).

import type { LiveSession, SessionType } from "@/types";

export const SESSION_TYPES: readonly SessionType[] = ["Conversation", "Interview", "Presentation"];
export const isSessionType = (v: string | null): v is SessionType => SESSION_TYPES.includes(v as SessionType);

export const MODES: Record<SessionType, { label: string; title: string; color: string; partner: string; setup: string }> = {
  Conversation: { label: "Conversation", title: "Daily conversation", color: "#D6245F", partner: "Your partner", setup: "/conversation" },
  // The interviewer's name is fixed by the backend's plans (backend/app/services/plans.py)
  Interview: { label: "Mock interview", title: "Mock interview", color: "#1A3A3A", partner: "Alex", setup: "/interview" },
  Presentation: { label: "Presentation Q&A", title: "Presentation Q&A", color: "#6B4FC4", partner: "The moderator", setup: "/presentations" },
};

/** The practice pages in the top nav (Impromptu has no recorded session type). Keep the backend's page
 *  list for Mate (backend/app/services/assistant.py GUIDE) in step with these. */
export const PRACTICE_PAGES = [
  { href: "/conversation", label: "Conversation" },
  { href: "/interview", label: "Interview" },
  { href: "/presentations", label: "Presentation" },
  { href: "/impromptu", label: "Impromptu" },
] as const;

/** A session's name: a deck talk is "Presentation"; the Q&A rehearsal and the rest use their mode's label. */
export function sessionLabel(s: Pick<LiveSession, "session_type" | "context">): string {
  return s.context?.kind === "talk" ? "Presentation" : MODES[s.session_type]?.label ?? s.session_type;
}

/** What the session was about: the role (and company), the deck or the topic. */
export function sessionSubtitle(s: Pick<LiveSession, "session_type" | "context">): string | undefined {
  const c = s.context;
  if (s.session_type === "Interview") return c?.setup ? [c.setup.position, c.setup.company].filter(Boolean).join(" · ") : undefined;
  if (s.session_type === "Presentation") return c?.deck_title;
  return c?.topic;
}

/** The live session page. `live`: a session prepared beforehand (interview plan, deck); `focus`: a drill's goal. */
export function sessionUrl(mode: SessionType, opts: { live?: string; topic?: string; focus?: string } = {}): string {
  const q = new URLSearchParams({ mode });
  for (const [k, v] of Object.entries(opts)) if (v) q.set(k, v);
  return `/session?${q}`;
}
