"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Download,
  Plus,
  Clock,
  BarChart2,
  Filter,
  FileSpreadsheet,
  Loader2,
  ChevronRight,
} from "lucide-react";

const REPORTS = [
  { id: "r-001", name: "Weekly Progress Report — Mar 10",  type: "PDF", scope: "All Sessions",  generated: "Mar 10, 2026 · 9:15 AM",  size: "1.2 MB", sessions: 8,  score: 78 },
  { id: "r-002", name: "Interview Practice Export — Feb 28",type: "CSV", scope: "Mock Interview", generated: "Feb 28, 2026 · 4:30 PM",  size: "84 KB",  sessions: 5,  score: 74 },
  { id: "r-003", name: "Monthly Summary — February",        type: "PDF", scope: "All Sessions",  generated: "Mar 1, 2026 · 12:00 AM",  size: "2.4 MB", sessions: 18, score: 75 },
  { id: "r-004", name: "Pronunciation Training Data — Feb", type: "CSV", scope: "Pronunciation", generated: "Feb 20, 2026 · 3:00 PM",  size: "48 KB",  sessions: 4,  score: 76 },
  { id: "r-005", name: "FYP Research Export — All Time",    type: "CSV", scope: "All Sessions",  generated: "Mar 5, 2026 · 10:45 AM", size: "312 KB", sessions: 42, score: 75 },
];

const REPORT_TYPES = ["All", "PDF", "CSV"] as const;
const SCOPES = ["All Sessions", "AI Conversation", "Mock Interview", "Presentation", "Pronunciation"] as const;

type ReportTypeFilter = (typeof REPORT_TYPES)[number];

function gradeColor(s: number) {
  if (s >= 90) return "#3F6B4C";
  if (s >= 80) return "#23345C";
  if (s >= 70) return "#8A5A22";
  return "#8C3B32";
}

function TypeBadge({ type }: { type: string }) {
  const isPdf = type === "PDF";
  return (
    <span
      className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide"
      style={isPdf
        ? { backgroundColor: "rgba(140,59,50,0.10)", color: "#8C3B32" }
        : { backgroundColor: "rgba(63,107,76,0.10)", color: "#3F6B4C" }
      }
    >
      {isPdf ? <FileText className="w-3 h-3" /> : <FileSpreadsheet className="w-3 h-3" />}
      {type}
    </span>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [filter,     setFilter]     = useState<ReportTypeFilter>("All");
  const [scope,      setScope]      = useState<string>("All Sessions");
  const [generating, setGenerating] = useState(false);
  const [genType,    setGenType]    = useState<"PDF" | "CSV">("PDF");
  const [genScope,   setGenScope]   = useState("All Sessions");
  const [showModal,  setShowModal]  = useState(false);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => { setGenerating(false); setShowModal(false); }, 2200);
  };

  const filtered = REPORTS.filter((r) => {
    const typeOk  = filter === "All" || r.type === filter;
    const scopeOk = scope  === "All Sessions" || r.scope === scope;
    return typeOk && scopeOk;
  });

  return (
    <div className="px-4 sm:px-6 py-6 sm:py-8 max-w-[1320px] mx-auto space-y-6">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl" style={{ color: "#17181C" }}>Reports</h1>
          <p className="text-sm mt-1" style={{ color: "#9B988E" }}>
            Download your progress data and session summaries
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all press-effect"
          style={{ background: "#23345C" }}
        >
          <Plus className="w-4 h-4" /> Generate Report
        </button>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Total Reports",     value: "5",      icon: FileText,  color: "#23345C" },
          { label: "Sessions Analyzed", value: "42",     icon: BarChart2, color: "#5A5470" },
          { label: "Data Exported",     value: "4.1 MB", icon: Download,  color: "#3F6B4C" },
        ].map(({ label, value, icon: Icon, color }, i) => (
          <div key={label} className="glass-card rounded-2xl p-5 flex items-center gap-4 slide-up" style={{ animationDelay: `${i * 0.06}s` }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `${color}18` }}>
              <Icon className="w-5 h-5" style={{ color }} />
            </div>
            <div>
              <p className="text-xl font-bold" style={{ color: "#17181C" }}>{value}</p>
              <p className="text-xs" style={{ color: "#9B988E" }}>{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="glass-card rounded-2xl p-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 text-xs" style={{ color: "#6E6C63" }}>
          <Filter className="w-3.5 h-3.5" /> Filter:
        </div>

        <div
          className="flex gap-1 rounded-xl p-1"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8" }}
        >
          {REPORT_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className="relative px-3 py-1 rounded-lg text-xs font-semibold transition-colors"
              style={{ color: filter === t ? "#17233E" : "#6E6C63" }}
            >
              {filter === t && (
                <motion.div
                  layoutId="reports-filter-pill"
                  className="absolute inset-0 rounded-lg"
                  style={{ background: "#FFFFFF", boxShadow: "0 0 0 1px rgba(35,52,92,0.25)" }}
                  transition={{ type: "spring", stiffness: 480, damping: 34 }}
                />
              )}
              <span className="relative">{t}</span>
            </button>
          ))}
        </div>

        <div className="w-px h-5" style={{ background: "#E6E2D8" }} />

        <select
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          className="text-xs rounded-xl px-3 py-1.5 outline-none transition-colors"
          style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#34343A" }}
        >
          {SCOPES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      {/* Report List */}
      <div className="glass-card rounded-2xl overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 mx-auto mb-3" style={{ color: "#CDC9BE" }} />
            <p className="text-sm" style={{ color: "#9B988E" }}>No reports match your filter</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div style={{ minWidth: 760 }}>
              {/* Header row */}
              <div
                className="grid grid-cols-[1fr_120px_100px_80px_80px_100px] gap-4 px-6 py-3 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: "#9B988E", borderBottom: "1px solid #F0EDE5" }}
              >
                <span>Report</span>
                <span>Scope</span>
                <span>Generated</span>
                <span>Size</span>
                <span>Score</span>
                <span className="text-right">Actions</span>
              </div>

              {filtered.map((r, i) => (
                <div
                  key={r.id}
                  className="grid grid-cols-[1fr_120px_100px_80px_80px_100px] gap-4 px-6 py-4 items-center transition-colors"
                  style={i < filtered.length - 1 ? { borderBottom: "1px solid #F1EEE6" } : {}}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "#F6F3EC"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: "#F1EEE6" }}
                    >
                      {r.type === "PDF"
                        ? <FileText className="w-4 h-4" style={{ color: "#8C3B32" }} />
                        : <FileSpreadsheet className="w-4 h-4" style={{ color: "#3F6B4C" }} />
                      }
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: "#17181C" }}>{r.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <TypeBadge type={r.type} />
                        <span className="text-[10px]" style={{ color: "#9B988E" }}>{r.sessions} sessions</span>
                      </div>
                    </div>
                  </div>

                  <span className="text-xs" style={{ color: "#4B4C52" }}>{r.scope}</span>

                  <div className="flex items-center gap-1 text-xs" style={{ color: "#6E6C63" }}>
                    <Clock className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{r.generated.split(" · ")[0]}</span>
                  </div>

                  <span className="text-xs" style={{ color: "#6E6C63" }}>{r.size}</span>

                  <span className="text-sm font-bold" style={{ color: gradeColor(r.score) }}>{r.score}</span>

                  <div className="flex items-center justify-end">
                    <button
                      className="flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-colors"
                      style={{ color: "#23345C" }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(35,52,92,0.08)"; e.currentTarget.style.color = "#17233E"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#23345C"; }}
                    >
                      <Download className="w-3.5 h-3.5" /> Download
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* FYP Research note */}
      <div
        className="rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center gap-4"
        style={{ background: "#F1EEE6", border: "1px solid #E6E2D8" }}
      >
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: "rgba(35,52,92,0.14)", border: "1px solid rgba(35,52,92,0.28)" }}
        >
          <BarChart2 className="w-5 h-5" style={{ color: "#17233E" }} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold" style={{ color: "#17181C" }}>FYP Research Export</p>
          <p className="text-xs mt-0.5" style={{ color: "#6E6C63" }}>
            Export anonymized pre/post data for your FYP research evaluation (paired T-test, ASR metrics, user satisfaction scores).
          </p>
        </div>
        <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2 flex-shrink-0">
          <button
            onClick={() => router.push("/methodology")}
            className="flex items-center gap-1.5 text-sm font-semibold whitespace-nowrap transition-colors"
            style={{ color: "#23345C" }}
          >
            View Methodology <ChevronRight className="w-4 h-4" />
          </button>
          <button
            className="flex items-center gap-1.5 text-xs font-medium whitespace-nowrap transition-colors"
            style={{ color: "#9B988E" }}
          >
            Research Export <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Generate Modal — a real frosted-glass surface (not just a white card
          on a dimmed backdrop): translucent, blurred, with a soft highlight
          along the top edge like light catching glass. */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            className="fixed inset-0 flex items-center justify-center z-50 p-4"
            style={{ background: "rgba(23,24,28,0.32)" }}
            initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
            animate={{ opacity: 1, backdropFilter: "blur(8px)" }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
            transition={{ duration: 0.22 }}
            onClick={() => setShowModal(false)}
          >
          <motion.div
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-[440px] p-6 rounded-2xl overflow-hidden"
            style={{
              background: "rgba(255,255,255,0.78)",
              backdropFilter: "blur(20px) saturate(1.6)",
              WebkitBackdropFilter: "blur(20px) saturate(1.6)",
              border: "1px solid rgba(255,255,255,0.6)",
              boxShadow: "var(--shadow-modal)",
            }}
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 6 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
          >
            {/* Glass highlight — a soft sheen along the top edge */}
            <div
              className="absolute inset-x-0 top-0 h-24 pointer-events-none"
              style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.5), transparent)" }}
            />
            <h2 className="relative text-base font-bold mb-5" style={{ color: "#17181C" }}>Generate New Report</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "#6E6C63" }}>Format</label>
                <div className="flex gap-2">
                  {(["PDF", "CSV"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setGenType(t)}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border text-sm font-semibold transition-all"
                      style={genType === t
                        ? { borderColor: "#23345C", background: "rgba(35,52,92,0.08)", color: "#17233E" }
                        : { borderColor: "#E6E2D8", color: "#9B988E", background: "#F6F3EC" }
                      }
                    >
                      {t === "PDF" ? <FileText className="w-4 h-4" /> : <FileSpreadsheet className="w-4 h-4" />}
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: "#6E6C63" }}>Session Scope</label>
                <select
                  value={genScope}
                  onChange={(e) => setGenScope(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none transition-all"
                  style={{ background: "#F5F2EB", border: "1px solid #E6E2D8", color: "#17181C" }}
                >
                  {SCOPES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-colors"
                style={{ border: "1px solid #E6E2D8", color: "#4B4C52", background: "#F5F2EB" }}
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-white text-sm font-semibold transition-all disabled:opacity-70"
                style={{ background: "#23345C" }}
              >
                {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</> : "Generate"}
              </button>
            </div>
          </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
