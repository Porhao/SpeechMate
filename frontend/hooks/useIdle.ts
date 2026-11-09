"use client";

import { useEffect, useState } from "react";

/** True once the browser is idle after the first render: for decoration (the 3D logo, the
 *  companion) that shouldn't compete with the page's own loading. */
export function useIdle(timeout = 2000): boolean {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    if ("requestIdleCallback" in window) {
      const id = window.requestIdleCallback(() => setIdle(true), { timeout });
      return () => window.cancelIdleCallback(id);
    }
    const t = setTimeout(() => setIdle(true), 600);  // Safari has no requestIdleCallback
    return () => clearTimeout(t);
  }, [timeout]);
  return idle;
}
