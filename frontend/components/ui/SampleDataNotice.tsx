import Link from "next/link";
import { Info } from "lucide-react";

/** Marks a page whose charts still show illustrative data, so it isn't mistaken for the user's own. */
export default function SampleDataNotice({ what }: { what: string }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 text-sm"
      style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderLeft: "3px solid var(--warn)" }}>
      <Info className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: "var(--warn)" }} />
      <p style={{ color: "var(--ink-2)" }}>
        <strong style={{ color: "var(--ink)" }}>Sample data.</strong> The {what} on this page are illustrative and not
        yet connected to your sessions. Your real results are on each session&rsquo;s{" "}
        <Link href="/practice" className="underline underline-offset-2" style={{ color: "var(--accent-ink)" }}>results page</Link>.
      </p>
    </div>
  );
}
