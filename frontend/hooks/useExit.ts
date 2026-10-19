"use client";

import { useCallback, useState } from "react";

const EXIT_MS = 450;  // .row-exit in globals.css

/** Delete animation for list rows: `exit(id, remove)` plays .row-exit on that row, then runs
 *  `remove` (dropping it from the list) once the row has folded away. */
export function useExit() {
  const [leaving, setLeaving] = useState<ReadonlySet<string>>(new Set());
  const exit = useCallback((id: string, remove: () => void) => {
    setLeaving((s) => new Set(s).add(id));
    setTimeout(() => {
      remove();
      setLeaving((s) => { const n = new Set(s); n.delete(id); return n; });
    }, EXIT_MS);
  }, []);
  return { isLeaving: (id: string) => leaving.has(id), exit };
}
