"use client";

// "CONTACT" spelled on a dock of 3D keycaps. Sweep the pointer across it: keys grow like a
// dock (magnified by distance to the pointer), and a key that holds a link turns over to show
// its icon. Keyboard focus turns a key too; on touch screens link keys show their icon.
// Fill in CONTACT_LINKS below: a key whose href is empty stays a plain letter.

import { useRef, type CSSProperties, type PointerEvent, type ReactNode } from "react";
import { Mail } from "lucide-react";

type ContactLink = { label: string; href: string; icon: ReactNode; brand: string };

const GITHUB = "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12";
const LINKEDIN = "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z";
const brandIcon = (d: string) => <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor" aria-hidden><path d={d} /></svg>;

// Letter position (0-6 of C-O-N-T-A-C-T) → the link that key turns into
const CONTACT_LINKS: Record<number, ContactLink> = {
  1: { label: "Email", href: "", icon: <Mail className="w-6 h-6" strokeWidth={2} />, brand: "#D6245F" },   // e.g. "mailto:you@example.com"
  2: { label: "LinkedIn", href: "", icon: brandIcon(LINKEDIN), brand: "#0A66C2" },                          // e.g. "https://www.linkedin.com/in/you"
  3: { label: "GitHub", href: "", icon: brandIcon(GITHUB), brand: "#181717" },                              // e.g. "https://github.com/you"
};

const WORD = "CONTACT";
const REACH = 140;  // px: how far from the pointer keys still grow

export default function ContactDock() {
  const dock = useRef<HTMLDivElement>(null);

  // Dock magnification: each key scales with its distance to the pointer
  const onMove = (e: PointerEvent) => {
    if (e.pointerType === "touch") return;
    dock.current?.querySelectorAll<HTMLElement>(".cd-key").forEach((k) => {
      const r = k.getBoundingClientRect();
      const near = Math.max(0, 1 - Math.abs(e.clientX - (r.left + r.width / 2)) / REACH);
      k.style.setProperty("--s", String(1 + near * near * 0.45));
    });
  };
  const onLeave = () => dock.current?.querySelectorAll<HTMLElement>(".cd-key").forEach((k) => k.style.setProperty("--s", "1"));

  return (
    <div ref={dock} className="cd-dock" onPointerMove={onMove} onPointerLeave={onLeave} role="navigation" aria-label="Contact">
      {[...WORD].map((letter, i) => {
        const link = CONTACT_LINKS[i]?.href ? CONTACT_LINKS[i] : null;
        const cap = (
          <span className="cd-cap">
            <span className="cd-face">{letter}</span>
            {link && <span className="cd-face cd-face--icon" style={{ color: link.brand }}>{link.icon}</span>}
          </span>
        );
        return link ? (
          <a key={i} href={link.href} className="cd-key cd-key--link" aria-label={link.label}
            target={link.href.startsWith("mailto:") ? undefined : "_blank"} rel="noreferrer" style={{ "--s": 1 } as CSSProperties}>
            {cap}
            <span className="cd-tip" aria-hidden>{link.label}</span>
          </a>
        ) : (
          <span key={i} className="cd-key" aria-hidden style={{ "--s": 1 } as CSSProperties}>{cap}</span>
        );
      })}
    </div>
  );
}
