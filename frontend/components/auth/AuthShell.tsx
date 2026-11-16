"use client";

// Shared layout for the sign-in and sign-up screens: one centred card with the 3D clay
// microphone on top and the form below. No marketing panel: the app opens straight on the form.

import { useSyncExternalStore, type ReactNode } from "react";
import dynamic from "next/dynamic";
import { Mic2 } from "lucide-react";

const ClayScene = dynamic(() => import("@/components/three/ClayScene"), { ssr: false });

const DESKTOP_QUERY = "(min-width: 1024px)";
export function useIsDesktop(): boolean | null {
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

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-dvh flex items-center justify-center px-4 py-10" style={{ background: "var(--bg)" }}>
      <div className="w-full max-w-[420px]">
        <div className="flex items-center justify-center gap-2.5 mb-5">
          <div className="clay w-9 h-9 rounded-sm flex items-center justify-center" style={{ background: "var(--pink)" }}>
            <Mic2 className="w-[18px] h-[18px] text-white" />
          </div>
          <span className="font-display text-[19px] text-[var(--ink)]">SpeechMate</span>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          {/* Click the mic to squash it like clay */}
          <div className="relative h-48 cursor-pointer" title="Click me"
            style={{ background: "radial-gradient(90% 90% at 50% 40%, #FFE3CF, var(--peach))" }}>
            <ClayScene variant="mic" className="absolute inset-0" />
          </div>
          <div className="p-6 sm:p-8">{children}</div>
        </div>
      </div>
    </main>
  );
}
