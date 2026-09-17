import TopNav from "@/components/layout/TopNav";
import LiquidBottomNav from "@/components/ui/LiquidBottomNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen relative" style={{ background: "#FBFAF7" }}>

      {/* Top navigation */}
      <div style={{ position: "relative", zIndex: 50 }}>
        <TopNav />
      </div>

      {/* Main content — full width, no sidebar. Bottom padding clears the
          liquid tab bar, which is now the primary navigation at every
          screen size. */}
      <main className="pb-[118px]" style={{ position: "relative", zIndex: 10 }}>
        {children}
      </main>

      <LiquidBottomNav />
    </div>
  );
}
