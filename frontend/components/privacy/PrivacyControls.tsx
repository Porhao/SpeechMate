"use client";

// Your privacy controls (PDPA): cloud-processing consent, keeping recordings, downloading all
// your data, and deleting the account. On the Privacy & security page.

import { useState, useSyncExternalStore } from "react";
import { Download, Loader2, Trash2 } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { authService } from "@/services/auth";
import { mascot } from "@/lib/mascot";
import { Button, Notice, inputClass, inputStyle } from "@/components/ui/kit";

export function Row({ label, description, children }: { label: string; description?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 border-b border-[var(--line-2)] last:border-b-0">
      <div className="min-w-0 flex-1 basis-64">
        <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>{label}</p>
        {description && <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{description}</p>}
      </div>
      {children}
    </div>
  );
}

export default function PrivacyControls() {
  const user = useUserStore((s) => s.user);
  const setUser = useUserStore((s) => s.setUser);
  const clearUser = useUserStore((s) => s.logout);
  const hydrated = useSyncExternalStore(() => () => {}, () => true, () => false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState("");

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setError(null);
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong"); mascot("error"); } finally { setBusy(null); }
  };
  const consented = hydrated && !!user?.cloud_consent_at;

  return (
    <div>
      <Row label="Cloud processing"
        description={consented
          ? `You agreed on ${new Date(user!.cloud_consent_at!).toLocaleDateString("en-MY", { dateStyle: "medium" })}: your voice goes to Groq (speech-to-text), text to Google Gemini.`
          : "Not agreed: practice sessions, interview plans and deck uploads are off until you agree."}>
        <Button variant="secondary" disabled={!hydrated || busy === "consent"}
          onClick={() => run("consent", async () => setUser(await authService.setConsent(!consented)))}>
          {busy === "consent" && <Loader2 className="w-4 h-4 animate-spin" />}{consented ? "Withdraw" : "Agree"}
        </Button>
      </Row>
      <Row label="Keep recordings" description="Off: each recording is deleted as soon as its results are ready (the results are kept).">
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--ink-2)" }}>
          <input type="checkbox" className="w-4 h-4 accent-[var(--accent)]" checked={hydrated && !!user?.keep_recordings}
            disabled={!hydrated || busy === "keep"}
            onChange={(e) => { const keep = e.target.checked; run("keep", async () => setUser(await authService.updateProfile({ keep_recordings: keep }))); }} />
          {hydrated && user?.keep_recordings ? "On" : "Off"}
        </label>
      </Row>
      <Row label="Download my data" description="Your profile, sessions, results, decks and notifications as one JSON file">
        <Button variant="secondary" disabled={busy === "export"}
          onClick={() => run("export", async () => { await authService.exportData(); mascot("success", "Your data is downloading."); })}>
          {busy === "export" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Download
        </Button>
      </Row>
      <Row label="Delete my account" description="Deletes your account, sessions, results, recordings and decks. This can't be undone.">
        {!deleting ? (
          <Button variant="secondary" onClick={() => { setDeleting(true); setError(null); }}>
            <Trash2 className="w-4 h-4" /> Delete account
          </Button>
        ) : (
          <form className="flex flex-wrap items-center gap-2 w-full sm:w-auto"
            onSubmit={(e) => { e.preventDefault(); run("delete", async () => {
              await authService.deleteAccount(password);
              await authService.logout(); clearUser(); window.location.href = "/login";
            }); }}>
            <label className="sr-only" htmlFor="delete-password">Your password</label>
            <input id="delete-password" type="password" autoComplete="current-password" required placeholder="Your password"
              className={inputClass + " sm:w-48"} style={inputStyle} value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button type="submit" disabled={!password || busy === "delete"} style={{ background: "var(--bad)", borderColor: "var(--bad)", color: "#fff" }}>
              {busy === "delete" && <Loader2 className="w-4 h-4 animate-spin" />} Delete forever
            </Button>
            <Button type="button" variant="ghost" onClick={() => { setDeleting(false); setPassword(""); }}>Cancel</Button>
          </form>
        )}
      </Row>
      {error && <div className="pt-3"><Notice tone="bad">{error}</Notice></div>}
    </div>
  );
}
