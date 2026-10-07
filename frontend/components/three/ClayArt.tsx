"use client";

// The 3D clay scene in a soft clay panel, for page heroes. Desktop only (one WebGL
// context per page, nothing to download on phones); click it to squash the clay.

import dynamic from "next/dynamic";
import { useIsDesktop } from "@/components/auth/AuthShell";
import { cn } from "@/lib/utils";
import type { ClayVariant } from "./ClayScene";

const ClayScene = dynamic(() => import("./ClayScene"), { ssr: false });

const BG: Record<ClayVariant, string> = {
  mic: "radial-gradient(90% 90% at 50% 40%, #FFE3CF, var(--peach))",
  interview: "radial-gradient(90% 90% at 50% 40%, #F1ECFD, var(--lavender))",
  present: "radial-gradient(90% 90% at 50% 40%, #E3F3EE, var(--mint))",
  logo: "radial-gradient(90% 90% at 50% 40%, #FFE3CF, var(--peach))",
};

export default function ClayArt({ variant, className }: { variant: ClayVariant; className?: string }) {
  const isDesktop = useIsDesktop();
  if (!isDesktop) return null;
  return (
    <div className={cn("clay relative rounded-xl overflow-hidden cursor-pointer", className)} style={{ background: BG[variant] }}
      title="Click me">
      <ClayScene variant={variant} className="absolute inset-0" />
    </div>
  );
}
