"use client";

// Asks once for consent to cloud processing (PDPA): SpeechMate sends your voice to Groq for
// speech-to-text and text to Google Gemini. Opens for signed-in users who haven't agreed yet,
// and again whenever the server refuses for lack of consent (api.ts fires CONSENT_EVENT).
// "Not now" closes it; practice sessions then stay unavailable until they agree.

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { authService } from "@/services/auth";
import { CONSENT_EVENT } from "@/services/api";
import { useUserStore } from "@/store/useUserStore";
import { Button } from "@/components/ui/kit";

export default function ConsentGate() {
  const setUser = useUserStore((s) => s.setUser);
  const [open, setOpen] = useState(false);
  const [keep, setKeep] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener(CONSENT_EVENT, show);
    if (authService.isSignedIn()) {
      authService.me().then((u) => { setUser(u); setKeep(u.keep_recordings); if (!u.cloud_consent_at) setOpen(true); }).catch(() => null);
    }
    return () => window.removeEventListener(CONSENT_EVENT, show);
  }, [setUser]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const agree = async () => {
    setSaving(true); setError(null);
    try {
      await authService.setConsent(true);
      setUser(await authService.updateProfile({ keep_recordings: keep }));
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4" style={{ background: "rgba(10,10,10,0.55)" }}>
      <div role="dialog" aria-modal="true" aria-labelledby="consent-title" className="w-full max-w-[520px] rounded-xl p-6 clay"
        style={{ background: "var(--surface)", border: "1px solid var(--line)" }}>
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-5 h-5" style={{ color: "var(--accent-ink)" }} aria-hidden />
          <h2 id="consent-title" className="font-display text-xl" style={{ color: "var(--ink)" }}>Before you practise</h2>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>
          To coach you, SpeechMate sends some of your data to two cloud services:
        </p>
        <ul className="text-sm leading-relaxed mt-2 space-y-1.5 list-disc pl-5" style={{ color: "var(--ink-2)" }}>
          <li><b>Your voice</b> goes to <b>Groq</b> to turn speech into text.</li>
          <li><b>Text</b> (what you said, your interview details and resume text, your slides) goes to <b>Google Gemini</b> for the AI partner and feedback.</li>
          <li>Your <b>camera video stays here</b>: face and posture are analysed on SpeechMate&apos;s own server.</li>
        </ul>
        <label className="flex items-start gap-2.5 mt-4 text-sm cursor-pointer" style={{ color: "var(--ink-2)" }}>
          <input type="checkbox" className="mt-0.5 w-4 h-4 accent-[var(--accent)]" checked={keep} onChange={(e) => setKeep(e.target.checked)} />
          <span>
            Keep my recordings after analysis so I can re-analyse them.
            <span className="block text-xs" style={{ color: "var(--muted)" }}>Off: each recording is deleted as soon as its results are ready. Results are kept either way.</span>
          </span>
        </label>
        <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
          You can withdraw, download your data or delete your account any time in Settings.
        </p>
        {error && <p className="text-sm mt-3" role="alert" style={{ color: "var(--bad)" }}>{error}</p>}
        <div className="flex flex-wrap justify-end gap-2 mt-5">
          <Button variant="ghost" onClick={() => setOpen(false)}>Not now</Button>
          <Button autoFocus onClick={agree} disabled={saving}>{saving ? "Saving…" : "I agree"}</Button>
        </div>
      </div>
    </div>
  );
}
