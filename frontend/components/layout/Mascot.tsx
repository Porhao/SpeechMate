"use client";

// The companion character in the corner: "Mate". Its eyes follow the pointer and a click makes
// it hop (bot-avatars' own pointer play); it reacts to what you do (lib/mascot.ts) with a hop,
// wobble, peek, spin or shake and a short speech bubble, works along while something runs,
// and dozes off after a minute of nothing. It hides on the live session page, which has the
// AI partner instead, and can be tucked away (remembered on this device).

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { BotAvatar } from "bot-avatars";
import { ChevronDown, Sparkles } from "lucide-react";
import { MASCOT_EVENT, type MascotAction } from "@/lib/mascot";

const TIPS = [
  "Pause for about 2 seconds when you finish an answer: that's my cue.",
  "Your three drills on each results page are the fastest way to improve.",
  "Tick off a task on Home when you've practised it.",
  "Manglish particles like 'lah' never count as fillers here.",
  "Present your deck first, then rehearse the Q&A from it.",
  "Short daily practice beats one long session a week.",
];
const SAYS: Partial<Record<MascotAction, string>> = {
  success: "Done!", deleted: "Gone. Tidy!", done: "Nice one!", error: "Hmm, that didn't work.", empty: "Nothing matches that.",
};
const MOVE: Record<MascotAction, string> = {
  busy: "", success: "mascot-hop", deleted: "mascot-wobble", search: "mascot-peek",
  empty: "mascot-tilt", done: "mascot-spin", error: "mascot-shake",
};
const IDLE_MS = 60_000;
const HIDE_KEY = "speechmate:mascot-hidden";

// Tucked away or not, per device; read through a store so the server render (shown) can't mismatch
const readHidden = () => { try { return localStorage.getItem(HIDE_KEY) === "1"; } catch { return false; } };
const subscribeHidden = (cb: () => void) => { window.addEventListener(HIDE_KEY, cb); return () => window.removeEventListener(HIDE_KEY, cb); };
const writeHidden = (v: boolean) => {
  try { localStorage.setItem(HIDE_KEY, v ? "1" : "0"); } catch { /* private mode: not remembered */ }
  window.dispatchEvent(new Event(HIDE_KEY));
};

export default function Mascot() {
  const pathname = usePathname();
  const hidden = useSyncExternalStore(subscribeHidden, readHidden, () => false);
  const [move, setMove] = useState<{ cls: string; key: number }>({ cls: "", key: 0 });
  const [bubble, setBubble] = useState<{ text: string; key: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [asleep, setAsleep] = useState(false);
  const tip = useRef(0);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bubbleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const wake = () => {
      setAsleep(false);
      if (idleTimer.current) clearTimeout(idleTimer.current);
      idleTimer.current = setTimeout(() => setAsleep(true), IDLE_MS);
    };
    const say = (text: string) => {
      setBubble({ text, key: Date.now() });
      if (bubbleTimer.current) clearTimeout(bubbleTimer.current);
      bubbleTimer.current = setTimeout(() => setBubble(null), 3200);
    };
    const onAction = (e: Event) => {
      const { action, say: text } = (e as CustomEvent<{ action: MascotAction; say?: string }>).detail;
      wake();
      setBusy(action === "busy");
      if (MOVE[action]) setMove({ cls: MOVE[action], key: Date.now() });
      const line = text ?? SAYS[action];
      if (line) say(line);
    };
    window.addEventListener(MASCOT_EVENT, onAction);
    window.addEventListener("pointerdown", wake);
    window.addEventListener("keydown", wake);
    wake();
    return () => {
      window.removeEventListener(MASCOT_EVENT, onAction);
      window.removeEventListener("pointerdown", wake);
      window.removeEventListener("keydown", wake);
      if (idleTimer.current) clearTimeout(idleTimer.current);
      if (bubbleTimer.current) clearTimeout(bubbleTimer.current);
    };
  }, []);

  if (pathname.startsWith("/session")) return null;

  if (hidden) {
    return (
      <button onClick={() => writeHidden(false)} aria-label="Show Mate, your companion"
        className="clay-nav fixed right-4 bottom-4 z-40 w-11 h-11 rounded-full flex items-center justify-center nav-pill">
        <Sparkles className="w-5 h-5" />
      </button>
    );
  }

  const onClick = () => {
    setBubble({ text: TIPS[tip.current++ % TIPS.length], key: Date.now() });
    if (bubbleTimer.current) clearTimeout(bubbleTimer.current);
    bubbleTimer.current = setTimeout(() => setBubble(null), 5000);
  };

  return (
    <div className="fixed right-4 bottom-4 z-40 flex flex-col items-end gap-1 pointer-events-none">
      {bubble && (
        <p key={bubble.key} role="status" className="mascot-bubble pointer-events-auto max-w-[220px] text-xs leading-snug px-3 py-2 rounded-xl rounded-br-sm"
          style={{ background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
          {bubble.text}
        </p>
      )}
      <div className="relative pointer-events-auto group">
        <button onClick={() => writeHidden(true)} aria-label="Hide Mate"
          className="absolute -top-1 -left-1 z-10 w-5 h-5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
          style={{ background: "var(--surface)", border: "1px solid var(--line)", color: "var(--muted)" }}>
          <ChevronDown className="w-3 h-3" />
        </button>
        <button key={move.key} onClick={onClick} aria-label="Mate, your companion: click for a tip"
          className={`block rounded-full ${move.cls}`}>
          <BotAvatar type="blob" face="eyes" headphones size={72}
            state={busy ? "working" : asleep ? "sleeping" : "default"} />
        </button>
      </div>
    </div>
  );
}
