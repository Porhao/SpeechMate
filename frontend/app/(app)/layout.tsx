import TopNav from "@/components/layout/TopNav";
import ContactDock from "@/components/layout/ContactDock";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded-md"
        style={{ background: "var(--accent)", color: "#fff" }}>
        Skip to content
      </a>
      <TopNav />
      <main id="main" className="pb-12 flex-1">{children}</main>
      <footer className="px-4 sm:px-6 pb-10 pt-6 flex flex-col items-center gap-3" style={{ borderTop: "1px solid var(--line-2)" }}>
        <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--muted)" }}>Get in touch</p>
        <ContactDock />
        <p className="text-xs" style={{ color: "var(--faint)" }}>SpeechMate · Final Year Project</p>
      </footer>
    </div>
  );
}
