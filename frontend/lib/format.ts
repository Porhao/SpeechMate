// Every date and duration shown in the app, in one place (Malaysian English formatting)
type When = string | Date;
const show = (when: When, opts: Intl.DateTimeFormatOptions) => new Date(when).toLocaleString("en-MY", opts);

/** "1:05" (whole seconds, never negative) */
export function formatDuration(seconds: number): string {
  const t = Math.max(0, Math.floor(seconds));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}

/** "12 Nov" */
export const formatDay = (when: When) => show(when, { day: "numeric", month: "short" });
/** "12 Nov 2026" */
export const formatDate = (when: When) => show(when, { dateStyle: "medium" });
/** "12 Nov 2026, 3:05 pm" */
export const formatDateTime = (when: When) => show(when, { dateStyle: "medium", timeStyle: "short" });
/** "November 2026" */
export const formatMonth = (when: When) => show(when, { month: "long", year: "numeric" });
