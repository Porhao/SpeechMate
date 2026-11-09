"use client";

// Settings: only what actually works. Appearance, the account, signing out; privacy has its own page.

import { useState, useSyncExternalStore } from "react";
import { Loader2, LogOut, ShieldCheck } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useAuth } from "@/hooks/useAuth";
import { TextSizeSelector, ThemeSelector } from "@/components/theme/ThemeToggle";
import { Button, Card, LinkButton, PageHeader } from "@/components/ui/kit";
import { Row } from "@/components/privacy/PrivacyControls";

export default function SettingsPage() {
  const user = useUserStore((s) => s.user);
  const hydrated = useSyncExternalStore(() => () => {}, () => true, () => false);
  const { logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  return (
    <div className="px-4 sm:px-6 py-6 max-w-[760px] mx-auto space-y-5">
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
        <Row label="Profile" description="Name, study level, field, goals and feedback style">
          <LinkButton href="/profile" variant="secondary">Edit profile</LinkButton>
        </Row>
        <Row label="Sign out" description="Sign out of SpeechMate on this browser">
          <Button variant="secondary" disabled={signingOut}
            onClick={async () => { setSigningOut(true); await logout(); }}>
            {signingOut ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogOut className="w-4 h-4" />} Sign out
          </Button>
        </Row>
      </Card>

      <Card title="Privacy & security">
        <Row label="Your data and how it's protected" description="What's collected, where it goes and how long it's kept; consent, download and account deletion">
          <LinkButton href="/privacy" variant="secondary"><ShieldCheck className="w-4 h-4" /> Open</LinkButton>
        </Row>
      </Card>
    </div>
  );
}
