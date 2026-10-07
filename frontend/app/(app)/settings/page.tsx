"use client";

// Settings: only what actually works. Appearance, the account, and signing out.

import { useState, useSyncExternalStore } from "react";
import { Loader2, LogOut } from "lucide-react";
import { useUserStore } from "@/store/useUserStore";
import { useAuth } from "@/hooks/useAuth";
import { TextSizeSelector, ThemeSelector } from "@/components/theme/ThemeToggle";
import { Button, Card, LinkButton, PageHeader } from "@/components/ui/kit";

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
    </div>
  );
}
