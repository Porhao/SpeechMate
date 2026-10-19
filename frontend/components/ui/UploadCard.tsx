"use client";

// The upload animation: the file card lifts while it travels, a striped bar fills with the real
// upload progress, "Reading it…" while the server takes over, then a check pops with a small
// burst. `progress` is 0–1 (null before the upload starts).

import { CheckCircle2, FileText, Loader2 } from "lucide-react";

export type UploadPhase = "idle" | "uploading" | "processing" | "done";

const BURST = [[-34, -26], [30, -30], [40, 6], [-40, 8], [-8, -40], [14, 34], [-22, 30]] as const;
const BURST_COLORS = ["var(--pink)", "var(--peach)", "var(--lavender)", "var(--ok)"];

export default function UploadCard({ name, size, phase, progress, color, processingLabel = "Reading it…" }: {
  name: string; size: number; phase: UploadPhase; progress: number | null; color: string; processingLabel?: string;
}) {
  const pct = Math.round((progress ?? 0) * 100);
  const working = phase === "uploading" || phase === "processing";
  return (
    <div className="w-full max-w-md flex items-center gap-3 text-left" aria-live="polite">
      <span className={`relative flex-shrink-0 w-11 h-12 rounded-lg flex items-center justify-center ${working ? "upload-lift" : ""}`}
        style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-card)" }}>
        {phase === "done"
          ? <CheckCircle2 className="upload-check w-6 h-6" style={{ color: "var(--ok)" }} />
          : <FileText className="w-6 h-6" style={{ color }} />}
        {phase === "done" && BURST.map(([dx, dy], i) => (
          <span key={i} className="upload-burst" aria-hidden
            style={{ "--dx": `${dx}px`, "--dy": `${dy}px`, background: BURST_COLORS[i % BURST_COLORS.length] } as React.CSSProperties} />
        ))}
      </span>
      <span className="flex-1 min-w-0">
        <span className="block text-sm font-semibold truncate" style={{ color: "var(--ink)" }}>{name}</span>
        {phase === "idle" ? (
          <span className="block text-xs" style={{ color: "var(--faint)" }}>{(size / 1024 / 1024).toFixed(1)} MB · click to change</span>
        ) : (
          <>
            <span className="mt-1.5 block h-2 rounded-full overflow-hidden" style={{ background: "var(--line)" }}
              role="progressbar" aria-valuenow={phase === "uploading" ? pct : 100} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress">
              <span className={`block h-full rounded-full ${working ? "upload-bar" : ""}`}
                style={{ width: `${phase === "uploading" ? Math.max(4, pct) : 100}%`, background: phase === "done" ? "var(--ok)" : color }} />
            </span>
            <span className="mt-1 flex items-center gap-1.5 text-xs" style={{ color: "var(--muted)" }}>
              {phase === "uploading" && <>Uploading… {pct}%</>}
              {phase === "processing" && <><Loader2 className="w-3 h-3 animate-spin" /> {processingLabel}</>}
              {phase === "done" && <span style={{ color: "var(--ok)" }}>Uploaded</span>}
            </span>
          </>
        )}
      </span>
    </div>
  );
}
