import type { ReactNode } from "react";

// Sign-in / sign-up render their own full-screen layout (components/auth/AuthShell);
// onboarding centres its own card.
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="min-h-dvh" style={{ background: "var(--bg)" }}>{children}</div>;
}
