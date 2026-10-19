"use client";

// A bin that wobbles, then asks once ("Delete · Cancel") before anything is deleted.
// The row itself folds away with useExit (hooks/useExit.ts).

import { useState } from "react";
import { Trash2 } from "lucide-react";

/** The bin that wobbles before a delete, and asks once ("Delete?") before it goes. */
export default function DeleteButton({ onDelete, label, disabled = false, light, disabledTitle = "Wait for it to finish preparing" }: {
  onDelete: () => void; label: string; disabled?: boolean; light?: boolean; disabledTitle?: string;
}) {
  const [asking, setAsking] = useState(false);
  const [wobble, setWobble] = useState(0);
  if (asking) {
    return (
      <span className="flex items-center gap-2 text-xs">
        <button onClick={() => { setAsking(false); onDelete(); }} className="font-semibold" style={{ color: light ? "#fff" : "var(--bad)" }}>Delete</button>
        <button onClick={() => setAsking(false)} style={{ color: light ? "rgba(255,255,255,0.8)" : "var(--muted)" }}>Cancel</button>
      </span>
    );
  }
  return (
    <button
      onClick={() => { setWobble((w) => w + 1); setTimeout(() => setAsking(true), 380); }}  // let the bin wobble first
      disabled={disabled}
      className="p-1.5 rounded-lg disabled:opacity-30"
      aria-label={label}
      title={disabled ? disabledTitle : "Delete"}
    >
      <Trash2 key={wobble} className={`w-4 h-4 ${wobble ? "bin-wobble" : ""}`} style={{ color: light ? "currentColor" : "var(--faint)" }} />
    </button>
  );
}
