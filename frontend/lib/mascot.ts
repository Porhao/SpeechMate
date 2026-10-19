// The companion character's event bus: pages announce what the user just did, and the
// character (components/layout/Mascot.tsx) reacts. Fire-and-forget; nothing listens on the server.

export type MascotAction =
  | "busy"       // something started (upload, search) — it works along
  | "success"    // it finished — a happy hop
  | "deleted"    // something was removed — a little wobble
  | "search"     // the user is searching — it peeks
  | "empty"      // a search found nothing — a puzzled tilt
  | "done"       // a task was ticked off — a spin
  | "error";     // something failed — a shake

export const MASCOT_EVENT = "speechmate:mascot";

export function mascot(action: MascotAction, say?: string) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(MASCOT_EVENT, { detail: { action, say } }));
  }
}
