"use client";

// Settings: only what actually works. Appearance, the account, privacy and your data, signing out.

import { useState, useSyncExternalStore } from "react";
import { Download, Loader2, LogOut, Trash2 } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useAuth } from "@/hooks/useAuth";
import { authService } from "@/services/auth";
import { TextSizeSelector, ThemeSelector } from "@/components/theme/ThemeToggle";
import { Button, Card, LinkButton, Notice, PageHeader, inputClass, inputStyle } from "@/components/ui/kit";

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 border-b border-[var(--line-2)] last:border-b-0">
      <div className="min-w-0">
        <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>{label}</p>
        {description && <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{description}</p>}
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const user = useUserStore((s) => s.user);
  const hydrated = useSyncExternalStore(() => () => {}, () => true, () => false);
  const { logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const setUser = useUserStore((s) => s.setUser);
  const clearUser = useUserStore((s) => s.logout);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState("");

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setError(null);
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong"); } finally { setBusy(null); }
  };
  const consented = hydrated && !!user?.cloud_consent_at;

  return (
    <div className="px-4 sm:px-6 py-8 max-w-[760px] mx-auto space-y-5">
      <PageHeader title="Settings" />

      <Card title="Appearance">
        <Row label="Theme" description="Light, dark, or follow your device">
          <ThemeSelector />
        </Row>
        <Row label="Text size" description="Larger text across the app">
          <TextSizeSelector />
        </Row>
      </Card>

      <Card title="Account">
        <Row label="Name">
          <span className="text-sm" style={{ color: "var(--ink-2)" }}>{hydrated ? user?.full_name ?? "Not signed in" : ""}</span>
        </Row>
        <Row label="Email">
          <span className="text-sm break-all" style={{ color: "var(--ink-2)" }}>{hydrated ? user?.email ?? "—" : ""}</span>
        </Row>
        <Row label="Profile" description="Name, language, goal and challenges">
          <LinkButton href="/profile" variant="secondary">Edit profile</LinkButton>
        </Row>
        <Row label="Sign out" description="Sign out of SpeechMate on this browser">
          <Button variant="secondary" disabled={signingOut}
            onClick={async () => { setSigningOut(true); await logout(); }}>
            {signingOut ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogOut className="w-4 h-4" />} Sign out
          </Button>
        </Row>
      </Card>

      {/* The side rail's "Your data & privacy" links here */}
      <div id="privacy" className="scroll-mt-24" />
      <Card title="Privacy & your data">
        <Row label="Cloud processing"
          description={consented
            ? `You agreed on ${new Date(user!.cloud_consent_at!).toLocaleDateString("en-MY", { dateStyle: "medium" })}: your voice goes to Groq (speech-to-text), text to Google Gemini.`
            : "Not agreed: practice sessions, interview plans and deck uploads are off until you agree."}>
          <Button variant="secondary" disabled={!hydrated || busy === "consent"}
            onClick={() => run("consent", async () => setUser(await authService.setConsent(!consented)))}>
            {busy === "consent" && <Loader2 className="w-4 h-4 animate-spin" />}{consented ? "Withdraw" : "Agree"}
          </Button>
        </Row>
        <Row label="Keep recordings" description="Off: each recording is deleted as soon as its results are ready (results are kept).">
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--ink-2)" }}>
            <input type="checkbox" className="w-4 h-4 accent-[var(--accent)]" checked={hydrated && !!user?.keep_recordings}
              disabled={!hydrated || busy === "keep"}
              onChange={(e) => { const keep = e.target.checked; run("keep", async () => setUser(await authService.updateProfile({ keep_recordings: keep }))); }} />
            {hydrated && user?.keep_recordings ? "On" : "Off"}
          </label>
        </Row>
        <Row label="Download my data" description="Your profile, sessions, results, decks and notifications as one JSON file">
          <Button variant="secondary" disabled={busy === "export"} onClick={() => run("export", authService.exportData)}>
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
      </Card>
    </div>
  );
}
