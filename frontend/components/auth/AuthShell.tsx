"use client";

// Shared layout for the sign-in and sign-up screens: the 3D voice orb on the left
// (a compact header on small screens) and the form on the right. Typing in the form
// makes the orb "listen"; `useOrbPulse()` lets other actions trigger it too.

import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import dynamic from "next/dynamic";
import { Mic2 } from "lucide-react";

const VoiceOrb = dynamic(() => import("./VoiceOrb"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-1/3 aspect-square rounded-full animate-pulse" style={{ background: "radial-gradient(circle, #5A547033, transparent 70%)" }} />
    </div>
  ),
});

// Only one orb is mounted (desktop panel or mobile header), so there's one WebGL context
const DESKTOP_QUERY = "(min-width: 1024px)";
function useIsDesktop(): boolean | null {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(DESKTOP_QUERY);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => window.matchMedia(DESKTOP_QUERY).matches,
    () => null, // server render: decide on the client
  );
}

const OrbPulseContext = createContext<() => void>(() => {});

/** Call the returned function (e.g. on every keystroke) to make the orb react. */
export function useOrbPulse() {
  return useContext(OrbPulseContext);
}

function Wordmark({ light = false }: { light?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "var(--accent)" }}>
        <Mic2 className="w-[18px] h-[18px] text-white" />
      </div>
      <span className="font-semibold text-[17px] tracking-tight" style={{ color: light ? "var(--bg)" : "var(--ink)" }}>
        SpeechMate
      </span>
    </div>
  );
}

export default function AuthShell({ children, busy = false }: { children: ReactNode; busy?: boolean }) {
  const energyRef = useRef(0);
  const [listening, setListening] = useState(false);
  const quietTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pulse = useCallback(() => {
    energyRef.current = Math.min(1, energyRef.current + 0.35);
    setListening(true);
    if (quietTimer.current) clearTimeout(quietTimer.current);
    quietTimer.current = setTimeout(() => setListening(false), 900);
  }, []);
  useEffect(() => () => { if (quietTimer.current) clearTimeout(quietTimer.current); }, []);

  const isDesktop = useIsDesktop();
  const status = busy ? "Signing you in…" : listening ? "Listening…" : "Ready when you are";

  return (
    <OrbPulseContext.Provider value={pulse}>
      <div className="min-h-dvh grid lg:grid-cols-[minmax(0,1.15fr)_minmax(440px,1fr)]" style={{ background: "var(--bg)" }}>

        {/* ── Orb panel (desktop) ────────────────────────────────────────── */}
        <aside
          className="relative hidden lg:block overflow-hidden"
          style={{ background: "radial-gradient(120% 90% at 50% 45%, var(--surface-2) 0%, var(--surface-3) 60%, var(--line) 100%)" }}
        >
          <div className="absolute top-8 left-10 z-10"><Wordmark /></div>
          {isDesktop && <VoiceOrb energyRef={energyRef} busy={busy} className="absolute inset-0" />}
          <div className="absolute bottom-10 left-0 right-0 flex justify-center z-10">
            <div
              className="flex items-center gap-2 text-xs font-medium px-3 py-1.5"
              style={{ background: "var(--bg)", border: "1px solid var(--line-strong)", color: "var(--ink-2)" }}
              aria-live="polite"
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: busy ? "#8A5A22" : listening ? "#3F6B4C" : "var(--faint)" }}
              />
              {status}
            </div>
          </div>
        </aside>

        {/* ── Form ───────────────────────────────────────────────────────── */}
        {/* Any typing in the form makes the orb react ("listening") */}
        <main className="flex flex-col justify-center px-6 sm:px-12 lg:px-16 py-10" onInputCapture={pulse}>
          <div className="w-full max-w-[400px] mx-auto">
            <div className="lg:hidden">
              <Wordmark />
              {isDesktop === false
                ? <VoiceOrb energyRef={energyRef} busy={busy} className="h-44 -mx-6 sm:mx-0 my-2" />
                : <div className="h-44 my-2" />}
            </div>
            {children}
          </div>
        </main>
      </div>
    </OrbPulseContext.Provider>
  );
}
