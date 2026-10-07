/// <reference types="react/canary" />

// Remounts on every navigation (unlike layout.tsx), so each page gets an enter/exit
// view transition: the old page squashes and fades, the new one springs up ("clay pop").
// The CSS is in globals.css (.page-3d-in / .page-3d-out); browsers without the
// View Transitions API just switch pages as before.

import { ViewTransition } from "react";

export default function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <ViewTransition enter="page-3d-in" exit="page-3d-out" default="none">
      <div>{children}</div>
    </ViewTransition>
  );
}
