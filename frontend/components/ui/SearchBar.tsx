"use client";

// A search box that grows when you use it: the magnifier sweeps while you type, a clear button
// appears, and screen readers hear how many results match. Mate peeks when you search and
// looks puzzled when nothing matches. <Highlight> marks the matching part of a result.

import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { mascot } from "@/lib/mascot";

export function SearchBar({ value, onChange, placeholder, results, label = "Search" }: {
  value: string; onChange: (v: string) => void; placeholder: string; results: number; label?: string;
}) {
  const [typing, setTyping] = useState(false);
  const stopTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const peeked = useRef(false);
  const q = value.trim();

  // Mate reacts once the user pauses: a peek for the first search, a tilt when nothing matches
  useEffect(() => {
    if (!q) { peeked.current = false; return; }
    const t = setTimeout(() => {
      if (results === 0) mascot("empty", `Nothing matches "${q}".`);
      else if (!peeked.current) { mascot("search"); peeked.current = true; }
    }, 600);
    return () => clearTimeout(t);
  }, [q, results]);

  const change = (v: string) => {
    onChange(v);
    setTyping(true);
    if (stopTimer.current) clearTimeout(stopTimer.current);
    stopTimer.current = setTimeout(() => setTyping(false), 500);
  };

  return (
    <div role="search" className={`relative w-full sm:w-56 focus-within:sm:w-72 transition-[width] duration-300 ${typing ? "search-active" : ""}`}>
      <Search className="search-icon absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "var(--muted)" }} />
      <input type="search" value={value} onChange={(e) => change(e.target.value)} placeholder={placeholder} aria-label={label}
        onKeyDown={(e) => { if (e.key === "Escape") onChange(""); }}
        className="w-full pl-9 pr-8 py-2 rounded-full text-sm outline-none [&::-webkit-search-cancel-button]:hidden"
        style={{ background: "var(--surface-2)", border: "1px solid var(--line)", color: "var(--ink)" }} />
      {value && (
        <button onClick={() => onChange("")} aria-label="Clear search"
          className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full flex items-center justify-center hover:bg-[var(--surface-3)]"
          style={{ color: "var(--muted)" }}>
          <X className="w-3.5 h-3.5" />
        </button>
      )}
      <span className="sr-only" aria-live="polite">{q ? `${results} result${results === 1 ? "" : "s"}` : ""}</span>
    </div>
  );
}

/** `text` with the first case-insensitive match of `query` marked. */
export function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim().toLowerCase();
  const i = q ? text.toLowerCase().indexOf(q) : -1;
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<mark className="search-hit">{text.slice(i, i + q.length)}</mark>{text.slice(i + q.length)}</>;
}

/** Whether any of `fields` contains `query` (case-insensitive); an empty query matches all. */
export const matches = (query: string, ...fields: (string | null | undefined)[]) => {
  const q = query.trim().toLowerCase();
  return !q || fields.some((f) => f?.toLowerCase().includes(q));
};
