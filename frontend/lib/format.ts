// Every date and duration shown in the app, in one place (Malaysian English formatting)
type When = string | Date;
const show = (when: When, opts: Intl.DateTimeFormatOptions) => new Date(when).toLocaleString("en-MY", opts);

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** "12 Nov" */
export const formatDay = (when: When) => show(when, { day: "numeric", month: "short" });
/** "12 Nov 2026" */
export const formatDate = (when: When) => show(when, { dateStyle: "medium" });
/** "12 Nov 2026, 3:05 pm" */
export const formatDateTime = (when: When) => show(when, { dateStyle: "medium", timeStyle: "short" });
/** "November 2026" */
export const formatMonth = (when: When) => show(when, { month: "long", year: "numeric" });
