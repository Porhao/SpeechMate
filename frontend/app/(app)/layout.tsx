import TopNav from "@/components/layout/TopNav";
import ContactDock from "@/components/layout/ContactDock";
import ConsentGate from "@/components/layout/ConsentGate";
import SideRail from "@/components/layout/SideRail";
import Mascot from "@/components/layout/Mascot";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded-md"
        style={{ background: "var(--accent)", color: "#fff" }}>
        Skip to content
      </a>
      <TopNav />
      <SideRail />
      <ConsentGate />
      <Mascot />
      {/* lg:pl-20 keeps the content clear of the side rail */}
      <main id="main" className="pb-12 flex-1 lg:pl-20">{children}</main>
      <footer className="px-4 sm:px-6 lg:pl-24 pb-10 pt-6 flex flex-col items-center gap-3" style={{ borderTop: "1px solid var(--line-2)" }}>
        <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--muted)" }}>Get in touch</p>
        {/* Room above the dock: hovered keys rise and show their name */}
        <div className="pt-14"><ContactDock /></div>
        <p className="text-xs" style={{ color: "var(--faint)" }}>SpeechMate · Final Year Project</p>
      </footer>
    </div>
  );
}
